from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Exam, AnswerKey, Language
from app.utils.security import require_role
from app.models.user import User


router = APIRouter(prefix="/content", tags=["Student Content"])


@router.get("/languages")
def list_languages(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    languages = (
        db.query(Language)
        .filter(Language.is_active == True)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": len(languages),
        "languages": [
            {
                "id": lang.id,
                "name": lang.name,
                "code": lang.code,
                "native_name": lang.native_name,
            }
            for lang in languages
        ],
    }


@router.get("/books")
def list_books(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Book).filter(Book.extraction_status == "done")
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
            }
            for b in books
        ],
    }


@router.get("/books/{book_id}")
def get_book(
    book_id: str,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    from app.models import Institution

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Book not found")

    institution = None
    if book.institution_id:
        institution = (
            db.query(Institution).filter(Institution.id == book.institution_id).first()
        )

    return {
        "id": str(book.id),
        "title": book.title,
        "subject": book.subject,
        "grade_level": book.grade_level,
        "page_count": book.page_count,
        "extraction_status": book.extraction_status,
    }


@router.get("/exams")
def list_exams(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Exam)
    total = query.count()
    exams = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "exams": [
            {
                "id": str(e.id),
                "title": e.title,
                "file_path": e.file_path,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exams
        ],
    }


@router.get("/exams/{exam_id}")
def get_exam(
    exam_id: str,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Exam not found")

    return {
        "id": str(exam.id),
        "title": exam.title,
        "file_path": exam.file_path,
        "raw_data": exam.raw_data,
    }


@router.get("/answer-keys")
def list_answer_keys(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(AnswerKey)
    total = query.count()
    answer_keys = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "answer_keys": [
            {
                "id": str(ak.id),
                "title": ak.title,
                "file_path": ak.file_path,
                "created_at": ak.created_at.isoformat() if ak.created_at else None,
            }
            for ak in answer_keys
        ],
    }


@router.get("/answer-keys/{answer_key_id}")
def get_answer_key(
    answer_key_id: str,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    answer_key = db.query(AnswerKey).filter(AnswerKey.id == answer_key_id).first()
    if not answer_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Answer key not found")

    return {
        "id": str(answer_key.id),
        "title": answer_key.title,
        "file_path": answer_key.file_path,
        "raw_data": answer_key.raw_data,
    }
