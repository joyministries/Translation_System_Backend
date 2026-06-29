from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
import uuid
import logging

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
    MessageResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    PasswordResetConfirmRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.utils.security import (
    get_current_user,
    require_role,
    decode_token,
    verify_password,
    get_password_hash,
    touch_user_session,
    clear_user_session,
)
from app.models import User


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token, refresh_token = AuthService.create_tokens(user)
    AuthService.update_last_login(db, user.id)
    touch_user_session(str(user.id))

    # Set HttpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=bool(user.must_change_password),
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
    touch_user_session(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: RefreshRequest,
    response: Response,
    current_user: User = Depends(
        require_role("admin", "teacher", "student", "translator")
    ),
    db: Session = Depends(get_db),
):
    AuthService.blacklist_token(request.refresh_token)
    clear_user_session(str(current_user.id))
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
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
            request.full_name,
        )
    else:
        user = AuthService.register(
            db,
            request.email,
            request.password,
            request.role,
            institution_uuid,
            request.full_name,
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
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
        full_name=current_user.full_name,
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


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = AuthService.get_user_by_email(db, request.email)
    if user and user.is_active:
        reset_token = AuthService.generate_password_reset_token()
        AuthService.store_password_reset_token(reset_token, user.id)
        sent = EmailService.send_password_reset_email(user.email, reset_token)
        logger.info(
            "Forgot-password email attempt for %s: sent=%s",
            user.email,
            sent,
        )
    else:
        logger.info(
            "Forgot-password requested for non-existent or inactive email: %s",
            request.email,
        )

    return MessageResponse(
        message="If an account with that email exists, a password reset email has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
):
    try:
        user_id = AuthService.consume_password_reset_token(request.token)
    except ValueError:
        user_id = None

    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    user.must_change_password = False
    db.commit()

    return MessageResponse(message="Password reset successfully")
