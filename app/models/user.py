import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
    )

    institution: Mapped["Institution | None"] = relationship(
        "Institution", back_populates="users"
    )
    uploaded_books: Mapped[list["Book"]] = relationship(
        "Book", back_populates="uploader"
    )
    translation_jobs: Mapped[list["TranslationJob"]] = relationship(
        "TranslationJob", back_populates="requester"
    )
    uploaded_exams: Mapped[list["Exam"]] = relationship(
        "Exam", back_populates="uploader"
    )
