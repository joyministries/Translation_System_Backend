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
    password: str | None = None
    role: str
    institution_id: str | None = None
    use_temp_password: bool = False
    first_name: str | None = None
    last_name: str | None = None


@router.post("")
def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if request.role not in ["student", "teacher", "admin", "translator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    existing = AuthService.get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    inst_id = None
    if request.institution_id:
        try:
            inst_id = uuid.UUID(request.institution_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid institution_id")

    if request.use_temp_password or not request.password:
        user, temp_password = AuthService.register_with_temp_password(db, request.email, request.role, inst_id)
    else:
        user = AuthService.register(db, request.email, request.password, request.role, inst_id)
        temp_password = None

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "temp_password": temp_password,
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
