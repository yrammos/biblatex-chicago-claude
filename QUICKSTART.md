# Quick Start Guide

Get up and running in 5 minutes.

## Step 1: Install dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install OCR tool (optional, for scanned PDFs)
brew install ocrmypdf
```

## Step 2: Get API key

1. Visit https://console.anthropic.com/settings/keys.
2. Create a new API key.
3. Copy it (starts with `sk-ant-`).

## Step 3: Configure

Edit `config.yaml` and replace `YOUR_API_KEY_HERE` with your actual API key:

```yaml
anthropic_api_key: "sk-ant-api03-xxxxxxxxxxxxx"
```

## Step 4: Add your files

1. Copy your `CLAUDE.md` to this directory.
2. Copy your `biblio-template.bib` to this directory.
3. Create a `pdf/` folder: `mkdir pdf`.
4. Put a test PDF in the `pdf/` folder.

## Step 5: Test setup

```bash
python test_setup.py
```

This will verify everything is configured correctly.

## Step 6: Process your first PDF

```bash
python biblio_agent.py pdf/your-test-file.pdf
```

You should see:

- Processing messages.
- The extracted BibLaTeX entry printed to console.
- Entry appended to the file set in `main_bib_file` (your `config.yaml`).

## Step 7: Review the output

Open the file set in `main_bib_file` and check:

- Is the entry type correct? (@Book, @Article, etc.)
- Are the fields properly populated?
- Is the formatting correct?

## Troubleshooting quick fixes

**“anthropic_api_key not found”**
Edit config.yaml with your real API key

**“CLAUDE.md not found”**
Copy your existing CLAUDE.md file to this directory

**“No module named ‘anthropic’”**
Run: `pip install -r requirements.txt`

**“ocrmypdf not installed”**
Only needed for scanned PDFs. Run: `brew install ocrmypdf`. When a scanned PDF is detected, a language selection dialog will appear — choose the document’s language. Set `default_ocr_language` in `config.yaml` (e.g. `rus`, `deu`) for unattended use.

## What’s in each file?

- **biblio_agent.py** - Main program (orchestrates everything).
- **extract_pages.py** - PDF text extraction (with OCR).
- **config.yaml** - Your settings (API key, paths).
- **test_setup.py** - Verifies your setup.
- **requirements.txt** - Python packages needed.

## Next steps

Once you’ve successfully processed one PDF:

1. Try a few more PDFs to verify quality.
2. Check if the bibliographic entries are accurate.
3. Adjust `CLAUDE.md` if needed to improve extraction.
4. Let me know if you want batch processing or folder watching!

## Cost per PDF

Approximately $0.02 per PDF with Claude Sonnet 4.
