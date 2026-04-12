import json
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

TRANSLATION_ENGINE = "google_translate"


def translate_chunk(text: str, source_lang: str, target_lang: str) -> str:
    from app.config import settings

    try:
        if settings.GOOGLE_CLOUD_API_KEY:
            cloud_response = requests.get(
                "https://translation.googleapis.com/language/translate/v2",
                params={
                    "key": settings.GOOGLE_CLOUD_API_KEY,
                    "q": text[:5000],
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text",
                },
                timeout=60,
            )
            if cloud_response.status_code == 200:
                data = cloud_response.json()
                if data.get("data", {}).get("translations"):
                    logger.info(
                        f"Translated using Google Translate {source_lang} -> {target_lang}"
                    )
                    return data["data"]["translations"][0]["translatedText"]
    except Exception as e:
        logger.warning(f"Google Translate failed: {e}")

    logger.error("Translation failed - no API available")
    return text


def _batch_translate(texts: list[str], source_lang: str, target_lang: str) -> list[str]:
    """Translate a list of texts in one API call using concurrent requests."""
    from app.config import settings
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not texts:
        return texts

    # Try Google Translate batch (up to 128 strings per request)
    try:
        if settings.GOOGLE_CLOUD_API_KEY:
            import urllib.parse
            # Build POST body with repeated q= params
            body = "&".join(
                f"q={urllib.parse.quote(str(t)[:5000])}" for t in texts
            ) + f"&source={source_lang}&target={target_lang}&format=text"

            response = requests.post(
                f"https://translation.googleapis.com/language/translate/v2?key={settings.GOOGLE_CLOUD_API_KEY}",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60,
            )
            if response.status_code == 200:
                translations = response.json().get("data", {}).get("translations", [])
                if len(translations) == len(texts):
                    logger.info(f"Batch translated {len(texts)} texts {source_lang}->{target_lang}")
                    return [t["translatedText"] for t in translations]
    except Exception as e:
        logger.warning(f"Batch translate failed: {e}")

    # Fallback: concurrent individual requests
    results = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(translate_chunk, t, source_lang, target_lang): i for i, t in enumerate(texts)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def _translate_excel_json(original_text: str, source_lang: str, target_lang: str) -> str:
    """Translate cell values and sheet names in batches."""
    try:
        data = json.loads(original_text)
    except Exception:
        return original_text

    sheets = data.get("sheets") or {}
    sheet_names = data.get("sheet_names") or list(sheets.keys())

    # Collect all unique non-empty strings across all sheets + sheet names
    all_texts = list(sheet_names)
    for sheet_name in sheet_names:
        for row in sheets.get(sheet_name, []):
            for cell in row:
                if cell and str(cell).strip():
                    all_texts.append(str(cell))

    # Batch translate in chunks of 100
    BATCH = 100
    translated_map = {}
    for i in range(0, len(all_texts), BATCH):
        batch = all_texts[i:i + BATCH]
        results = _batch_translate(batch, source_lang, target_lang)
        for orig, trans in zip(batch, results):
            translated_map[orig] = trans

    translated_sheet_names = [translated_map.get(n, n) for n in sheet_names]

    translated_sheets = {}
    for sheet_name, trans_name in zip(sheet_names, translated_sheet_names):
        rows = sheets.get(sheet_name, [])
        translated_rows = [
            [translated_map.get(str(cell), cell) if cell and str(cell).strip() else cell for cell in row]
            for row in rows
        ]
        translated_sheets[trans_name] = translated_rows

    return json.dumps({
        "sheet_names": sheet_names,
        "translated_sheet_names": translated_sheet_names,
        "sheets": translated_sheets,
    })


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

        # Check if this is an exam (JSON with sheets structure) — translate cells, not raw JSON
        is_excel = False
        try:
            parsed = json.loads(original_text)
            if isinstance(parsed, dict) and ("sheets" in parsed or "makaratasi" in parsed):
                is_excel = True
        except Exception:
            pass

        if is_excel:
            translated_text = _translate_excel_json(original_text, source_lang_code, target_lang_code)
            chunks = [original_text]  # for chunk_count
        else:
            chunks = chunk_text(original_text)
            logger.info(f"Split into {len(chunks)} chunks")
            results = _batch_translate(chunks, source_lang_code, target_lang_code)
            translated_text = merge_chunks(results)

        translation = (
            db.query(Translation)
            .filter(Translation.id == uuid.UUID(translation_id))
            .first()
        )
        if translation:
            translation.translated_text = translated_text
            translation.status = "done"
            translation.translation_engine = "google_translate"
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
