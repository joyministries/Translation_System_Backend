from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
    MessageResponse,
    ChangePasswordRequest,
)
from app.services.auth_service import AuthService
from app.utils.security import (
    get_current_user,
    require_role,
    decode_token,
    verify_password,
    get_password_hash,
)
from app.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = AuthService.authenticate(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token, refresh_token = AuthService.create_tokens(user)
    AuthService.update_last_login(db, user.id)

    if user.must_change_password:
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            must_change_password=True,
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if AuthService.is_token_blacklisted(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token, refresh_token = AuthService.create_tokens(user)

    AuthService.blacklist_token(request.refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: RefreshRequest,
    current_user: User = Depends(
        require_role("admin", "teacher", "student", "translator")
    ),
    db: Session = Depends(get_db),
):
    AuthService.blacklist_token(request.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    request: RegisterRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = AuthService.get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    institution_uuid = None
    if request.institution_id:
        try:
            institution_uuid = uuid.UUID(request.institution_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid institution_id format",
            )

    if request.use_temp_password:
        user, _ = AuthService.register_with_temp_password(
            db,
            request.email,
            request.role,
            institution_uuid,
        )
    else:
        user = AuthService.register(
            db,
            request.email,
            request.password,
            request.role,
            institution_uuid,
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        institution_id=str(user.institution_id) if user.institution_id else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(
        require_role("admin", "teacher", "student", "translator")
    ),
):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        institution_id=str(current_user.institution_id)
        if current_user.institution_id
        else None,
        last_login_at=current_user.last_login_at.isoformat()
        if current_user.last_login_at
        else None,
        must_change_password=current_user.must_change_password,
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(
        require_role("admin", "teacher", "student", "translator")
    ),
    db: Session = Depends(get_db),
):
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.must_change_password = False
    db.commit()

    return MessageResponse(message="Password changed successfully")
