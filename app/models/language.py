from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    native_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    libretranslate_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    translations: Mapped[list["Translation"]] = relationship(
        "Translation", back_populates="language"
    )
