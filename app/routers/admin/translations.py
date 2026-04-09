from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Translation, TranslationJob
from app.utils.security import require_role, get_current_user
from app.models.user import User
from app.services.translation_service import TranslationService


router = APIRouter(prefix="/translations", tags=["admin", "translations"])


@router.get("/stats")
def get_translation_stats(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Translation.id)).scalar() or 0
    completed = (
        db.query(func.count(Translation.id))
        .filter(Translation.status == "done")
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(Translation.id))
        .filter(Translation.status == "pending")
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(Translation.id))
        .filter(Translation.status == "failed")
        .scalar()
        or 0
    )

    jobs_total = db.query(func.count(TranslationJob.id)).scalar() or 0

    return {
        "translations": {
            "total": total,
            "completed": completed,
            "pending": pending,
            "failed": failed,
        },
        "jobs": {
            "total": jobs_total,
        },
    }


@router.post("/translate")
def admin_trigger_translation(
    content_type: str = "book",
    content_id: str = None,
    language_id: int = None,
    source_language_id: int = 1,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if not content_id or not language_id:
        raise HTTPException(
            status_code=400, detail="content_id and language_id are required"
        )

    from app.models import Book, Exam
    import uuid

    if content_type == "book":
        book = db.query(Book).filter(Book.id == content_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if not book.extracted_text:
            raise HTTPException(status_code=400, detail="Book text not extracted yet")

        translation, task_id = TranslationService.get_or_create_translation(
            db,
            content_type="book",
            content_id=book.id,
            language_id=language_id,
            source_language_id=source_language_id,
            original_text=book.extracted_text,
        )
        return {
            "translation_id": str(translation.id),
            "status": translation.status,
            "task_id": task_id,
        }

    if content_type == "exam":
        exam = db.query(Exam).filter(Exam.id == content_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        if not exam.raw_data:
            raise HTTPException(status_code=400, detail="Exam has no data")

        import json

        exam_text = json.dumps(exam.raw_data)

        translation, task_id = TranslationService.get_or_create_translation(
            db,
            content_type="exam",
            content_id=exam.id,
            language_id=language_id,
            source_language_id=source_language_id,
            original_text=exam_text,
        )
        return {
            "translation_id": str(translation.id),
            "status": translation.status,
            "task_id": task_id,
        }

    raise HTTPException(status_code=400, detail="Unsupported content_type")
