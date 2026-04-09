from datetime import datetime
import uuid
import redis

from sqlalchemy.orm import Session

from app.models import User
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL)


class AuthService:
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_tokens(user: User) -> tuple[str, str]:
        access_token = create_access_token({"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return access_token, refresh_token

    @staticmethod
    def update_last_login(db: Session, user_id: uuid.UUID):
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def blacklist_token(token: str):
        try:
            redis_client.setex(f"blacklist:{token}", 86400 * 7, "1")
        except Exception:
            pass

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        try:
            return redis_client.exists(f"blacklist:{token}") > 0
        except Exception:
            return False

    @staticmethod
    def register(
        db: Session,
        email: str,
        password: str,
        role: str,
        institution_id: uuid.UUID | None = None,
    ) -> User:
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            role=role,
            institution_id=institution_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()
