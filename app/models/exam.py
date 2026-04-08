import uuid
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Exam(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "exams"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    institution: Mapped["Institution | None"] = relationship(
        "Institution", back_populates="exams"
    )
    book: Mapped["Book | None"] = relationship("Book", back_populates="exams")
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_exams")
    answer_keys: Mapped[list["AnswerKey"]] = relationship(
        "AnswerKey", back_populates="exam"
    )


class AnswerKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "answer_keys"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=True,
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        nullable=True,
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    institution: Mapped["Institution | None"] = relationship("Institution")
    book: Mapped["Book | None"] = relationship("Book")
    exam: Mapped["Exam | None"] = relationship("Exam", back_populates="answer_keys")
    uploader: Mapped["User"] = relationship("User")
