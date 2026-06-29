from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Language, User
from app.models.exam import Exam
from app.models.translation import Translation
from app.services.translation_service import TranslationService
from app.services.document_conversion_service import CONVERTIBLE_TO_DOCX_MIME_TYPES, DOCX_MIME
from app.utils.file_utils import save_upload_stream_securely
from app.utils.security import require_role


router = APIRouter(prefix="/integration", tags=["Integration"])


def _callback_translation(callback_url: str, filename: str, content: bytes, title: str, language_code: str):
    import requests

    resp = requests.post(
        callback_url,
        data={
            "title": title,
            "language_code": language_code,
        },
        files={
            "file": (filename, content, "application/pdf"),
        },
        timeout=60,
    )
    resp.raise_for_status()


@router.get("/catalog")
def integration_catalog(
    title: str | None = None,
    content_type: str | None = None,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    payload = {"books": [], "exams": []}

    # Books
    if content_type in (None, "book"):
        query = db.query(Book)
        if title:
            query = query.filter(Book.title == title)
        for book in query.order_by(Book.created_at.desc()).all():
            translations = (
                db.query(Translation, Language)
                .join(Language, Language.id == Translation.language_id)
                .filter(
                    Translation.content_type == "book",
                    Translation.content_id == book.id,
                    Translation.status == "done",
                )
                .all()
            )
            payload["books"].append(
                {
                    "book_id": str(book.id),
                    "title": book.title,
                    "extraction_status": book.extraction_status,
                    "languages": [
                        {
                            "language_id": lang.id,
                            "language_code": lang.code,
                            "language_name": lang.name,
                            "translation_id": str(tr.id),
                        }
                        for tr, lang in translations
                    ],
                }
            )

    # Exams
    if content_type in (None, "exam"):
        query = db.query(Exam)
        if title:
            query = query.filter(Exam.title == title)
        for exam in query.order_by(Exam.created_at.desc()).all():
            translations = (
                db.query(Translation, Language)
                .join(Language, Language.id == Translation.language_id)
                .filter(
                    Translation.content_type == "exam",
                    Translation.content_id == exam.id,
                    Translation.status == "done",
                )
                .all()
            )
            payload["exams"].append(
                {
                    "exam_id": str(exam.id),
                    "title": exam.title,
                    "languages": [
                        {
                            "language_id": lang.id,
                            "language_code": lang.code,
                            "language_name": lang.name,
                            "translation_id": str(tr.id),
                        }
                        for tr, lang in translations
                    ],
                }
            )

    return payload


@router.post("/exchange")
async def integration_exchange(
    title: str = Form(...),
    language_code: str = Form(...),
    source_language_code: str = Form("en"),
    content_type: str = Form("book"),
    first_content_page: int = Form(5),
    callback_url: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    target_lang = db.query(Language).filter(Language.code == language_code).first()
    if not target_lang:
        raise HTTPException(status_code=404, detail="Target language not found")

    source_lang = db.query(Language).filter(Language.code == source_language_code).first()

    # --- EXAM HANDLING ---
    if content_type == "exam":
        exam = db.query(Exam).filter(Exam.title == title).order_by(Exam.created_at.desc()).first()
        if exam:
            translation = (
                db.query(Translation)
                .filter(
                    Translation.content_type == "exam",
                    Translation.content_id == exam.id,
                    Translation.language_id == target_lang.id,
                    Translation.status == "done",
                )
                .first()
            )
            if translation:
                from app.routers.student.translate import download_translation
                response = download_translation(
                    translation_id=str(translation.id),
                    format="xlsx",
                    cache_variant=None,
                    refresh_cache=False,
                    current_user=current_user,
                    db=db,
                )
                if callback_url:
                    _callback_translation(
                        callback_url,
                        f"{exam.title}-{language_code}.xlsx",
                        response.body,
                        exam.title,
                        language_code,
                    )
                    return {
                        "status": "sent",
                        "exam_id": str(exam.id),
                        "translation_id": str(translation.id),
                        "language_code": language_code,
                    }
                return response

            if not exam.original_text:
                return Response(
                    content=f'{{"status":"pending","detail":"Exam exists but has no extracted text","exam_id":"{exam.id}"}}',
                    media_type="application/json",
                    status_code=status.HTTP_202_ACCEPTED,
                )

            translation, task_id = TranslationService.get_or_create_translation(
                db,
                content_type="exam",
                content_id=exam.id,
                language_id=target_lang.id,
                source_language_id=source_lang.id if source_lang else None,
                original_text=exam.original_text,
                output_format="xlsx",
            )
            return Response(
                content=f'{{"status":"pending","detail":"Translation queued","exam_id":"{exam.id}","translation_id":"{translation.id}","language_code":"{language_code}"}}',
                media_type="application/json",
                status_code=status.HTTP_202_ACCEPTED,
            )

        raise HTTPException(status_code=404, detail="Exam not found")

    # --- BOOK HANDLING ---
    book = db.query(Book).filter(Book.title == title).order_by(Book.created_at.desc()).first()

    if book:
        translation = (
            db.query(Translation)
            .filter(
                Translation.content_type == "book",
                Translation.content_id == book.id,
                Translation.language_id == target_lang.id,
                Translation.status == "done",
            )
            .first()
        )
        if translation:
            from app.routers.student.translate import download_translation

            response = download_translation(
                translation_id=str(translation.id),
                format="pdf",
                cache_variant=None,
                refresh_cache=False,
                current_user=current_user,
                db=db,
            )
            if callback_url:
                _callback_translation(
                    callback_url,
                    f"{book.title}-{language_code}.pdf",
                    response.body,
                    book.title,
                    language_code,
                )
                return {
                    "status": "sent",
                    "book_id": str(book.id),
                    "translation_id": str(translation.id),
                    "language_code": language_code,
                    "callback_url": callback_url,
                }
            return response

        if book.extraction_status != "done" or not book.extracted_text:
            return Response(
                content=(
                    '{"status":"pending","detail":"Book exists but extraction is not complete yet",'
                    f'"book_id":"{book.id}","extraction_status":"{book.extraction_status}"'
                    "}"
                ),
                media_type="application/json",
                status_code=status.HTTP_202_ACCEPTED,
            )

        translation, task_id = TranslationService.get_or_create_translation(
            db,
            content_type="book",
            content_id=book.id,
            language_id=target_lang.id,
            source_language_id=source_lang.id if source_lang else None,
            original_text=book.extracted_text,
            output_format="pdf",
        )
        return Response(
            content=(
                '{"status":"pending","detail":"Translation queued",'
                f'"book_id":"{book.id}","translation_id":"{translation.id}","task_id":"{task_id}","language_code":"{language_code}"'
                "}"
            ),
            media_type="application/json",
            status_code=status.HTTP_202_ACCEPTED,
        )

    if not file:
        raise HTTPException(status_code=404, detail="Content not found locally and no file was provided")

    try:
        filename, mime_type, file_size_bytes = await save_upload_stream_securely(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    book = Book(
        title=title or file.filename or "uploaded-book",
        file_path=filename,
        normalized_docx_path=filename if mime_type == DOCX_MIME else None,
        normalized_source_type=mime_type,
        normalization_status="done" if mime_type == DOCX_MIME else ("pending" if mime_type in CONVERTIBLE_TO_DOCX_MIME_TYPES else None),
        file_size_bytes=file_size_bytes,
        uploaded_by=None,
        extraction_status="pending",
        first_content_page=first_content_page,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    if mime_type == "application/pdf":
        from app.tasks.ingestion_tasks import extract_pdf_text

        extract_pdf_text.delay(str(book.id), filename)
    elif mime_type in CONVERTIBLE_TO_DOCX_MIME_TYPES:
        from app.tasks.ingestion_tasks import extract_doc_text

        extract_doc_text.delay(str(book.id), filename)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return Response(
        content=(
            '{"status":"pending","detail":"Book uploaded and extraction queued",'
            f'"book_id":"{book.id}","title":"{book.title}","language_code":"{language_code}"'
            "}"
        ),
        media_type="application/json",
        status_code=status.HTTP_202_ACCEPTED,
    )
