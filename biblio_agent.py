#!/usr/bin/env python3
"""
Bibliographic extraction agent using Claude API.
Processes PDFs and generates BibLaTeX-Chicago entries.
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import yaml
from anthropic import Anthropic

from extract_pages import extract_content

class BiblioAgent:
    def __init__(self, config_path="config.yaml"):
        """Initialize the agent with configuration."""
        self.config = self.load_config(config_path)
        self.client = Anthropic(api_key=self.config['anthropic_api_key'])
        
    def load_config(self, config_path):
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                "Please create config.yaml from the template."
            )
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        if not config.get('anthropic_api_key') or config['anthropic_api_key'] == 'YOUR_API_KEY_HERE':
            raise ValueError(
                "Please set your Anthropic API key in config.yaml\n"
                "Get one at: https://console.anthropic.com/settings/keys"
            )
        
        return config
    
    def load_context_files(self):
        """Load CLAUDE.md and biblio-template.bib for context."""
        context = {}
        verbose = self.config.get('verbose', True)

        # Load CLAUDE.md
        claude_md_path = Path(self.config['claude_md_file'])
        if claude_md_path.exists():
            with open(claude_md_path) as f:
                context['claude_md'] = f.read()
        else:
            if verbose:
                print(f"⚠️  Warning: {claude_md_path} not found", file=sys.stderr)
            context['claude_md'] = ""

        # Load biblio-template.bib
        template_path = Path(self.config['template_file'])
        if template_path.exists():
            with open(template_path) as f:
                context['template'] = f.read()
        else:
            if verbose:
                print(f"⚠️  Warning: {template_path} not found", file=sys.stderr)
            context['template'] = ""

        return context
    
    def build_prompt(self, pdf_text, context):
        """Build the prompt for Claude."""
        prompt = f"""I need you to extract bibliographic information from a PDF and create a BibLaTeX entry using the biblatex-chicago package (notes and bibliography style).

Here is the extracted text from the first 2 pages and last page of the PDF:

<pdf_text>
{pdf_text}
</pdf_text>

"""
        
        if context['claude_md']:
            prompt += f"""Here are the project guidelines:

<guidelines>
{context['claude_md']}
</guidelines>

"""
        
        if context['template']:
            prompt += f"""Here is a reference template showing the types and fields you should use:

<reference_template>
{context['template']}
</reference_template>

"""
        
        prompt += """Please:
1. Identify the publication type (@Book, @Article, @InCollection, etc.)
2. Extract all relevant bibliographic fields
3. Format as a single BibLaTeX entry using biblatex-chicago standards
4. Use a citation key in the format: AuthorYEAR (e.g., Smith2023)
5. Use single hyphens (-) for all ranges (pages, dates, etc.)
6. Do NOT include these fields: ISSN, ISBN, keywords, reference, devonthink

