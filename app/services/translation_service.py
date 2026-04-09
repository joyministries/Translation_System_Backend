import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Translation, TranslationJob
from app.models.language import Language
from app.utils.text_chunker import chunk_text, merge_chunks
from app.tasks.translation_tasks import translate_content


class TranslationService:
    @staticmethod
    def get_or_create_translation(
        db: Session,
        content_type: str,
        content_id: uuid.UUID,
        language_id: int,
        original_text: str | None = None,
    ) -> tuple[Translation, str | None]:
        existing = (
            db.query(Translation)
            .filter(
                Translation.content_type == content_type,
                Translation.content_id == content_id,
                Translation.language_id == language_id,
                Translation.status == "done",
            )
            .first()
        )

        if existing:
            return existing, None

        translation = (
            db.query(Translation)
            .filter(
                Translation.content_type == content_type,
                Translation.content_id == content_id,
                Translation.language_id == language_id,
            )
            .first()
        )

        if translation:
            return translation, None

        translation = Translation(
            content_type=content_type,
            content_id=content_id,
            language_id=language_id,
            status="pending",
        )
        db.add(translation)
        db.commit()
        db.refresh(translation)

        if original_text:
            chunks = chunk_text(original_text)
            translation.chunk_count = len(chunks)
            db.commit()

            task = translate_content.delay(
                str(translation.id), original_text, str(language_id)
            )

            job = TranslationJob(
                celery_task_id=task.id,
                translation_id=translation.id,
                requested_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                started_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()

            return translation, task.id

        return translation, None

    @staticmethod
    def get_translation(db: Session, translation_id: uuid.UUID) -> Translation | None:
        return db.query(Translation).filter(Translation.id == translation_id).first()

    @staticmethod
    def get_translation_by_content(
        db: Session,
        content_type: str,
        content_id: uuid.UUID,
        language_id: int,
    ) -> Translation | None:
        return (
            db.query(Translation)
            .filter(
                Translation.content_type == content_type,
                Translation.content_id == content_id,
                Translation.language_id == language_id,
            )
            .first()
        )

    @staticmethod
    def update_translation(
        db: Session,
        translation_id: uuid.UUID,
        translated_text: str,
        status: str = "done",
    ) -> Translation | None:
        translation = TranslationService.get_translation(db, translation_id)
        if not translation:
            return None
        translation.translated_text = translated_text
        translation.status = status
        translation.translation_engine = "libretranslate"
        db.commit()
        db.refresh(translation)
        return translation

    @staticmethod
    def get_job(db: Session, job_id: uuid.UUID) -> TranslationJob | None:
        return db.query(TranslationJob).filter(TranslationJob.id == job_id).first()

    @staticmethod
    def get_job_by_task_id(db: Session, task_id: str) -> TranslationJob | None:
        return (
            db.query(TranslationJob)
            .filter(TranslationJob.celery_task_id == task_id)
            .first()
        )
