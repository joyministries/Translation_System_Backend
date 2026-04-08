import uuid

from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Institution(Base, UUIDMixin):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="institution")
    books: Mapped[list["Book"]] = relationship("Book", back_populates="institution")
    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="institution")
