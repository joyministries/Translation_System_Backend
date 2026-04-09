import logging
import uuid
from datetime import datetime

import requests
from celery import Task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Language
from app.utils.text_chunker import chunk_text, merge_chunks


logger = logging.getLogger(__name__)


def translate_chunk(text: str, source_lang: str, target_lang: str) -> str:
    from app.config import settings

    try:
        response = requests.post(
            f"{settings.LIBRETRANSLATE_URL}/translate",
            json={
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("translatedText", text)
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise


class TranslationTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = 5
    retry_backoff_max = 60
    max_retries = 3


@celery_app.task(bind=True, base=TranslationTask)
def translate_content(self, translation_id: str, original_text: str, language_id: int):
    logger.info(f"Translation task started: {translation_id}")
    logger.info(f"Language ID: {language_id}, Text length: {len(original_text)}")

    db = SessionLocal()
    try:
        from app.models import Translation, TranslationJob

        language = db.query(Language).filter(Language.id == language_id).first()
        if not language or not language.libretranslate_code:
            raise ValueError(
                f"Invalid language or missing libretranslate_code for language_id: {language_id}"
            )

        chunks = chunk_text(original_text)
        logger.info(f"Split into {len(chunks)} chunks")

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i + 1}/{len(chunks)}")
            translated = translate_chunk(chunk, "en", language.libretranslate_code)
            translated_chunks.append(translated)

        translated_text = merge_chunks(translated_chunks)

        translation = (
            db.query(Translation)
            .filter(Translation.id == uuid.UUID(translation_id))
            .first()
        )
        if translation:
            translation.translated_text = translated_text
            translation.status = "done"
            translation.translation_engine = "libretranslate"
            translation.chunk_count = len(chunks)
            db.commit()

        job = (
            db.query(TranslationJob)
            .filter(TranslationJob.celery_task_id == self.request.id)
            .first()
        )
        if job:
            job.completed_at = datetime.utcnow()
            db.commit()

        logger.info(f"Translation task completed: {translation_id}")
        return {"status": "success", "translation_id": translation_id}

    except Exception as e:
        logger.error(f"Translation task failed: {e}")

        try:
            translation = (
                db.query(Translation)
                .filter(Translation.id == uuid.UUID(translation_id))
                .first()
            )
            if translation:
                translation.status = "failed"
                db.commit()

            job = (
                db.query(TranslationJob)
                .filter(TranslationJob.celery_task_id == self.request.id)
                .first()
            )
            if job:
                job.error_message = str(e)
                db.commit()
        except Exception:
            pass

        raise
    finally:
        db.close()
