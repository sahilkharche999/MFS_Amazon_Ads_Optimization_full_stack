# ============================================================
# manuscript_parser.py — PDF & DOCX Text Extraction
# Social Media Asset Generation Module
# ============================================================

import logging
import io

logger = logging.getLogger("social_media.manuscript_parser")

# Maximum characters to send to AI (approx 12k tokens)
MAX_CHARS = 48_000


def extract_text(file_bytes: bytes, filename: str = "") -> str:
    """
    Extract plain text from a PDF or DOCX file's bytes.
    Returns the combined text, truncated to MAX_CHARS.
    """
    ext = filename.split(".")[-1].lower() if filename else ""
    
    # Try to detect if it's a PDF by signature if filename is missing
    if not ext and file_bytes.startswith(b"%PDF"):
        ext = "pdf"
    
    if ext == "pdf" or (not ext and file_bytes.startswith(b"%PDF")):
        return _extract_from_pdf(file_bytes)
    elif ext == "docx" or (not ext and file_bytes.startswith(b"PK\x03\x04")): # Zip signature for docx
        return _extract_from_docx(file_bytes)
    else:
        # Fallback: try PDF first, then DOCX
        try:
            return _extract_from_pdf(file_bytes)
        except:
            try:
                return _extract_from_docx(file_bytes)
            except:
                raise RuntimeError(f"Unsupported file format or extraction failed. Please upload a PDF or DOCX file.")


def _extract_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            if page_text.strip():
                texts.append(page_text.strip())
        doc.close()
        return _clean_and_truncate("\n\n".join(texts))
    except Exception as e:
        raise RuntimeError(f"PDF parsing failed: {str(e)}")


def _extract_from_docx(docx_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("python-docx is not installed.")

    try:
        doc = Document(io.BytesIO(docx_bytes))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        return _clean_and_truncate("\n\n".join(texts))
    except Exception as e:
        raise RuntimeError(f"DOCX parsing failed: {str(e)}")


def _clean_and_truncate(full_text: str) -> str:
    if len(full_text) > MAX_CHARS:
        logger.warning(f"Text truncated from {len(full_text)} to {MAX_CHARS} characters")
        return full_text[:MAX_CHARS] + "\n\n[... manuscript continues ...]"
    return full_text
