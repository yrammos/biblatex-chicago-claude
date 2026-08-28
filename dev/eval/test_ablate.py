#!/usr/bin/env python3
"""
Self-test for the ablation runner (ablate.py), against a synthetic config
and fixture pair built here at run time. Makes no API call, needs no
config.yaml, and never imports biblio_agent - build_variants() and
run_ablation() take a plain config dict and an injected extraction step,
exactly like run.py's evaluate().

    python3 dev/eval/test_ablate.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ablate  # noqa: E402
import bib_audit  # noqa: E402
import run as eval_run  # noqa: E402


def _entry(text: str) -> bib_audit.Entry:
    entries, _ = bib_audit.scan(text)
    assert len(entries) == 1
    return entries[0]


# A synthetic config shaped like a loaded BiblioAgent config: ref_file and
# two example_files entries (one dict-with-label, one bare path - config.py
# allows both, see BiblioAgent.load_config).
BASE_CONFIG = {
    'model': 'claude-sonnet-4-6',
    'ref_file': '/fake/prompt-context/biblatex-chicago-notes-ref.md',
    'example_files': [
        {'path': '/fake/prompt-context/notes-test.bib', 'label': 'annotated test suite'},
        '/fake/prompt-context/cms-notes-intro-guide.md',
    ],
}


def test_build_variants_shape():
    variants = ablate.build_variants(BASE_CONFIG)
    names = [v[0] for v in variants]
    assert names[0] == "baseline"
    assert "without biblatex-chicago-notes-ref.md" in names
    assert "without notes-test.bib" in names
    assert "without cms-notes-intro-guide.md" in names
    assert len(names) == 4
    return True


def test_build_variants_actually_removes_the_component():
    variants = ablate.build_variants(BASE_CONFIG)
    by_name = {v[0]: v[2] for v in variants}

    assert 'ref_file' in by_name['baseline']
    assert 'ref_file' not in by_name['without biblatex-chicago-notes-ref.md']
    # Removing ref_file must not also drop example_files.
    assert len(by_name['without biblatex-chicago-notes-ref.md']['example_files']) == 2

    ex_names = [Path(s['path'] if isinstance(s, dict) else s).name
                for s in by_name['without notes-test.bib']['example_files']]
    assert ex_names == ['cms-notes-intro-guide.md']
    return True


def test_build_variants_does_not_mutate_base_config():
    import copy
    original = copy.deepcopy(BASE_CONFIG)
    ablate.build_variants(BASE_CONFIG)
    assert BASE_CONFIG == original
    return True


def test_build_variants_with_no_optional_components():
    variants = ablate.build_variants({'model': 'x'})
    assert [v[0] for v in variants] == ["baseline"]
    return True


def test_run_ablation_shows_accuracy_dropping_without_a_component():
    """The whole point of the harness: a variant that behaves worse must be
    visible in the comparison. Simulated here by making the canned
    extraction step consult the variant's own config, the same way a real
    model's answer would actually depend on what's in its prompt."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        sample_dir = td / 'sample'
        sample_dir.mkdir()
        (sample_dir / 'a.pdf').write_bytes(b'placeholder')

        manifest = [{"citekey": "A", "source": "a.pdf"}]
        expected_entries = {"A": _entry(
            "@Article{A, Author = {Doe, Jane}, Title = {A Title}, Journaltitle = {A Journal},}"
        )}

        def run_one_factory(config):
            def run_one(source_path):
                # With ref_file present: gets Journaltitle right too.
                # Without it: "forgets" that field - a stand-in for a real
                # accuracy regression, not a literal model of one.
                if config.get('ref_file'):
                    return _entry("@Article{A, Author = {Doe, Jane}, Title = {A Title}, "
                                  "Journaltitle = {A Journal},}")
                return _entry("@Article{A, Author = {Doe, Jane}, Title = {A Title},}")
            return run_one

        variants = ablate.build_variants(BASE_CONFIG)
        results = ablate.run_ablation(variants, manifest, sample_dir, expected_entries, run_one_factory)

        by_name = {name: entry_scores for name, _desc, entry_scores, _warn in results}
        baseline_summary = ablate.summarize(by_name['baseline'])
        without_ref_summary = ablate.summarize(by_name['without biblatex-chicago-notes-ref.md'])

        assert baseline_summary['missing'] == 0
        assert without_ref_summary['missing'] == 1  # Journaltitle now missing

        report = ablate.format_comparison(results)
        assert "baseline" in report
        assert "without biblatex-chicago-notes-ref.md" in report

    return True


TESTS = [
    test_build_variants_shape,
    test_build_variants_actually_removes_the_component,
    test_build_variants_does_not_mutate_base_config,
    test_build_variants_with_no_optional_components,
    test_run_ablation_shows_accuracy_dropping_without_a_component,
]


def main():
    failures = []
    for test in TESTS:
        try:
            assert test() is True
            print(f"  ✓ {test.__name__}")
        except Exception as e:
            failures.append((test.__name__, e))
            print(f"  ✗ {test.__name__}: {e}")

    print()
    if failures:
        print(f"{len(failures)}/{len(TESTS)} test(s) failed.")
        return 1
    print(f"All {len(TESTS)} ablation self-tests passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
