import secrets
import string

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
from app.services.email_service import EmailService

redis_client = redis.from_url(settings.REDIS_URL)


class AuthService:
    PASSWORD_RESET_TOKEN_TTL_SECONDS = 3600

    @staticmethod
    def _password_reset_key(token: str) -> str:
        return f"password_reset:{token}"

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
            redis_client.setex(
                f"blacklist:{token}",
                86400 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
                "1",
            )
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
        full_name: str | None = None,
    ) -> User:
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            full_name=full_name,
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

    @staticmethod
    def generate_temp_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_password_reset_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def store_password_reset_token(token: str, user_id: uuid.UUID) -> None:
        redis_client.setex(
            AuthService._password_reset_key(token),
            AuthService.PASSWORD_RESET_TOKEN_TTL_SECONDS,
            str(user_id),
        )

    @staticmethod
    def consume_password_reset_token(token: str) -> uuid.UUID | None:
        key = AuthService._password_reset_key(token)
        user_id = redis_client.get(key)
        if not user_id:
            return None
        redis_client.delete(key)
        if isinstance(user_id, bytes):
            user_id = user_id.decode("utf-8")
        return uuid.UUID(str(user_id))

    @staticmethod
    def register_with_temp_password(
        db: Session,
        email: str,
        role: str,
        institution_id: uuid.UUID | None = None,
        full_name: str | None = None,
    ) -> tuple[User, str]:
        temp_password = AuthService.generate_temp_password()
        hashed_password = get_password_hash(temp_password)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            institution_id=institution_id,
            is_active=True,
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        EmailService.send_welcome_email(email, temp_password)

        return user, temp_password
