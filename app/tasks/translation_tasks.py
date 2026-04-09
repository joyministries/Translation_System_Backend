import logging
import uuid
from datetime import datetime

import requests
from celery import Task
from deep_translator import GoogleTranslator

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Language
from app.utils.text_chunker import chunk_text, merge_chunks


logger = logging.getLogger(__name__)

TRANSLATION_ENGINE = "libretranslate"


def translate_chunk(text: str, source_lang: str, target_lang: str) -> str:
    global TRANSLATION_ENGINE
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
        if response.status_code == 200:
            data = response.json()
            TRANSLATION_ENGINE = "libretranslate"
            return data.get("translatedText", text)
    except Exception as e:
        logger.warning(f"LibreTranslate failed: {e}")

    logger.info("Falling back to Google Cloud Translation API")
    try:
        if settings.GOOGLE_CLOUD_API_KEY:
            cloud_response = requests.get(
                f"https://translation.googleapis.com/language/translate/v2",
                params={
                    "key": settings.GOOGLE_CLOUD_API_KEY,
                    "q": text[:5000],
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text",
                },
                timeout=30,
            )
            if cloud_response.status_code == 200:
                data = cloud_response.json()
                if data.get("data", {}).get("translations"):
                    TRANSLATION_ENGINE = "google_cloud"
                    return data["data"]["translations"][0]["translatedText"]
    except Exception as gce:
        logger.warning(f"Google Cloud API failed: {gce}")

    logger.info("Falling back to Google Translate (free)")
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        TRANSLATION_ENGINE = "google_free"
        return result
    except Exception as ge:
        logger.error(f"Google Translate also failed: {ge}")
        raise


class TranslationTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = 5
    retry_backoff_max = 60
    max_retries = 3


@celery_app.task(bind=True, base=TranslationTask)
def translate_content(
    self,
    translation_id: str,
    original_text: str,
    language_id: int,
    source_language_id: int | None = None,
):
    logger.info(f"Translation task started: {translation_id}")
    logger.info(
        f"Language ID: {language_id}, Source Language ID: {source_language_id}, Text length: {len(original_text)}"
    )

    db = SessionLocal()
    try:
        from app.models import Translation, TranslationJob, Language

        target_language = db.query(Language).filter(Language.id == language_id).first()
        if not target_language or not target_language.libretranslate_code:
            raise ValueError(
                f"Invalid language or missing libretranslate_code for language_id: {language_id}"
            )

        source_language = None
        if source_language_id:
            source_language = (
                db.query(Language).filter(Language.id == source_language_id).first()
            )

        source_lang_code = (
            source_language.libretranslate_code if source_language else "en"
        )
        target_lang_code = target_language.libretranslate_code or target_language.code

        logger.info(f"Translating from {source_lang_code} to {target_lang_code}")

        chunks = chunk_text(original_text)
        logger.info(f"Split into {len(chunks)} chunks")

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i + 1}/{len(chunks)}")
            translated = translate_chunk(chunk, source_lang_code, target_lang_code)
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
            translation.translation_engine = TRANSLATION_ENGINE
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
