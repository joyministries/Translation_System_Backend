from sqlalchemy.orm import Session

from app.models import Language


class LanguageService:
    @staticmethod
    def list_languages(db: Session, skip: int = 0, limit: int = 100) -> list[Language]:
        return db.query(Language).offset(skip).limit(limit).all()

    @staticmethod
    def get_language(db: Session, language_id: int) -> Language | None:
        return db.query(Language).filter(Language.id == language_id).first()

    @staticmethod
    def get_language_by_code(db: Session, code: str) -> Language | None:
        return db.query(Language).filter(Language.code == code).first()

    @staticmethod
    def create_language(db: Session, data: dict) -> Language:
        language = Language(**data)
        db.add(language)
        db.commit()
        db.refresh(language)
        return language

    @staticmethod
    def update_language(db: Session, language_id: int, data: dict) -> Language | None:
        language = LanguageService.get_language(db, language_id)
        if not language:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(language, key, value)
        db.commit()
        db.refresh(language)
        return language

    @staticmethod
    def deactivate_language(db: Session, language_id: int) -> Language | None:
        return LanguageService.update_language(db, language_id, {"is_active": False})

    @staticmethod
    def activate_language(db: Session, language_id: int) -> Language | None:
        return LanguageService.update_language(db, language_id, {"is_active": True})
