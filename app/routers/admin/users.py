import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Book, Exam, AnswerKey
from app.models.translation import TranslationJob
from app.utils.security import require_role
from app.services.auth_service import AuthService
from app.utils.security import get_password_hash


router = APIRouter(prefix="/users", tags=["User Management"])


class CreateUserRequest(BaseModel):
    email: str
    full_name: str | None = None
    password: str | None = None
    role: str
    institution_id: str | None = None
    use_temp_password: bool = False


class UpdateUserRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    institution_id: str | None = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str | None = None


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
        user, temp_password = AuthService.register_with_temp_password(
            db, request.email, request.role, inst_id, request.full_name
        )
    else:
        user = AuthService.register(
            db, request.email, request.password, request.role, inst_id, request.full_name
        )
        temp_password = None

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
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
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.put("/{user_id}")
def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.role is not None and request.role not in ["student", "teacher", "admin", "translator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if request.email is not None and request.email != user.email:
        existing = AuthService.get_user_by_email(db, request.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = request.email

    if request.full_name is not None:
        user.full_name = request.full_name

    if request.role is not None:
        user.role = request.role

    if request.is_active is not None:
        user.is_active = request.is_active

    if request.institution_id:
        try:
            user.institution_id = uuid.UUID(request.institution_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid institution_id")
    else:
        user.institution_id = None

    db.commit()
    db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "institution_id": str(user.institution_id) if user.institution_id else None,
        "must_change_password": user.must_change_password,
    }


@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: str,
    request: AdminResetPasswordRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = request.new_password or AuthService.generate_temp_password()
    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = True
    db.commit()

    return {
        "message": "Password reset successfully",
        "temporary_password": new_password,
        "must_change_password": True,
    }


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(Book).filter(Book.uploaded_by == user_uuid).update(
        {"uploaded_by": None}, synchronize_session=False
    )
    db.query(Exam).filter(Exam.uploaded_by == user_uuid).update(
        {"uploaded_by": None}, synchronize_session=False
    )
    db.query(AnswerKey).filter(AnswerKey.uploaded_by == user_uuid).update(
        {"uploaded_by": None}, synchronize_session=False
    )
    db.query(TranslationJob).filter(TranslationJob.requested_by == user_uuid).update(
        {"requested_by": None}, synchronize_session=False
    )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}
