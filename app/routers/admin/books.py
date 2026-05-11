from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Exam, AnswerKey
from app.models.translation import Translation, TranslationJob
from app.utils.file_utils import save_upload_stream_securely
from app.utils.security import require_role
from app.models.user import User


router = APIRouter(prefix="/books", tags=["Books Management"])


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: str = "",
    subject: str | None = None,
    first_content_page: int = 5,
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

    book = Book(
        title=title or file.filename,
        subject=subject,
        file_path=filename,
        file_size_bytes=file_size_bytes,
        uploaded_by=None,
        extraction_status="pending",
        first_content_page=first_content_page,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    if mime_type == "application/pdf":
        from app.tasks.ingestion_tasks import extract_pdf_text

        extract_pdf_text.delay(str(book.id), filename)
        message = "Book uploaded. PDF extraction in progress."
    elif mime_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        from app.tasks.ingestion_tasks import extract_doc_text

        extract_doc_text.delay(str(book.id), filename)
        message = "Book uploaded. DOC/DOCX extraction in progress."
    else:
        message = "Book uploaded successfully."

    return {
        "id": str(book.id),
        "title": book.title,
        "status": "pending",
        "message": message,
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
