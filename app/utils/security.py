from datetime import datetime, timedelta
from typing import Optional
import uuid

import bcrypt
import redis
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ALGORITHM = "HS256"
redis_client = redis.from_url(settings.REDIS_URL)


def _session_activity_key(user_id: str) -> str:
    return f"session:last_activity:{user_id}"


def _session_ttl_seconds() -> int:
    return max(settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, 60)


def touch_user_session(user_id: str) -> None:
    try:
        redis_client.setex(
            _session_activity_key(user_id),
            _session_ttl_seconds(),
            datetime.utcnow().isoformat(),
        )
    except Exception:
        pass


def clear_user_session(user_id: str) -> None:
    try:
        redis_client.delete(_session_activity_key(user_id))
    except Exception:
        pass


def is_user_session_idle_expired(user_id: str) -> bool:
    try:
        value = redis_client.get(_session_activity_key(user_id))
        if not value:
            return False
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        last_activity = datetime.fromisoformat(value)
        idle_timeout = timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)
        return datetime.utcnow() - last_activity > idle_timeout
    except Exception:
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return hash_password(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    default_expiry = timedelta(
        minutes=max(
            settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60,
        )
    )
    expire = datetime.utcnow() + (
        expires_delta or default_expiry
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    if is_user_session_idle_expired(user_id):
        clear_user_session(user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity",
        )

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    touch_user_session(user_id)
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user


def require_role(*roles: str):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {roles}",
            )
        return current_user

    return role_checker
