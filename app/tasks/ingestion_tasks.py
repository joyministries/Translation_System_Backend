import logging
import os

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Book
from app.services.pdf_service import extract_text_from_pdf
from app.services.document_conversion_service import normalize_upload_to_docx
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

        normalized_docx, normalization_error = normalize_upload_to_docx(file_path, "application/pdf")
        book.normalized_docx_path = normalized_docx
        book.normalized_source_type = "application/pdf"
        book.normalization_status = "done" if normalized_docx else "failed"
        book.normalization_error = normalization_error

        if not normalized_docx:
            book.extraction_status = "failed"
            db.commit()
            raise RuntimeError(f"PDF-to-DOCX normalization failed: {normalization_error or 'unknown error'}")

        from app.services.docx_translation_service import extract_docx_translation_text
        with open(get_file_path(normalized_docx), "rb") as docx_file:
            text = extract_docx_translation_text(docx_file.read())
        page_count = None

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
        cover_text = ""
        content_text = ""

        if file_path.endswith(".docx"):
            source_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif file_path.endswith(".odt"):
            source_mime = "application/vnd.oasis.opendocument.text"
        elif file_path.endswith(".rtf"):
            source_mime = "application/rtf"
        else:
            source_mime = "application/msword"
        normalized_docx, normalization_error = normalize_upload_to_docx(file_path, source_mime)
        book.normalized_docx_path = normalized_docx
        book.normalized_source_type = source_mime
        book.normalization_status = "done" if normalized_docx else "failed"
        book.normalization_error = normalization_error

        if normalized_docx:
            from app.services.docx_translation_service import extract_docx_translation_text

            normalized_full_path = get_file_path(normalized_docx)
            with open(normalized_full_path, "rb") as docx_file:
                content_text = extract_docx_translation_text(docx_file.read())
            cover_text = None

            # Generate cover image + full PDF using LibreOffice
            try:
                import subprocess, tempfile, os, fitz
                cover_img_path = normalized_full_path.replace(".docx", "_cover.png")
                pdf_out_path = normalized_full_path.replace(".docx", ".pdf")
                with tempfile.TemporaryDirectory() as tmpdir:
                    r = subprocess.run(
                        ["libreoffice", "--headless", "--convert-to", "pdf",
                         "--outdir", tmpdir, normalized_full_path],
                        capture_output=True, timeout=90
                    )
                    pdf_files = [f for f in os.listdir(tmpdir) if f.endswith(".pdf")]
                    if pdf_files:
                        import shutil
                        shutil.copy(os.path.join(tmpdir, pdf_files[0]), pdf_out_path)
                        pdf_doc = fitz.open(pdf_out_path)
                        pix = pdf_doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
                        pix.save(cover_img_path)
                        logger.info(f"Cover image + PDF saved for {book_id}")
            except Exception as e:
                logger.warning(f"Cover image generation failed: {e}")
        elif file_path.endswith(".doc"):
            start_page = book.first_content_page or 1
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
