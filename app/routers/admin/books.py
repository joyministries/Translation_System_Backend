from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book
from app.utils.file_utils import validate_mime_type, save_upload_securely
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

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    mime_type = validate_mime_type(file_bytes, file.filename or "")
    if not mime_type:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDF, DOC, DOCX allowed."
        )

    filename = save_upload_securely(file_bytes, mime_type)

    book = Book(
        title=title or file.filename,
        subject=subject,
        file_path=filename,
        file_size_bytes=len(file_bytes),
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
    query = db.query(Book)

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
def delete_book(book_id: str, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()

    return {"message": "Book deleted"}
