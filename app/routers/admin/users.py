import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils.security import require_role
from app.services.auth_service import AuthService


router = APIRouter(prefix="/users", tags=["User Management"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str
    institution_id: str | None = None


@router.post("")
def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    email = request.email
    password = request.password
    role = request.role
    institution_id = request.institution_id
    if role not in ["student", "teacher", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    existing = AuthService.get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    inst_id = None
    if institution_id:
        try:
            inst_id = uuid.UUID(institution_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid institution_id")

    user = AuthService.register(db, email, password, role, inst_id)

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
    }


@router.get("")
def list_users(
    skip: int = 0,
    limit: int = 20,
    role: str | None = None,
    institution_id: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if institution_id:
        try:
            inst_uuid = uuid.UUID(institution_id)
            query = query.filter(User.institution_id == inst_uuid)
        except ValueError:
            pass

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "institution_id": str(u.institution_id) if u.institution_id else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }
