import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Book
from app.services.pdf_service import extract_text_from_pdf


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

        text, page_count = extract_text_from_pdf(file_path)

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
