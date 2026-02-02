# Bibliographic Extractor - Minimal Prototype

A Claude-powered tool for extracting bibliographic information from PDF files and generating BibLaTeX-Chicago entries.

## What This Prototype Does

1. Takes a PDF file as input
2. Extracts text from the first 2 pages and last page
3. Automatically runs OCR if pages appear to be scanned
4. Sends extracted text to Claude API with your project context
5. Returns a properly formatted BibLaTeX-Chicago entry
6. Appends the entry to `biblio-ai.bib`

## Setup Instructions

### 1. Install System Dependencies (macOS)

```bash
# Install OCR tool (optional but recommended for scanned PDFs)
brew install ocrmypdf
```

### 2. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install required packages
pip install -r requirements.txt
```

### 3. Get Your Anthropic API Key

1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key
3. Copy the key (starts with `sk-ant-`)

### 4. Configure the Tool

Edit `config.yaml` and add your API key:

```yaml
anthropic_api_key: "sk-ant-api03-your-actual-key-here"
```

You can also customize other settings like paths and model selection.

### 5. Add Your Project Files

Place these files in the same directory:
- `CLAUDE.md` - Your project guidelines
- `biblio-template.bib` - Your reference template

Create a `pdf/` folder for your PDF files:
```bash
mkdir pdf
```

## Usage

### Process a Single PDF

```bash
python biblio_agent.py path/to/paper.pdf
```

This will:
- Extract bibliographic info
- Print the BibLaTeX entry to console
- Append it to `biblio-ai.bib`

### Process Without Saving

To just see the output without saving:

```bash
python biblio_agent.py path/to/paper.pdf --no-save
```

### Use Custom Config File

```bash
python biblio_agent.py path/to/paper.pdf --config my-config.yaml
```

### Specify Custom Output File

```bash
python biblio_agent.py path/to/paper.pdf --output my-bibliography.bib
```

## Example Workflow

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Process a PDF
python biblio_agent.py pdf/smith2023.pdf

# Output:
# 📄 Processing: smith2023.pdf
#    Extracting text...
#    Sending to Claude...
#    ✓ Complete
#    ✓ Saved to ./biblio-ai.bib
#
# @Article{Smith2023,
#   author = {Smith, John},
#   title = {A Study of Something Important},
#   ...
# }
```

## File Structure

```
biblio-extractor/
├── biblio_agent.py       # Main orchestrator
├── extract_pages.py      # PDF text extraction
├── config.yaml           # Your configuration
├── requirements.txt      # Python dependencies
├── CLAUDE.md             # Project guidelines
├── biblio-template.bib   # Reference template
├── biblio-ai.bib         # Generated bibliography (created automatically)
└── pdf/                  # Your PDF files
```

## Troubleshooting

### "anthropic_api_key not found"
- Make sure you've edited `config.yaml` with your actual API key
- The key should start with `sk-ant-`

### "ocrmypdf not installed"
- This is only needed for scanned PDFs
- Install with: `brew install ocrmypdf`
- Or the tool will skip OCR and work with text-based PDFs only

### "Could not read PDF"
- Make sure the PDF isn't corrupted
- Try opening it in Preview/Adobe Reader first
- Some encrypted PDFs may not work

### Poor extraction quality
- Check that your `CLAUDE.md` file has clear guidelines
- Make sure `biblio-template.bib` shows good examples
- The first 2 + last page might not always have all info
- Consider manually checking/editing the output

## What's Next?

This is the minimal prototype. Once you verify it works well with your PDFs, we can add:

1. **Batch processing** - Process entire folders
2. **Folder watching** - Auto-process new PDFs
3. **Deduplication** - Track already-processed files
4. **Error recovery** - Retry failed extractions
5. **Quality checks** - Validate BibLaTeX syntax
6. **Interactive mode** - Review entries before saving

## Cost Estimate

With Claude Sonnet 4:
- ~$0.003 per PDF (input tokens)
- ~$0.015 per PDF (output tokens)
- **~$0.02 per PDF total**

For 5000 PDFs: approximately $100 total

## License

This is a custom tool for personal use.
