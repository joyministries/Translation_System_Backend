from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, BookImage, Exam, AnswerKey
from app.models.translation import Translation, TranslationJob
from app.utils.file_utils import save_upload_stream_securely, save_image_upload_stream_securely
from app.services.document_conversion_service import CONVERTIBLE_TO_DOCX_MIME_TYPES, DOCX_MIME
from app.utils.security import require_role
from app.models.user import User


router = APIRouter(prefix="/books", tags=["Books Management"])


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    images: list[UploadFile] | None = File(None),
    title: str = Form(""),
    subject: str | None = Form(None),
    first_content_page: int = Form(1),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Upload a book (PDF, DOC, DOCX).
    - content_type: 'book' (default) - for study materials
    - For exams, use /admin/exams/import instead
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        filename, mime_type, file_size_bytes = await save_upload_stream_securely(file)
    except ValueError as exc:
        detail = str(exc)
        if detail == "Empty file":
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF, DOC, DOCX allowed.",
        ) from exc

    book_title = title or file.filename
    existing = db.query(Book).filter(Book.title == book_title).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Book already exists: '{book_title}'")

    book = Book(
        title=book_title,
        subject=subject,
        file_path=filename,
        normalized_docx_path=filename if mime_type == DOCX_MIME else None,
        normalized_source_type=mime_type,
        normalization_status="done" if mime_type == DOCX_MIME else ("pending" if mime_type in CONVERTIBLE_TO_DOCX_MIME_TYPES else None),
        file_size_bytes=file_size_bytes,
        uploaded_by=None,
        extraction_status="pending",
        first_content_page=first_content_page,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    attached_images = []
    for image in images or []:
        if not image or not image.filename:
            continue
        try:
            image_filename, image_mime_type, image_size_bytes, original_filename = await save_image_upload_stream_securely(image)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image upload: {exc}") from exc
        book_image = BookImage(
            book_id=book.id,
            file_path=image_filename,
            original_filename=original_filename,
            mime_type=image_mime_type,
            file_size_bytes=image_size_bytes,
        )
        db.add(book_image)
        attached_images.append(book_image)
    if attached_images:
        db.commit()

    if mime_type == "application/pdf":
        from app.tasks.ingestion_tasks import extract_pdf_text

        extract_pdf_text.delay(str(book.id), filename)
        message = "Book uploaded. Conversion to DOCX and extraction in progress."
    elif mime_type in CONVERTIBLE_TO_DOCX_MIME_TYPES:
        from app.tasks.ingestion_tasks import extract_doc_text

        extract_doc_text.delay(str(book.id), filename)
        message = "Book uploaded. DOCX normalization and extraction in progress."
    else:
        message = "Book uploaded successfully."

    return {
        "id": str(book.id),
        "title": book.title,
        "status": "pending",
        "message": message,
        "image_count": len(attached_images),
        "images": [
            {
                "id": str(img.id),
                "original_filename": img.original_filename,
                "mime_type": img.mime_type,
            }
            for img in attached_images
        ],
    }


@router.get("/")
def list_books(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book, exam, or answer_key"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Book).order_by(desc(Book.created_at))

    total = query.count()
    books = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "books": [
            {
                "id": str(b.id),
                "title": b.title,
                "subject": b.subject,
                "page_count": b.page_count,
                "content_type": "book",
                "image_count": len(getattr(b, "images", []) or []),
                "extraction_status": b.extraction_status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in books
        ],
    }


@router.delete("/{book_id}")
def delete_book(
    book_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    exam_ids = [row[0] for row in db.query(Exam.id).filter(Exam.book_id == book.id).all()]
    translation_ids = [
        row[0]
        for row in db.query(Translation.id)
        .filter(
            or_(
                (Translation.content_type == "book") & (Translation.content_id == book.id),
                (Translation.content_type == "exam") & (Translation.content_id.in_(exam_ids or [book.id])),
            )
        )
        .all()
    ]

    if translation_ids:
        db.query(TranslationJob).filter(TranslationJob.translation_id.in_(translation_ids)).delete(
            synchronize_session=False
        )
        db.query(Translation).filter(Translation.id.in_(translation_ids)).delete(
            synchronize_session=False
        )

    if exam_ids:
        db.query(AnswerKey).filter(AnswerKey.exam_id.in_(exam_ids)).delete(
            synchronize_session=False
        )
        db.query(Exam).filter(Exam.id.in_(exam_ids)).delete(synchronize_session=False)

    db.query(AnswerKey).filter(AnswerKey.book_id == book.id).delete(synchronize_session=False)
    db.delete(book)
    db.commit()

    return {"message": "Book deleted"}


@router.post("/{book_id}/images")
async def upload_book_images(
    book_id: str,
    images: list[UploadFile] = File(...),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    created = []
    for image in images:
        if not image.filename:
            continue
        try:
            image_filename, image_mime_type, image_size_bytes, original_filename = await save_image_upload_stream_securely(image)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image upload: {exc}") from exc
        book_image = BookImage(
            book_id=book.id,
            file_path=image_filename,
            original_filename=original_filename,
            mime_type=image_mime_type,
            file_size_bytes=image_size_bytes,
        )
        db.add(book_image)
        created.append(book_image)
    db.commit()

    return {
        "book_id": str(book.id),
        "image_count": len(created),
        "images": [
            {
                "id": str(img.id),
                "original_filename": img.original_filename,
                "mime_type": img.mime_type,
            }
            for img in created
        ],
    }
