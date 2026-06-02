import logging
import os
import shutil
import tempfile

import fitz
import pytesseract

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_text_with_tesseract(doc: fitz.Document, start_page: int) -> str:
    """OCR fallback for image-only/scanned PDFs."""
    if not shutil.which("tesseract"):
        logger.warning("Tesseract OCR fallback skipped: tesseract binary not found")
        return ""

    text_parts = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for page_num in range(start_page - 1, len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = os.path.join(tmpdir, f"page-{page_num + 1}.png")
            pix.save(image_path)
            try:
                page_text = pytesseract.image_to_string(image_path, lang="eng")
            except Exception as exc:
                logger.warning("Tesseract OCR failed on page %s: %s", page_num + 1, exc)
                page_text = ""
            text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_pdf(file_path: str, start_page: int = 1) -> tuple[str, int]:
    full_path = os.path.join(settings.STORAGE_ROOT, file_path)

    doc = fitz.open(full_path)
    page_count = len(doc)

    text_parts = []
    for page_num in range(start_page - 1, page_count):
        page = doc[page_num]
        page_text = page.get_text("text", sort=True)
        text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    if len(full_text.strip()) < 50:
        ocr_text = _extract_text_with_tesseract(doc, start_page)
        if len(ocr_text.strip()) > len(full_text.strip()):
            full_text = ocr_text

    doc.close()

    return full_text, page_count
