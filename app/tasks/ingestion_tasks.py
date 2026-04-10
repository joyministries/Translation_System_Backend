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

        text = ""
        if file_path.endswith(".docx"):
            from docx import Document

            doc = Document(full_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif file_path.endswith(".doc"):
            text = extract_doc_as_text(full_path)

        book.extracted_text = text
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