Output ONLY the BibLaTeX entry, with no additional commentary or explanation."""

        return prompt
    
    def extract_bibtex(self, pdf_path):
        """
        Extract bibliographic information from a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            str: BibLaTeX entry or error message
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return f"Error: File not found: {pdf_path}"
        
        if self.config.get('verbose'):
            print(f"📄 Processing: {pdf_path.name}", file=sys.stderr)
        
        # Extract text from PDF
        if self.config.get('verbose'):
            print("   Extracting text...", file=sys.stderr)
        
        quiet = not self.config.get('verbose', True)
        pdf_text = extract_content(pdf_path, quiet=quiet)
        
        if pdf_text.startswith("Error:"):
            return pdf_text
        
        # Load context files
        context = self.load_context_files()
        
        # Build prompt
        prompt = self.build_prompt(pdf_text, context)
        
        # Call Claude API
        if self.config.get('verbose'):
            print("   Sending to Claude...", file=sys.stderr)
        
        try:
            message = self.client.messages.create(
                model=self.config['model'],
                max_tokens=self.config['max_tokens'],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            bibtex_entry = message.content[0].text
            
            if self.config.get('verbose'):
                print("   ✓ Complete", file=sys.stderr)
            
            return bibtex_entry
            
        except Exception as e:
            return f"Error calling Claude API: {e}"
    
    def clean_bibtex(self, bibtex_entry):
        """Remove code fencing from BibLaTeX entry if present."""
        entry = bibtex_entry.strip()
        # Remove ```bibtex or ``` fencing
        if entry.startswith("```"):
            lines = entry.split("\n")
            # Remove first line (```bibtex or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            entry = "\n".join(lines)
        return entry.strip()

    def save_entry(self, bibtex_entry, pdf_name):
        """Append BibLaTeX entry to output file."""
        output_path = Path(self.config['output_file'])

        # Create file if it doesn't exist
        if not output_path.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch()

        # Append entry
        with open(output_path, 'a') as f:
            f.write(self.clean_bibtex(bibtex_entry))
            f.write("\n\n")

        if self.config.get('verbose'):
            print(f"   ✓ Saved to {output_path}", file=sys.stderr)

    def move_to_processed(self, pdf_path):
        """Move a processed PDF to the output folder."""
        pdf_path = Path(pdf_path)
        out_folder = Path(self.config.get('pdf_out_folder', './pdf-out'))
        out_folder.mkdir(parents=True, exist_ok=True)

        dest = out_folder / pdf_path.name
        # Handle duplicates by adding a suffix
        if dest.exists():
            stem = pdf_path.stem
            suffix = pdf_path.suffix
            counter = 1
            while dest.exists():
                dest = out_folder / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.move(str(pdf_path), str(dest))

        if self.config.get('verbose'):
            print(f"   ✓ Moved to {dest}", file=sys.stderr)

        return dest

    def process_batch(self, move_files=True):
        """
        Process all PDFs in the input folder.

        Args:
            move_files: If True, move processed files to output folder

        Returns:
            dict: Summary with 'success', 'failed', 'skipped' lists
        """
        in_folder = Path(self.config.get('pdf_in_folder', './pdf-in'))

        if not in_folder.exists():
            print(f"Error: Input folder not found: {in_folder}", file=sys.stderr)
            print(f"Create it with: mkdir {in_folder}", file=sys.stderr)
            return {'success': [], 'failed': [], 'skipped': []}

        # Find all PDFs
        pdf_files = sorted(in_folder.glob('*.pdf'))

        if not pdf_files:
            print(f"No PDF files found in {in_folder}", file=sys.stderr)
            return {'success': [], 'failed': [], 'skipped': []}

        print(f"\n📚 Found {len(pdf_files)} PDF(s) in {in_folder}\n", file=sys.stderr)

        results = {'success': [], 'failed': [], 'skipped': []}

        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] {pdf_path.name}", file=sys.stderr)

            # Extract bibliography
            bibtex_entry = self.extract_bibtex(pdf_path)

            if bibtex_entry.startswith("Error:"):
                print(f"   ✗ {bibtex_entry}", file=sys.stderr)
                results['failed'].append((pdf_path.name, bibtex_entry))
                continue

            # Save entry
            self.save_entry(bibtex_entry, pdf_path.name)

            # Move file if requested
            if move_files:
                self.move_to_processed(pdf_path)

            results['success'].append(pdf_path.name)
            print(f"   ✓ Done\n", file=sys.stderr)

        # Print summary
        print("\n" + "=" * 40, file=sys.stderr)
        print("SUMMARY", file=sys.stderr)
        print("=" * 40, file=sys.stderr)
        print(f"✓ Success: {len(results['success'])}", file=sys.stderr)
        print(f"✗ Failed:  {len(results['failed'])}", file=sys.stderr)

        if results['failed']:
            print("\nFailed files:", file=sys.stderr)
            for name, error in results['failed']:
                print(f"  - {name}: {error}", file=sys.stderr)

        return results

def main():
    parser = argparse.ArgumentParser(
        description="Extract bibliographic data from PDFs using Claude"
    )
    parser.add_argument(
        'pdf_files',
        nargs='*',
        help='Path(s) to PDF file(s) to process'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all PDFs in the input folder (pdf-in/)'
    )
    parser.add_argument(
        '--no-move',
        action='store_true',
        help='Do not move processed files to output folder'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--output',
        help='Output bib file (overrides config)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Print to stdout instead of saving'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress status messages (for automation)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.pdf_files:
        parser.error("Either provide PDF file(s) or use --all to process the input folder")

    try:
        # Initialize agent
        agent = BiblioAgent(args.config)

        # Override config options
        if args.output:
            agent.config['output_file'] = args.output
        if args.quiet:
            agent.config['verbose'] = False

        # Batch processing mode
        if args.all:
            results = agent.process_batch(move_files=not args.no_move)
            if results['failed']:
                sys.exit(1)
            return

        # Single/multiple file mode
        for pdf_file in args.pdf_files:
            pdf_path = Path(pdf_file)
            if not args.quiet:
                print(f"\n📄 Processing: {pdf_path.name}", file=sys.stderr)

            # Extract bibliography
            bibtex_entry = agent.extract_bibtex(pdf_file)

            # Handle result
            if bibtex_entry.startswith("Error:"):
                print(bibtex_entry, file=sys.stderr)
                continue

            clean_entry = agent.clean_bibtex(bibtex_entry)
            if not args.no_save:
                agent.save_entry(bibtex_entry, pdf_path.name)
            print(clean_entry)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
