import logging

from app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def translate_content(
    self, translation_id: str, original_text: str, language_code: str
):
    logger.info(f"Translation task started: {translation_id}")
    logger.info(f"Language: {language_code}, Text length: {len(original_text)}")

    logger.info(f"Translation task completed: {translation_id}")
    return {"status": "success", "translation_id": translation_id}
