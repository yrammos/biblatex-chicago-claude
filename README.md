# Ostracon AI

A Claude-powered macOS tool for extracting bibliographic information from academic PDF files and generating BibLaTeX-Chicago entries (notes and bibliography style).

## What It Does

1. Takes one or more PDF files as input
2. Extracts text from the first page (~450 words) and last ~150 words
3. Automatically runs OCR if the PDF appears to be scanned
4. Sends the extracted text to the Claude API with project guidelines and a reference template
5. Returns a properly formatted BibLaTeX-Chicago entry
6. Validates brace balance before saving
7. Appends the entry — with a BibDesk `bdsk-file-1` bookmark — to a staging file (`~/Desktop/biblio-staging.bib`)
8. On validation failure, saves the raw entry to `~/Desktop/biblio-failed.bib` and sends a macOS notification

The staging file can be periodically imported into BibDesk; PDF links will already be intact thanks to the embedded bookmark.

## Setup

### 1. Install System Dependencies

```bash
# OCR support (optional but recommended for scanned PDFs)
brew install ocrmypdf
```

### 2. Create a Python Environment and Install Dependencies

```bash
conda create -n biblio-ai python=3.11   # or use venv
conda activate biblio-ai
pip install -r requirements.txt
```

`requirements.txt` includes:
- `anthropic` — Claude API client
- `pypdf` — PDF text extraction
- `pyyaml` — configuration
- `pyobjc-framework-Cocoa` — macOS file bookmarks for BibDesk integration

### 3. Configure

Edit `config.yaml`:

```yaml
anthropic_api_key: "sk-ant-..."          # your Anthropic API key
main_bib_file: "~/Desktop/biblio-staging.bib"  # staging output
```

The other paths (`pdf_in_folder`, `pdf_out_folder`, `template_file`, `claude_md_file`) can be left as-is or adjusted to your setup.

### 4. Customize the Extraction Prompt

Edit `CLAUDE.md` to match your bibliographic conventions. At minimum, review:

- The output format and field exclusions (e.g. which fields to omit)
- Title-case rules for any languages you work with
- Any domain-specific entry types or fields you rely on

The richer and more specific your `CLAUDE.md`, the more accurately Claude will format entries to your standards.

### 5. Configure the Automator Script

```bash
cp automator/script.sh.example automator/script.sh
```

Edit `automator/script.sh` and set `PYTHON` to the path of your Python executable and `WORKDIR` to the absolute path of this repository. This file is excluded from version control.

### 6. Install the macOS Quick Action

```bash
python3 install_service.py
```

This builds the Automator workflow from `automator/script.sh` and installs it to `~/Library/Services/`. Re-run it any time you modify `script.sh`.

## Usage

### macOS Quick Action (recommended)

Right-click any PDF (or selection of PDFs) in Finder and choose **Extract BibLaTeX-Chicago Bibliography (via Claude)**. The entry is appended to the staging file and copied to the clipboard.

See [Setup](#5-configure-the-automator-script) for initial configuration. To reinstall after changes to `automator/script.sh`:

```bash
python3 install_service.py
```

### Command Line

```bash
# Process one or more PDFs
python biblio_agent.py path/to/paper.pdf

# Process without saving (print to stdout only)
python biblio_agent.py path/to/paper.pdf --no-save

# Process all PDFs in pdf-in/ and move them to pdf-out/
python biblio_agent.py --all

# Write to a custom output file
python biblio_agent.py path/to/paper.pdf --output custom.bib
```

## File Structure

```
ostracon-ai/
├── biblio_agent.py       # Main orchestrator
├── extract_pages.py      # PDF text extraction with OCR fallback
├── install_service.py    # Builds and installs the macOS Quick Action
├── config.yaml           # Configuration (API key, paths, model)
├── requirements.txt      # Python dependencies
├── CLAUDE.md             # Bibliographic extraction guidelines for Claude
├── biblio-template.bib   # Reference template for BibLaTeX-Chicago types/fields
├── automator/
│   ├── script.sh.example # Shell script template (copy to script.sh and edit)
│   └── script.sh         # Your local script (gitignored — machine-specific paths)
├── pdf-in/               # Drop PDFs here for batch processing (--all)
└── pdf-out/              # Processed PDFs are moved here
```

## BibDesk Integration

The tool writes to `~/Desktop/biblio-staging.bib` rather than directly to your main BibDesk database, because BibDesk does not detect external file modifications. Import the staging file into BibDesk manually whenever you want to merge new entries. Each entry includes a `bdsk-file-1` field with a macOS file bookmark, so PDF links will be resolved correctly after import.

## Troubleshooting

**Entry saved to `~/Desktop/biblio-failed.bib` instead of staging file**
The generated entry had unbalanced braces. Open the failed file, fix the entry manually, and add it to the staging file.

**`bdsk-file-1` bookmark not working after import**
Make sure `pyobjc-framework-Cocoa` is installed in the Python environment used by the Quick Action (check the `PYTHON` path in `automator/script.sh`).

**Quick Action not appearing in Finder**
Run `python3 install_service.py` and check System Settings → General → Login Items & Extensions to confirm the action is enabled.

**OCR not working**
Install `ocrmypdf` via Homebrew. The tool will fall back to direct text extraction if OCR is unavailable.

## Cost Estimate

Using Claude Sonnet:
- ~$0.02 per PDF

## License

Personal use.
