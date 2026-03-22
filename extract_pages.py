#!/usr/bin/env python3
"""
Extract bibliographic text from PDF files.
Extracts first N and last M words, with OCR fallback for scanned documents.
"""

import sys
import subprocess
import shutil
import re
from pathlib import Path
from pypdf import PdfReader


def run_ocr(pdf_path, pages=None, language="eng"):
    """
    Run ocrmypdf on the file.

    Args:
        pdf_path: Path to PDF
        pages: Optional page specification (e.g., "1-3,98-100")
        language: Tesseract language code (e.g., "eng", "rus", "deu")

    Returns:
        True on success, error string on failure
    """
    ocrmypdf_bin = shutil.which("ocrmypdf") or next(
        (p for p in ["/opt/homebrew/bin/ocrmypdf", "/usr/local/bin/ocrmypdf"] if Path(p).exists()),
        None
    )
    if not ocrmypdf_bin:
        return "Error: ocrmypdf not installed. Install with: brew install ocrmypdf"

    try:
        cmd = [ocrmypdf_bin, "--skip-text", "-l", language or "eng"]
        if pages:
            cmd.extend(["--pages", pages])
        cmd.extend([str(pdf_path), str(pdf_path)])

        import os
        env = os.environ.copy()
        for brew_bin in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if brew_bin not in env.get("PATH", ""):
                env["PATH"] = brew_bin + ":" + env.get("PATH", "")

        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=120,
            env=env,
        )
        return True
    except subprocess.TimeoutExpired:
        return "OCR Error: Process timed out after 2 minutes"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        if "already has text" in stderr.lower():
            return True
        return f"OCR Error: {stderr}"


def extract_all_text(pdf_path):
    """
    Extract text from all pages of a PDF.

    Returns:
        tuple: (list of page texts, num_pages) or (error_string, 0)
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return f"Error: File not found: {pdf_path}", 0

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        return f"Error: Could not read PDF: {e}", 0

    num_pages = len(reader.pages)

    if num_pages == 0:
        return "Error: PDF has no pages", 0

    page_texts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        page_texts.append(text)

    return page_texts, num_pages


def split_into_words(text):
    """Split text into words."""
    return [w for w in text.split() if w]


def snap_to_sentence_end(text, target_word_count, from_end=False):
    """
    Extract approximately target_word_count words, snapping to sentence boundary.

    Args:
        text: Full text
        target_word_count: Approximate number of words to extract
        from_end: If True, extract from end of text

    Returns:
        str: Extracted text snapped to sentence boundary
    """
    words = split_into_words(text)

    if len(words) <= target_word_count:
        return text.strip()

    if from_end:
        subset_words = words[-target_word_count:]
        subset_text = " ".join(subset_words)

        # Find first sentence boundary and start from there
        match = re.search(r'[.!?]\s+[A-Z]', subset_text)
        if match:
            return subset_text[match.end()-1:].strip()
        return subset_text
    else:
        subset_words = words[:target_word_count]
        subset_text = " ".join(subset_words)

        # Find last sentence boundary
        matches = list(re.finditer(r'[.!?](?:\s|$)', subset_text))
        if matches:
            last_match = matches[-1]
            return subset_text[:last_match.end()].strip()
        return subset_text


def extract_content(pdf_path, min_first_words=450, last_words=150, min_words_threshold=100, quiet=False, language_prompt_fn=None):
    """
    Extract beginning and end of PDF for bibliographic extraction.

    Beginning: max(first page, min_first_words) - ensures all page 1 metadata is captured.
    End: last_words from the end.

    Args:
        pdf_path: Path to PDF file
        min_first_words: Minimum words from beginning (takes more if page 1 is longer)
        last_words: Number of words to extract from end
        min_words_threshold: If total words below this, attempt OCR
        quiet: Suppress status messages
        language_prompt_fn: Optional callable () -> str that returns a tesseract language
            code (e.g. "eng", "rus"). Called interactively when OCR is needed.

    Returns:
        str: Extracted text with section markers
    """
    pdf_path = Path(pdf_path)

    # First pass: extract all text
    result, num_pages = extract_all_text(pdf_path)

    if isinstance(result, str) and result.startswith("Error:"):
        return result

    page_texts = result
    full_text = "\n\n".join(page_texts)
    words = split_into_words(full_text)
    total_words = len(words)

    # Check if OCR is needed
    if total_words < min_words_threshold:
        if not quiet:
            print(f"⚠️  Only {total_words} words extracted. Attempting OCR on key pages...", file=sys.stderr)

        # Determine OCR language
        language = "eng"
        if language_prompt_fn is not None:
            language = language_prompt_fn() or "eng"

        # OCR first 3 + last 2 pages (or all if short doc)
        if num_pages <= 5:
            pages_spec = None
        else:
            first_pages = "1-3"
            last_pages = f"{num_pages-1}-{num_pages}"
            pages_spec = f"{first_pages},{last_pages}"

        ocr_result = run_ocr(pdf_path, pages_spec, language=language)

        if ocr_result is True:
            if not quiet:
                print("✓ OCR successful", file=sys.stderr)
            result, num_pages = extract_all_text(pdf_path)
            if isinstance(result, str) and result.startswith("Error:"):
                return result
            page_texts = result
            full_text = "\n\n".join(page_texts)
            words = split_into_words(full_text)
            total_words = len(words)
        else:
            return f"Error: {ocr_result}"

    # Determine beginning section: max(first page, min_first_words)
    first_page_text = page_texts[0] if page_texts else ""
    first_page_word_count = len(split_into_words(first_page_text))

    if first_page_word_count >= min_first_words:
        # First page is long enough, use it entirely
        first_section = first_page_text.strip()
    else:
        # First page is short, take min_first_words (snap to sentence)
        first_section = snap_to_sentence_end(full_text, min_first_words, from_end=False)

    first_count = len(split_into_words(first_section))

    # Short documents: return everything
    if total_words <= first_count + last_words:
        return f"--- FULL TEXT ({total_words} words) ---\n{full_text.strip()}"

    # Extract last M words (snap to sentence)
    last_section = snap_to_sentence_end(full_text, last_words, from_end=True)
    last_count = len(split_into_words(last_section))

    output = [
        f"--- BEGINNING ({first_count} words) ---",
        first_section,
        f"\n--- END ({last_count} words) ---",
        last_section
    ]

    return "\n".join(output)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pages.py <pdf_file>", file=sys.stderr)
        sys.exit(1)
    
    result = extract_content(sys.argv[1])
    print(result)
