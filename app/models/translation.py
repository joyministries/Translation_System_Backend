import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Translation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "translations"

    content_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    language_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("languages.id"),
        nullable=False,
    )

    language: Mapped["Language"] = relationship(
        "Language", back_populates="translations"
    )
    translation_jobs: Mapped[list["TranslationJob"]] = relationship(
        "TranslationJob", back_populates="translation"
    )


class TranslationJob(Base, UUIDMixin):
    __tablename__ = "translation_jobs"

    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    translation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("translations.id"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    translation: Mapped["Translation"] = relationship(
        "Translation", back_populates="translation_jobs"
    )
    requester: Mapped["User"] = relationship("User", back_populates="translation_jobs")
