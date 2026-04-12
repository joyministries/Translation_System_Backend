from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Institution
from app.utils.security import require_role
from app.models.user import User


router = APIRouter(prefix="/institutions", tags=["Institutions Management"])


@router.get("")
def list_institutions(
    skip: int = 0,
    limit: int = 20,
    search: str | None = Query(None, description="Search by name or code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Institution)

    if search:
        query = query.filter(
            (Institution.name.ilike(f"%{search}%"))
            | (Institution.code.ilike(f"%{search}%"))
        )

    total = query.count()
    institutions = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(i.id),
                "name": i.name,
                "code": i.code,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in institutions
        ],
    }
