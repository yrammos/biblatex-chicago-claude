#!/usr/bin/env python3
"""
Ablation runner for Issue #7: does the ~69k-token static prefix earn its
size? Scores dev/eval/sample/ once per prefix variant - the full prefix
(baseline), then once with each optional prompt-context component removed
(ref_file, and each entry in example_files; notes-test.bib is the largest
and the first candidate) - and reports each variant's field-level counts
plus a one-line comparison against the baseline.

Blocked on Issue #6: dev/eval/sample/ and dev/eval/expected.bib are still
empty (populating them is hand work, not something this script can do), so
this has never been run against real data or the live API. It exits
immediately, before importing biblio_agent or constructing an Anthropic
client, whenever the sample is empty - see main() below.

    python3 dev/eval/ablate.py                       # every variant, once the sample is populated
    python3 dev/eval/ablate.py --variant "without notes-test.bib"
    python3 dev/eval/test_ablate.py                   # self-test; no sample, no API call

Deliberately NOT implemented here: selective inclusion (classify the source
into a family, then load only that family's slice of examples). The issue's
own caveat is to model the cache-fragmentation cost before building it -
each family becomes its own cache prefix, and below some batch size that
costs more than it saves. That modeling needs the baseline this script
produces as an input, so it comes after, not alongside.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run as eval_run  # noqa: E402
import scorer  # noqa: E402


def build_variants(base_config: dict) -> list:
    """(name, description, config) for the baseline plus one ablation per
    optional prompt-context component actually present in base_config -
    built from the config in use, not hardcoded, so a config that adds or
    drops an example_files entry is picked up automatically.

    claude_md_file and template_file are never ablated: they are the house
    style and the one required worked example per type, not optional
    context - removing either isn't a prefix-size experiment, it's a
    different (broken) product.
    """
    variants = [("baseline", "full prefix", dict(base_config))]

    if base_config.get('ref_file'):
        name = f"without {Path(base_config['ref_file']).name}"
        c = dict(base_config)
        c.pop('ref_file', None)
        variants.append((name, "condensed field reference removed", c))

    for spec in base_config.get('example_files') or []:
        path = spec['path'] if isinstance(spec, dict) else spec
        label = spec.get('label', path) if isinstance(spec, dict) else path
        name = f"without {Path(path).name}"
        c = dict(base_config)
        c['example_files'] = [s for s in c['example_files'] if s is not spec]
        variants.append((name, label, c))

    return variants


def run_ablation(variants, manifest, sample_dir, expected_entries, run_one_factory):
    """Score every variant over the same manifest.

    run_one_factory(config) -> run_one(source_path) -> Entry|None builds the
    extraction step for one variant's config - injected so this needs
    nothing about BiblioAgent or the API, exactly like run.py's evaluate().

    Returns [(name, description, entry_scores, warnings), ...], one per
    variant, in the order build_variants() produced them (baseline first).
    """
    results = []
    for name, description, config in variants:
        run_one = run_one_factory(config)
        entry_scores, warnings = eval_run.evaluate(
            manifest, sample_dir, expected_entries, run_one=run_one,
        )
        results.append((name, description, entry_scores, warnings))
    return results


def summarize(entry_scores: list) -> dict:
    """One variant's field counts collapsed to totals, for the comparison
    table - the full per-field breakdown is still in that variant's own
    format_report() output, printed alongside."""
    agg = scorer.aggregate(entry_scores)
    totals = Counter()
    for es in entry_scores:
        for fs in es.fields:
            totals[fs.verdict] += 1
    return {
        'n_entries': agg['n_entries'],
        'type_accuracy': agg['type_accuracy'],
        **{v: totals.get(v, 0) for v in scorer.VERDICTS},
    }


def format_comparison(results) -> str:
    """One row per variant: entries scored, entry-type accuracy, and the
    field-verdict totals - a summary to compare variants by, not a
    replacement for each variant's own detailed report."""
    rows = []
    for name, description, entry_scores, _warnings in results:
        s = summarize(entry_scores)
        pct = f"{s['type_accuracy']:.0%}" if s['type_accuracy'] is not None else "n/a"
        rows.append((name, s['n_entries'], pct,
                     s['exact'], s['different'], s['missing'], s['spurious']))

    name_w = max([len("Variant")] + [len(r[0]) for r in rows])
    header = (f"{'Variant':<{name_w}}  {'Entries':<7}  {'Type acc.':<9}  "
              f"{'Exact':<7}  {'Different':<9}  {'Missing':<7}  {'Spurious':<8}")
    lines = ["=" * 60, "Ablation comparison", "=" * 60, "", header, "-" * len(header)]
    for name, n, pct, exact, different, missing, spurious in rows:
        lines.append(f"{name:<{name_w}}  {n:<7}  {pct:<9}  "
                      f"{exact:<7}  {different:<9}  {missing:<7}  {spurious:<8}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sample-dir', default=str(eval_run.DEFAULT_SAMPLE_DIR),
                         help='Directory holding manifest.json and the source files (default: dev/eval/sample/)')
    parser.add_argument('--expected', default=str(eval_run.DEFAULT_EXPECTED),
                         help='Hand-verified .bib to score against (default: dev/eval/expected.bib)')
    parser.add_argument('--config', default='config.yaml',
                         help='Path to config file (default: config.yaml)')
    parser.add_argument('--model', help='Claude model to use (overrides config)')
    parser.add_argument('--variant', action='append', metavar='NAME',
                         help="Restrict to this variant (repeatable); default is every variant. "
                              "'baseline' is always included, matched by name from a first run's output")
    args = parser.parse_args(argv)

    sample_dir = Path(args.sample_dir)
    manifest = eval_run.load_manifest(sample_dir)
    if not manifest:
        print(f"No manifest entries in {sample_dir / 'manifest.json'} - nothing to ablate.\n"
              f"This is expected until Issue #6's sample is populated; see dev/eval/README.md.",
              file=sys.stderr)
        return 1

    expected_path = Path(args.expected)
    if not expected_path.exists() or not expected_path.read_text(encoding='utf-8').strip():
        print(f"{expected_path} is empty - nothing to score against.\n"
              f"See dev/eval/README.md for its format.", file=sys.stderr)
        return 1
    expected_entries = eval_run.load_bib(expected_path)

    sys.path.insert(0, str(eval_run.ROOT / 'src'))
    import biblio_agent  # noqa: E402 - imported here, not at module load, so
    # test_ablate.py can import this module and drive run_ablation() and
    # build_variants() directly without needing config.yaml or anthropic.

    agent = biblio_agent.BiblioAgent(args.config)
    if args.model:
        agent.config['model'] = args.model
    base_config = dict(agent.config)

    variants = build_variants(base_config)
    if args.variant:
        wanted = set(args.variant) | {"baseline"}
        variants = [v for v in variants if v[0] in wanted]

    def run_one_factory(variant_config):
        def run_one(source_path):
            original = agent.config
            agent.config = variant_config
            try:
                return eval_run.run_pipeline(agent, source_path)
            finally:
                agent.config = original
        return run_one

    results = run_ablation(variants, manifest, sample_dir, expected_entries, run_one_factory)

    for name, description, entry_scores, warnings in results:
        print(f"\n### {name} ({description})\n")
        print(scorer.format_report(entry_scores, warnings))

    print()
    print(format_comparison(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
