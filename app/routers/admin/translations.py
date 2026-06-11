from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Translation, TranslationJob
from app.models.book import Book
from app.utils.security import require_role, get_current_user
from app.models.user import User
from app.services.translation_service import TranslationService


router = APIRouter(prefix="/translations", tags=["admin", "translations"])


@router.get("/stats")
def get_translation_stats(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.models import Language

    total = db.query(func.count(Translation.id)).scalar() or 0

    # Status breakdown
    done = (
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
    processing = (
        db.query(func.count(Translation.id))
        .filter(Translation.status == "processing")
        .scalar()
        or 0
    )

    # Calculate success rate
    success_rate = round((done / total * 100), 1) if total > 0 else 0

    # By content type
    book_count = (
        db.query(func.count(Translation.id))
        .filter(Translation.content_type == "book")
        .scalar()
        or 0
    )
    exam_count = (
        db.query(func.count(Translation.id))
        .filter(Translation.content_type == "exam")
        .scalar()
        or 0
    )

    # Top language pairs
    language_pairs = (
        db.query(
            Language.name.label("target_language"),
            func.count(Translation.id).label("count"),
        )
        .join(Translation, Translation.language_id == Language.id)
        .group_by(Language.name)
        .order_by(func.count(Translation.id).desc())
        .limit(5)
        .all()
    )

    # Recent failed translations
    recent_failures = (
        db.query(Translation)
        .filter(Translation.status == "failed")
        .order_by(Translation.created_at.desc())
        .limit(5)
        .all()
    )

    failure_details = []
    for f in recent_failures:
        src_lang = (
            db.query(Language).filter(Language.id == f.source_language_id).first()
        )
        tgt_lang = db.query(Language).filter(Language.id == f.language_id).first()
        failure_details.append(
            {
                "id": str(f.id),
                "content_type": f.content_type,
                "source_language": src_lang.name if src_lang else "Unknown",
                "target_language": tgt_lang.name if tgt_lang else "Unknown",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
        )

    # Jobs stats
    jobs_total = db.query(func.count(TranslationJob.id)).scalar() or 0
    jobs_active = (
        db.query(func.count(TranslationJob.id))
        .filter(TranslationJob.completed_at == None)
        .scalar()
        or 0
    )
    jobs_failed = (
        db.query(func.count(TranslationJob.id))
        .filter(TranslationJob.error_message != None)
        .scalar()
        or 0
    )

    # This month stats
    from datetime import datetime, timedelta

    month_start = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    monthly_total = (
        db.query(func.count(Translation.id))
        .filter(Translation.created_at >= month_start)
        .scalar()
        or 0
    )
    monthly_completed = (
        db.query(func.count(Translation.id))
        .filter(Translation.status == "done", Translation.created_at >= month_start)
        .scalar()
        or 0
    )

    return {
        "overview": {
            "total_translations": total,
            "success_rate": f"{success_rate}%",
            "this_month": {
                "total": monthly_total,
                "completed": monthly_completed,
            },
        },
        "by_status": {
            "completed": done,
            "pending": pending,
            "processing": processing,
            "failed": failed,
        },
        "by_content_type": {
            "books": book_count,
            "exams": exam_count,
        },
        "top_languages": [
            {"language": pair.target_language, "count": pair.count}
            for pair in language_pairs
        ],
        "recent_failures": failure_details,
        "jobs": {
            "total": jobs_total,
            "active": jobs_active,
            "failed": jobs_failed,
        },
    }


@router.get("")
def list_translations(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Translation)
    if status:
        query = query.filter(Translation.status == status)

    total = query.count()
    translations = (
        query.order_by(Translation.created_at.desc()).offset(skip).limit(limit).all()
    )

    from app.models import Language

    results = []
    for t in translations:
        source_lang = (
            db.query(Language).filter(Language.id == t.source_language_id).first()
        )
        target_lang = db.query(Language).filter(Language.id == t.language_id).first()

        results.append(
            {
                "id": str(t.id),
                "content_type": t.content_type,
                "content_id": str(t.content_id),
                "source_language": source_lang.name if source_lang else None,
                "target_language": target_lang.name if target_lang else None,
                "status": t.status,
                "chunk_count": t.chunk_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "output_format": t.output_format,
            }
        )

    return {"total": total, "translations": results}


@router.get("/failed")
def list_failed_translations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.models import Book, Exam, Language

    query = db.query(Translation).filter(Translation.status == "failed")
    total = query.count()
    translations = (
        query.order_by(Translation.created_at.desc()).offset(skip).limit(limit).all()
    )

    results = []
    for t in translations:
        source_lang = (
            db.query(Language).filter(Language.id == t.source_language_id).first()
        )
        target_lang = db.query(Language).filter(Language.id == t.language_id).first()

        content_title = None
        if t.content_type == "book":
            book = db.query(Book).filter(Book.id == str(t.content_id)).first()
            content_title = book.title if book else None
        elif t.content_type == "exam":
            exam = db.query(Exam).filter(Exam.id == str(t.content_id)).first()
            content_title = exam.title if exam else None

        results.append(
            {
                "id": str(t.id),
                "content_type": t.content_type,
                "content_id": str(t.content_id),
                "content_title": content_title,
                "source_language": source_lang.name if source_lang else None,
                "target_language": target_lang.name if target_lang else None,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "chunk_count": t.chunk_count,
                "output_format": t.output_format,
            }
        )

    return {"total": total, "failed_translations": results}


@router.get("/{translation_id}")
def get_translation_detail(
    translation_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    import uuid

    try:
        trans_uuid = uuid.UUID(translation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid translation_id format")

    translation = db.query(Translation).filter(Translation.id == trans_uuid).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    from app.models import Language

    source_lang = (
        db.query(Language).filter(Language.id == translation.source_language_id).first()
    )
    target_lang = (
        db.query(Language).filter(Language.id == translation.language_id).first()
    )

    return {
        "id": str(translation.id),
        "content_type": translation.content_type,
        "content_id": str(translation.content_id),
        "source_language": source_lang.name if source_lang else None,
        "target_language": target_lang.name if target_lang else None,
        "status": translation.status,
        "translated_text": translation.translated_text,
        "chunk_count": translation.chunk_count,
        "created_at": translation.created_at.isoformat()
        if translation.created_at
        else None,
    }


@router.get("/{translation_id}/download")
def download_translation(
    translation_id: str,
    format: str = "pdf",
    cache_variant: str | None = Query(
        None,
        pattern=r"^[A-Za-z0-9_-]{1,40}$",
        description="Optional suffix for writing/reading a separate cached PDF variant.",
    ),
    refresh_cache: bool = False,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    import uuid
    try:
        trans_uuid = uuid.UUID(translation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid translation_id format")
    translation = TranslationService.get_translation(db, trans_uuid)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    if translation.status != "done":
        raise HTTPException(status_code=400, detail="Translation not complete yet")
    # Use the same rendering logic as the student endpoint
    from app.routers.student.translate import download_translation as _student_dl
    return _student_dl(
        translation_id=translation_id,
        format=format,
        cache_variant=cache_variant,
        refresh_cache=refresh_cache,
        current_user=current_user,
        db=db,
    )


@router.post("/translate")
def admin_trigger_translation(
    content_type: str = "book",
    content_id: str = None,
    language_id: int = None,
    source_language_id: int = 21,
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
        if (book.file_path or "").lower().endswith(".pdf"):
            normalized_docx_path = getattr(book, "normalized_docx_path", None)
            if not (normalized_docx_path and normalized_docx_path.lower().endswith(".docx") and getattr(book, "normalization_status", None) == "done"):
                raise HTTPException(status_code=409, detail="PDF book is not ready: DOCX normalization is required before translation")

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
