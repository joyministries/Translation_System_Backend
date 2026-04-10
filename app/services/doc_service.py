import os
import logging

from docx import Document
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import io

from app.config import settings
from app.utils.file_utils import get_file_path

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_path: str) -> str:
    full_path = get_file_path(file_path)
    doc = Document(full_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text_from_doc(file_path: str) -> str:
    import subprocess

    full_path = get_file_path(file_path)
    result = subprocess.run(
        ["catdoc", full_path], capture_output=True, text=True, timeout=60
    )

    if result.returncode == 0:
        return result.stdout
    logger.warning(f"catdoc failed: {result.stderr}")
    return ""


def translate_excel(original_file_path: str, translations: dict[int, str]) -> bytes:
    full_path = get_file_path(original_file_path)
    wb = load_workbook(full_path)
    ws = wb.active

    for row_idx, col_idx in translations:
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.value = translations[(row_idx, col_idx)]

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def create_translated_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    paragraphs = text.split("\n")
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para, styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def create_translated_docx(text: str) -> bytes:
    doc = Document()
    for para in text.split("\n"):
        if para.strip():
            doc.add_paragraph(para)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
