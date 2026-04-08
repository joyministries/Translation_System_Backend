import os

import fitz

from app.config import settings


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    full_path = os.path.join(settings.STORAGE_ROOT, file_path)

    doc = fitz.open(full_path)
    page_count = len(doc)

    text_parts = []
    for page in doc:
        page_text = page.get_text("text", sort=True)
        text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    doc.close()

    return full_text, page_count
