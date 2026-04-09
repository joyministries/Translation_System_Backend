from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Translation, TranslationJob


router = APIRouter(prefix="/admin/translations", tags=["admin", "translations"])


@router.get("/stats")
def get_translation_stats(db: Session = Depends(get_db)):
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
