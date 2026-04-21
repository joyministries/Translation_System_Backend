import logging
import os

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Book
from app.services.pdf_service import extract_text_from_pdf
from app.utils.file_utils import get_file_path


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def extract_pdf_text(self, book_id: str, file_path: str):
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            logger.error(f"Book not found: {book_id}")
            return {"status": "error", "message": "Book not found"}

        book.extraction_status = "processing"
        db.commit()

        start_page = book.first_content_page or 1
        text, page_count = extract_text_from_pdf(file_path, start_page=start_page)

        book.extracted_text = text
        book.page_count = page_count
        book.extraction_status = "done"
        db.commit()

        logger.info(f"PDF extracted successfully: {book_id}, pages: {page_count}")
        return {"status": "success", "book_id": book_id, "pages": page_count}

    except Exception as exc:
        logger.error(f"PDF extraction failed for {book_id}: {exc}")
        if book:
            book.extraction_status = "failed"
            db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def extract_doc_text(self, book_id: str, file_path: str):
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            logger.error(f"Book not found: {book_id}")
            return {"status": "error", "message": "Book not found"}

        book.extraction_status = "processing"
        db.commit()

        full_path = get_file_path(file_path)
        start_page = book.first_content_page or 1

        cover_text = ""
        content_text = ""

        if file_path.endswith(".docx"):
            from docx import Document

            doc = Document(full_path)
            all_paragraphs = [
                para.text.strip() for para in doc.paragraphs if para.text.strip()
            ]

            if start_page > 1:
                cover_paragraphs = all_paragraphs[:10]
                content_paragraphs = all_paragraphs[10:]
                cover_text = "\n".join(cover_paragraphs)
                content_text = "\n".join(content_paragraphs)
            else:
                content_text = "\n".join(all_paragraphs)

            # Generate cover page image using LibreOffice + fitz
            try:
                import subprocess, tempfile, os, fitz
                cover_img_path = full_path.replace(".docx", "_cover.png")
                with tempfile.TemporaryDirectory() as tmpdir:
                    r = subprocess.run(
                        ["libreoffice", "--headless", "--convert-to", "pdf",
                         "--outdir", tmpdir, full_path],
                        capture_output=True, timeout=90
                    )
                    pdf_files = [f for f in os.listdir(tmpdir) if f.endswith(".pdf")]
                    if pdf_files:
                        pdf_doc = fitz.open(os.path.join(tmpdir, pdf_files[0]))
                        pix = pdf_doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
                        pix.save(cover_img_path)
                        logger.info(f"Cover image saved: {cover_img_path}")
            except Exception as e:
                logger.warning(f"Cover image generation failed: {e}")

        elif file_path.endswith(".doc"):
            full_text = extract_doc_as_text(full_path)
            lines = [line.strip() for line in full_text.split("\n") if line.strip()]

            if start_page > 1:
                cover_lines = lines[:30]
                content_lines = lines[30:]
                cover_text = "\n".join(cover_lines)
                content_text = "\n".join(content_lines)
            else:
                content_text = "\n".join(lines)

        book.extracted_text = content_text
        book.extracted_cover_text = cover_text if cover_text else None
        book.page_count = None
        book.extraction_status = "done"
        db.commit()

        logger.info(f"DOC extracted successfully: {book_id}")
        return {"status": "success", "book_id": book_id}

    except Exception as exc:
        logger.error(f"DOC extraction failed for {book_id}: {exc}")
        if book:
            book.extraction_status = "failed"
            db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


def extract_doc_as_text(doc_path: str) -> str:
    import subprocess

    result = subprocess.run(
        ["catdoc", doc_path], capture_output=True, text=True, timeout=60
    )

    if result.returncode == 0:
        return result.stdout

    logger.warning(
        f"catdoc failed, return code: {result.returncode}, stderr: {result.stderr}"
    )
    return ""
