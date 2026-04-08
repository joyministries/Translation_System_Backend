import uuid

from sqlalchemy import String, Integer, BigInteger, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class ExtractionStatus(str):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class Book(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(20),
        default=ExtractionStatus.PENDING,
        nullable=False,
    )

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    institution: Mapped["Institution | None"] = relationship(
        "Institution", back_populates="books"
    )
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_books")
    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="book")
