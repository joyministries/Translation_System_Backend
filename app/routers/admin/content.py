import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Book, Exam, AnswerKey, Language
from app.utils.security import require_role
from app.models.user import User
from app.services.auth_service import AuthService


router = APIRouter(prefix="/content", tags=["Content Management"])


@router.get("")
def list_all_content(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book, exam, or answer_key"
    ),
    institution_id: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    results = []
    total = 0

    content_type = content_type.lower() if content_type else None

    if content_type is None or content_type == "book":
        query = db.query(Book)
        if institution_id:
            query = query.filter(Book.institution_id == institution_id)
        query = query.order_by(desc(Book.created_at))
        if content_type == "book":
            total = query.count()
        books = query.offset(skip).limit(limit).all()
        for b in books:
            results.append(
                {
                    "id": str(b.id),
                    "title": b.title,
                    "subject": b.subject,
                    "grade_level": b.grade_level,
                    "page_count": b.page_count,
                    "content_type": "book",
                    "extraction_status": b.extraction_status,
                    "institution_name": b.institution.name if b.institution else None,
                    "institution_id": str(b.institution_id)
                    if b.institution_id
                    else None,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
            )

    if content_type is None or content_type == "exam":
        query = db.query(Exam)
        if institution_id:
            query = query.filter(Exam.institution_id == institution_id)
        query = query.order_by(desc(Exam.created_at))
        if content_type == "exam":
            total = query.count()
        exams = query.offset(skip).limit(limit).all()
        for e in exams:
            results.append(
                {
                    "id": str(e.id),
                    "title": e.title,
                    "content_type": "exam",
                    "sheet_names": e.raw_data.get("sheet_names", [])
                    if e.raw_data
                    else [],
                    "institution_name": e.institution.name if e.institution else None,
                    "institution_id": str(e.institution_id)
                    if e.institution_id
                    else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )

    if content_type is None or content_type == "answer_key":
        query = db.query(AnswerKey)
        if institution_id:
            query = query.filter(AnswerKey.institution_id == institution_id)
        query = query.order_by(desc(AnswerKey.created_at))
        if content_type == "answer_key":
            total = query.count()
        answer_keys = query.offset(skip).limit(limit).all()
        for ak in answer_keys:
            results.append(
                {
                    "id": str(ak.id),
                    "title": ak.title,
                    "content_type": "answer_key",
                    "institution_name": ak.institution.name if ak.institution else None,
                    "institution_id": str(ak.institution_id)
                    if ak.institution_id
                    else None,
                    "created_at": ak.created_at.isoformat() if ak.created_at else None,
                }
            )

    if content_type is None:
        total = (
            db.query(Book).count()
            + db.query(Exam).count()
            + db.query(AnswerKey).count()
        )
    results = results[:limit]

    return {
        "total": total,
        "content": results,
    }


@router.get("/languages")
def list_languages(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("admin")),
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
    content_type: str | None = Query(
        None, description="Filter by content_type: book or exam"
    ),
    institution_id: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Book)
    if institution_id:
        query = query.filter(Book.institution_id == institution_id)

    total = query.count()
    books = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "books": [
            {
                "id": str(b.id),
                "title": b.title,
                "subject": b.subject,
                "grade_level": b.grade_level,
                "page_count": b.page_count,
                "content_type": "book",
            }
            for b in books
        ],
    }


@router.get("/books/{book_id}")
def get_book(
    book_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.models import Institution

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
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
        "content_type": "book",
        "institution": {"name": institution.name} if institution else None,
    }


@router.get("/exams")
def list_exams(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book or exam"
    ),
    institution_id: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Exam)
    if institution_id:
        query = query.filter(Exam.institution_id == institution_id)

    total = query.count()
    exams = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "exams": [
            {
                "id": str(e.id),
                "title": e.title,
                "file_path": e.file_path,
                "content_type": "exam",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exams
        ],
    }


@router.get("/exams/{exam_id}")
def get_exam(
    exam_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return {
        "id": str(exam.id),
        "title": exam.title,
        "file_path": exam.file_path,
        "content_type": "exam",
        "raw_data": exam.raw_data,
    }


@router.get("/answer-keys")
def list_answer_keys(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book or exam"
    ),
    institution_id: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(AnswerKey)
    if institution_id:
        query = query.filter(AnswerKey.institution_id == institution_id)

    total = query.count()
    answer_keys = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "answer_keys": [
            {
                "id": str(ak.id),
                "title": ak.title,
                "file_path": ak.file_path,
                "content_type": "answer_key",
                "created_at": ak.created_at.isoformat() if ak.created_at else None,
            }
            for ak in answer_keys
        ],
    }


@router.get("/answer-keys/{answer_key_id}")
def get_answer_key(
    answer_key_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    answer_key = db.query(AnswerKey).filter(AnswerKey.id == answer_key_id).first()
    if not answer_key:
        raise HTTPException(status_code=404, detail="Answer key not found")

    return {
        "id": str(answer_key.id),
        "title": answer_key.title,
        "file_path": answer_key.file_path,
        "content_type": "answer_key",
        "raw_data": answer_key.raw_data,
    }
