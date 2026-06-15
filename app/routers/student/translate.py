import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Exam, User
from app.utils.security import require_role
from app.services.translation_service import TranslationService


router = APIRouter(prefix="/translate", tags=["Translations"])


DEFAULT_FONT_SET = {
    "reportlab_regular_file": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "reportlab_bold_file": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "overlay_regular_file": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "overlay_bold_file": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

SPECIAL_SCRIPT_FONT_MAP = {
    "hi": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSerifDevanagari-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSerifDevanagari-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansDevanagari-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansDevanagari-Bold.ttf",
    },
    "mr": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSerifDevanagari-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSerifDevanagari-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansDevanagari-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansDevanagari-Bold.ttf",
    },
    "ne": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSerifDevanagari-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSerifDevanagari-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansDevanagari-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansDevanagari-Bold.ttf",
    },
    "sa": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSerifDevanagari-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSerifDevanagari-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansDevanagari-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansDevanagari-Bold.ttf",
    },
    "bn": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansBengali-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansBengali-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansBengali-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansBengali-Bold.ttf",
    },
    "pa": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansGurmukhi-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansGurmukhi-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansGurmukhi-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansGurmukhi-Bold.ttf",
    },
    "gu": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansGujarati-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansGujarati-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansGujarati-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansGujarati-Bold.ttf",
    },
    "ta": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansTamil-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansTamil-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansTamil-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansTamil-Bold.ttf",
    },
    "te": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansTelugu-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansTelugu-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansTelugu-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansTelugu-Bold.ttf",
    },
    "kn": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansKannada-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansKannada-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansKannada-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansKannada-Bold.ttf",
    },
    "ml": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansMalayalam-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansMalayalam-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansMalayalam-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansMalayalam-Bold.ttf",
    },
    "si": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansSinhala-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansSinhala-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansSinhala-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansSinhala-Bold.ttf",
    },
    "th": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansThai-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansThai-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansThai-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansThai-Bold.ttf",
    },
    "km": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansKhmer-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansKhmer-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansKhmer-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansKhmer-Bold.ttf",
    },
    "my": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansMyanmar-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansMyanmar-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansMyanmar-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansMyanmar-Bold.ttf",
    },
    "lo": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansLao-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansLao-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansLao-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansLao-Bold.ttf",
    },
    "zh": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansCJKsc-Regular.otf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansCJKsc-Bold.otf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansCJKsc-Regular.otf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansCJKsc-Bold.otf",
    },
    "zh-cn": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansCJKsc-Regular.otf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansCJKsc-Bold.otf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansCJKsc-Regular.otf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansCJKsc-Bold.otf",
    },
    "zh-tw": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansCJKtc-Regular.otf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansCJKtc-Bold.otf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansCJKtc-Regular.otf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansCJKtc-Bold.otf",
    },
    "ja": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansJP-Regular.otf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansJP-Bold.otf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansJP-Regular.otf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansJP-Bold.otf",
    },
    "ko": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansKR-Regular.otf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansKR-Bold.otf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansKR-Regular.otf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansKR-Bold.otf",
    },
    "ar": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
    },
    "ur": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoNastaliqUrdu-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoNastaliqUrdu-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoNastaliqUrdu-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoNastaliqUrdu-Bold.ttf",
    },
    "fa": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
    },
    "ps": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
    },
    "ku": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoNaskhArabic-Bold.ttf",
    },
    "he": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansHebrew-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansHebrew-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansHebrew-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansHebrew-Bold.ttf",
    },
    "am": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansEthiopic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansEthiopic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansEthiopic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansEthiopic-Bold.ttf",
    },
    "ti": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansEthiopic-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansEthiopic-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansEthiopic-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansEthiopic-Bold.ttf",
    },
    "hy": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansArmenian-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansArmenian-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansArmenian-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansArmenian-Bold.ttf",
    },
    "ka": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansGeorgian-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansGeorgian-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansGeorgian-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansGeorgian-Bold.ttf",
    },
    "bo": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansTibetan-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansTibetan-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansTibetan-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansTibetan-Bold.ttf",
    },
    "mn": {
        "reportlab_regular_file": "/app/app/assets/fonts/NotoSansMongolian-Regular.ttf",
        "reportlab_bold_file": "/app/app/assets/fonts/NotoSansMongolian-Bold.ttf",
        "overlay_regular_file": "/app/app/assets/fonts/NotoSansMongolian-Regular.ttf",
        "overlay_bold_file": "/app/app/assets/fonts/NotoSansMongolian-Bold.ttf",
    },
}


def _resolve_font_set(language_code: str | None) -> dict[str, str]:
    code = (language_code or "").lower()
    font_set = SPECIAL_SCRIPT_FONT_MAP.get(code)
    if not font_set:
        return DEFAULT_FONT_SET.copy()

    resolved = DEFAULT_FONT_SET.copy()
    for key, path in font_set.items():
        if os.path.exists(path):
            resolved[key] = path
    return resolved


@router.get("/book/{book_id}")
def list_book_translations(
    book_id: str,
    current_user: User = Depends(require_role("admin", "student", "teacher", "translator")),
    db: Session = Depends(get_db),
):
    """List all existing translations for a book. Includes download URL for each."""
    from app.models import Translation, Language
    translations = (
        db.query(Translation, Language)
        .join(Language, Language.id == Translation.language_id)
        .filter(Translation.content_id == book_id, Translation.content_type == "book", Translation.status == "done")
        .all()
    )
    return {
        "book_id": book_id,
        "translations": [
            {
                "translation_id": str(t.id),
                "language_id": t.language_id,
                "language_name": l.name,
                "language_code": l.code,
                "status": t.status,
                "download_url": f"/translations/{t.id}/download",
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t, l in translations
        ]
    }


@router.get("/exam/{exam_id}")
def list_exam_translations(
    exam_id: str,
    current_user: User = Depends(require_role("admin", "student", "teacher", "translator")),
    db: Session = Depends(get_db),
):
    """List all existing translations for an exam. Includes download URL for each."""
    from app.models import Translation, Language
    translations = (
        db.query(Translation, Language)
        .join(Language, Language.id == Translation.language_id)
        .filter(Translation.content_id == exam_id, Translation.content_type == "exam", Translation.status == "done")
        .all()
    )
    return {
        "exam_id": exam_id,
        "translations": [
            {
                "translation_id": str(t.id),
                "language_id": t.language_id,
                "language_name": l.name,
                "language_code": l.code,
                "status": t.status,
                "download_url": f"/translations/{t.id}/download",
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t, l in translations
        ]
    }


@router.post("")
async def trigger_translation(
    content_type: str,
    content_id: str,
    language_id: int,
    source_language_id: int | None = None,
    output_format: str = "pdf",
    current_user: User = Depends(require_role("admin", "student")),
    db: Session = Depends(get_db),
):
    if content_type == "book":
        book = db.query(Book).filter(Book.id == content_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if not book.extracted_text:
            raise HTTPException(status_code=400, detail="Book text not extracted yet")
        if (book.file_path or "").lower().endswith(".pdf"):
            normalized_docx_path = getattr(book, "normalized_docx_path", None)
            if not (normalized_docx_path and normalized_docx_path.lower().endswith(".docx") and getattr(book, "normalization_status", None) == "done"):
                raise HTTPException(status_code=409, detail="PDF book is not ready: DOCX normalization is required before translation")

        translation, task_id = TranslationService.get_or_create_translation(
            db,
            content_type="book",
            content_id=book.id,
            language_id=language_id,
            source_language_id=source_language_id,
            original_text=book.extracted_text,
            output_format=output_format,
        )

        return {
            "translation_id": str(translation.id),
            "status": translation.status,
            "task_id": task_id,
            "output_format": output_format,
        }

    if content_type == "exam":
        from app.models import Exam
        import json

        exam = db.query(Exam).filter(Exam.id == content_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        if not exam.raw_data:
            raise HTTPException(status_code=400, detail="Exam has no data")

        exam_text = json.dumps(exam.raw_data)

        translation, task_id = TranslationService.get_or_create_translation(
            db,
            content_type="exam",
            content_id=exam.id,
            language_id=language_id,
            source_language_id=source_language_id,
            original_text=exam_text,
            output_format="xlsx",
        )

        return {
            "translation_id": str(translation.id),
            "status": translation.status,
            "task_id": task_id,
            "output_format": "xlsx",
        }

    raise HTTPException(status_code=400, detail="Unsupported content_type")


@router.get("/status/{job_id}")
def get_translation_status(
    job_id: str,
    current_user: User = Depends(require_role("admin", "student")),
    db: Session = Depends(get_db),
):
    from app.models import TranslationJob
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(TranslationJob).filter(TranslationJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job.id),
        "status": job.translation.status if job.translation else "unknown",
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


@router.get("/{translation_id}")
def get_translation(
    translation_id: str,
    current_user: User = Depends(require_role("admin", "student")),
    db: Session = Depends(get_db),
):
    import uuid
    import logging as _logging

    try:
        trans_uuid = uuid.UUID(translation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid translation_id format")

    translation = TranslationService.get_translation(db, trans_uuid)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    return {
        "id": str(translation.id),
        "content_type": translation.content_type,
        "content_id": str(translation.content_id),
        "language_id": translation.language_id,
        "source_language_id": translation.source_language_id,
        "translated_text": translation.translated_text,
        "status": translation.status,
        "chunk_count": translation.chunk_count,
        "created_at": translation.created_at.isoformat()
        if translation.created_at
        else None,
    }


@router.get("/{translation_id}/download")
def download_translation(
    translation_id: str,
    format: str = "pdf",
    cache_variant: str | None = None,
    refresh_cache: bool = False,
    current_user: User = Depends(require_role("admin", "student")),
    db: Session = Depends(get_db),
):
    import uuid

    try:
        trans_uuid = uuid.UUID(translation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid translation_id format")
    translation = TranslationService.get_translation(db, trans_uuid)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    import re as _re

    if translation.status != "done":
        raise HTTPException(status_code=400, detail="Translation not complete yet")

    from fastapi.responses import Response

    if not isinstance(cache_variant, str):
        cache_variant = None

    text = translation.translated_text
    if text:
        _clean_lines = []
        _prev_norm = None
        for _line in text.splitlines():
            _stripped = (_line or '').strip()
            if not _stripped:
                _clean_lines.append('')
                _prev_norm = None
                continue
            _norm = _re.sub(r'\s+', ' ', _stripped).upper()
            if _norm and _norm == _prev_norm:
                continue
            _clean_lines.append(_stripped)
            _prev_norm = _norm
        text = '\n'.join(_clean_lines)

    # Get book cover text if exists
    if translation.content_type == "book":
        book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
        if book and book.extracted_cover_text:
            # Prepend original cover text to translated content
            text = book.extracted_cover_text + "\n\n" + translation.translated_text

    content = None
    media_type = "application/pdf"
    filename = f"translation_{translation_id}.pdf"

    # Auto-detect format for exams
    if translation.content_type == "exam":
        format = "xlsx"

    # Layout-preserving PDF for book PDFs / docx with cover
    if translation.content_type == "book" and format == "pdf":
        import logging as _route_log
        _route_log.getLogger(__name__).warning(f"download start content_type={translation.content_type} format={format} book_id={translation.content_id}")

        book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
        source_docx_path = (getattr(book, "normalized_docx_path", None) or book.file_path) if book else None
        has_source_docx = bool(source_docx_path and source_docx_path.endswith(".docx"))
        if book and book.file_path and book.file_path.endswith(".pdf") and not has_source_docx:
            try:
                from app.services.document_conversion_service import normalize_upload_to_docx
                normalized_docx, normalization_error = normalize_upload_to_docx(book.file_path, "application/pdf")
                if normalized_docx:
                    book.normalized_docx_path = normalized_docx
                    book.normalized_source_type = "application/pdf"
                    book.normalization_status = "done"
                    book.normalization_error = normalization_error
                    db.commit()
                    source_docx_path = normalized_docx
                    has_source_docx = True
                else:
                    book.normalization_status = "failed"
                    book.normalization_error = normalization_error
                    db.commit()
            except Exception as _norm_exc:
                import logging as _norm_logging
                _norm_logging.getLogger(__name__).warning(f"On-demand PDF normalization failed: {_norm_exc}")
        if book and (book.file_path or "").lower().endswith(".pdf") and not has_source_docx:
            raise HTTPException(status_code=409, detail="PDF book cannot be rendered until DOCX normalization succeeds")
        _route_log.getLogger(__name__).warning(f"pdf branch entered file_path={book.file_path if book else None} normalized_docx_path={source_docx_path if has_source_docx else None}")
        if False and book and book.file_path and book.file_path.endswith(".pdf") and not has_source_docx:
            try:
                import os as _os, io as _io
                cache_suffix = f"_translated_{translation.language_id}"
                if isinstance(cache_variant, str) and cache_variant:
                    cache_suffix = f"{cache_suffix}_{cache_variant}"
                cached_pdf_path = f"/app/storage/{book.file_path.replace('.pdf', f'{cache_suffix}.pdf')}"

                if _os.path.exists(cached_pdf_path) and not refresh_cache:
                    with open(cached_pdf_path, "rb") as f:
                        content = f.read()
                elif translation.translated_text:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether, CondPageBreak, Image as RLImage
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.units import inch
                    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
                    from reportlab.lib import colors
                    from reportlab.pdfbase import pdfmetrics
                    from reportlab.pdfbase.ttfonts import TTFont
                    import re as _re
                    import fitz as _fitz
                    from app.models import Language
                    from app.tasks.translation_tasks import _batch_translate

                    lang = db.query(Language).filter(Language.id == translation.language_id).first()
                    src_lang = db.query(Language).filter(Language.id == translation.source_language_id).first()
                    target_code = lang.libretranslate_code or lang.code if lang else "sw"
                    source_code = src_lang.libretranslate_code or src_lang.code if src_lang else "en"

                    font_set = _resolve_font_set(target_code)
                    reportlab_regular_file = font_set["reportlab_regular_file"]
                    reportlab_bold_file = font_set["reportlab_bold_file"]
                    reportlab_regular_name = "DocFont"
                    reportlab_bold_name = "DocFont-Bold"
                    overlay_regular_file = font_set["overlay_regular_file"]
                    overlay_bold_file = font_set["overlay_bold_file"]
                    overlay_regular_name = "docfont"
                    overlay_bold_name = "docfontb"

                    try:
                        pdfmetrics.registerFont(TTFont(reportlab_regular_name, reportlab_regular_file))
                        pdfmetrics.registerFont(TTFont(reportlab_bold_name, reportlab_bold_file))
                    except Exception:
                        pass

                    orig_doc = _fitz.open(f"/app/storage/{book.file_path}")
                    last_page = len(orig_doc) - 1

                    chapter_1_pattern = _re.compile(
                        r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*1\b',
                        _re.IGNORECASE,
                    )

                    introduction_pattern = _re.compile(
                        r'^(INTRODUCTION|COURSE\s+INTRODUCTION|KURSUS\s+INLEIDING|NHANGANYAYA|ISINGENISO|ISANDULELO|INTRODUCCI[ÓO]N|UTANGULIZI|INTRODUÇÃO|EINFÜHRUNG)\b',
                        _re.IGNORECASE,
                    )

                    def _page_looks_like_toc(page):
                        page_text = page.get_text("text", sort=True)
                        upper = page_text.upper()
                        if any(
                            marker in upper
                            for marker in (
                                "TABLE OF CONTENTS",
                                "INHOUDSOPGAWE",
                                "INHOUDS",
                                "YALIYOMO",
                                "ZVIRI MUKATI",
                                "TABLE DES",
                                "ÍNDICE",
                                "OKUQUKETHWE",
                                "ATỌKA",
                            )
                        ):
                            return True
                        dotted_lines = 0
                        for raw_line in page_text.splitlines():
                            line = raw_line.strip()
                            if "....." in line or "….." in line or line.count(".") >= 8:
                                dotted_lines += 1
                        return dotted_lines >= 3

                    def _find_body_start_page_index():
                        start_idx = max((book.first_content_page or 5) - 1, 0)
                        for idx in range(start_idx, len(orig_doc)):
                            if _page_looks_like_toc(orig_doc[idx]):
                                continue
                            page_text = orig_doc[idx].get_text("text", sort=True)
                            for raw_line in page_text.splitlines():
                                line = raw_line.strip()
                                if not line:
                                    continue
                                if introduction_pattern.match(line) and "....." not in line:
                                    return idx
                        for idx in range(start_idx, len(orig_doc)):
                            if _page_looks_like_toc(orig_doc[idx]):
                                continue
                            page_text = orig_doc[idx].get_text("text", sort=True)
                            for raw_line in page_text.splitlines():
                                line = raw_line.strip()
                                if not line:
                                    continue
                                if chapter_1_pattern.match(line) and "....." not in line:
                                    return idx
                        return min(6, last_page - 1) + 1

                    def _is_toc_page(page, text_blocks=None):
                        page_text = page.get_text("text", sort=True)
                        upper = page_text.upper()
                        if any(
                            marker in upper
                            for marker in (
                                "TABLE OF CONTENTS",
                                "INHOUDSOPGAWE",
                                "INHOUDS",
                                "YALIYOMO",
                                "ZVIRI MUKATI",
                                "TABLE DES",
                                "ÍNDICE",
                                "JEDWALI",
                                "ATỌKA",
                            )
                        ):
                            return True
                        blocks = text_blocks or _extract_text_blocks(page)
                        dotted_count = sum(1 for _, text, _ in blocks if "....." in text or "….." in text)
                        return dotted_count >= 3

                    def _normalize_render_quotes(text: str) -> str:
                        if not text:
                            return text
                        return (
                            text.replace("<<", '"')
                            .replace(">>", '"')
                            .replace("«", '"')
                            .replace("»", '"')
                        )

                    def _split_inline_url_references(text: str):
                        if not text or not _re.search(r'https?://|www\.', text):
                            return text, []
                        # Pull footnote/reference URLs out of prose so each renders on its own line.
                        pattern = r'(?<!\w)(?:\d{1,3}\s*)?(?:https?://\S+|www\.\S+)'
                        matches = list(_re.finditer(pattern, text))
                        if not matches:
                            return text, []
                        body_text = text[:matches[0].start()].strip()
                        references = []
                        prose_after_refs = []
                        for idx, match in enumerate(matches):
                            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                            segment = text[match.start():end].strip()
                            page_end = _re.search(r'\b(?:ikhasi|page|p\.)\s*\d+\.?', segment, _re.IGNORECASE)
                            if page_end:
                                ref = segment[:page_end.end()].strip()
                                tail = segment[page_end.end():].strip()
                                if tail:
                                    prose_after_refs.append(tail)
                            else:
                                split_tail = _re.search(r'(?<=[\w/)])\.\s+(?=[A-ZÀ-ÖØ-ÞA-Z][a-zÀ-öø-ÿ])', segment)
                                if split_tail:
                                    ref = segment[:split_tail.start()+1].strip()
                                    tail = segment[split_tail.end():].strip()
                                    if tail:
                                        prose_after_refs.append(tail)
                                else:
                                    ref = segment
                            ref = _re.sub(r'^(\d{1,3})\s*(https?://|www\.)', r'\1 \2', ref)
                            references.append(ref)
                        if prose_after_refs:
                            body_text = f"{body_text} {' '.join(prose_after_refs)}".strip()
                        return body_text, references

                    def _append_reference_flowables(references):
                        if not references:
                            return
                        _append_flowable(Spacer(1, 0.04*inch))
                        for ref_text in references:
                            safe_ref = _normalize_render_quotes(ref_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_flowable(Paragraph(safe_ref, reference_style))

                    body_start_page_idx = _find_body_start_page_index()
                    front_matter_end_idx = max(0, min(body_start_page_idx - 1, last_page - 1))

                    def _page_has_marker(page_idx, markers):
                        if page_idx < 0 or page_idx >= len(orig_doc):
                            return False
                        upper = orig_doc[page_idx].get_text("text", sort=True).upper()
                        return any(marker in upper for marker in markers)

                    _page1_lines = [ln for ln in orig_doc[1].get_text("text", sort=True).splitlines() if ln.strip()] if len(orig_doc) > 1 else []
                    has_manual_marker = any(
                        _page_has_marker(i, (
                            "HOW TO USE THIS MANUAL",
                            "COURSE INTRODUCTION",
                            "INDLELA YOKUSEBENZISA LE NCWADI",
                            "ISINGENISO SESIFUNDO",
                            "ISINGENISO",
                            "MASHANDISIRO ENZVIMBO INO",
                            "Nhanganyaya",
                            "Isandulelo",
                        ))
                        for i in range(1, min(6, len(orig_doc)))
                    )
                    has_exam_marker = any(
                        _page_has_marker(i, ("EXAMINATION", "UKUHLOLWA", "EKSAMEN", "KUONGORORA"))
                        for i in range(1, min(8, len(orig_doc)))
                    )
                    has_toc_marker = any(
                        _page_has_marker(i, ("TABLE OF CONTENTS", "OKUQUKETHWE", "ZVIRI MUKATI", "OKUQUKETHWE"))
                        for i in range(1, min(8, len(orig_doc)))
                    )
                    workbook_like = len(orig_doc) >= 5 and has_manual_marker and has_exam_marker and has_toc_marker
                    import logging as _log
                    _log.getLogger(__name__).warning(f'workbook_like={workbook_like} manual={has_manual_marker} exam={has_exam_marker} toc={has_toc_marker} first_content={book.first_content_page if book else None}')

                    def _normalize_split_scripture_text(value):
                        normalized = _re.sub(
                            r"\((?P<book>[A-ZÀ-Þ][\wÀ-ÿ’'-]{2,}(?:\s+[A-ZÀ-Þ]?[\wÀ-ÿ’'-]{1,}){0,3})\s*\n\s*(?P<verse>\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?\))",
                            lambda _m: '(' + _re.sub(r'\s+', '', _m.group('book').strip()) + _m.group('verse'),
                            value or '',
                        )
                        normalized = _re.sub(
                            r"(?P<book>\b(?:[1-3]\s*)?[A-ZÀ-Þ][\wÀ-ÿ’'.-]{1,}(?:\s+[A-ZÀ-Þ]?[\wÀ-ÿ’'.-]+){0,2})\s*\n\s*(?P<verse>\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?)",
                            lambda _m: _re.sub(r'\s+', '', _m.group('book').strip()) + _m.group('verse'),
                            normalized,
                        )
                        # Translation APIs sometimes split quoted ellipsis continuations
                        # with a blank line. Keep those fragments in the same paragraph
                        # before source-record alignment can attach the tail elsewhere.
                        normalized = _re.sub(r'(?:\.\.\.|…)\s*\n\s*\n\s*(?:\.\.\.|…)', '... ...', normalized)
                        return normalized

                    rendered_translated_text = _normalize_split_scripture_text(text or "")
                    _stored_translated_lines = [ln.strip() for ln in rendered_translated_text.split("\n") if ln.strip()]
                    _cover_line_count = len([ln for ln in orig_doc[0].get_text("text", sort=True).splitlines() if ln.strip()]) if len(orig_doc) else 0
                    _title_page_line_count = len([ln for ln in orig_doc[1].get_text("text", sort=True).splitlines() if ln.strip()]) if len(orig_doc) > 1 else 0
                    _front_translation_cursor = 0
                    _cached_front_matter_available = bool(_stored_translated_lines)

                    def _next_front_translated_line(fallback=""):
                        nonlocal _front_translation_cursor
                        if _front_translation_cursor >= len(_stored_translated_lines):
                            return fallback
                        value = _stored_translated_lines[_front_translation_cursor]
                        _front_translation_cursor += 1
                        return value or fallback

                    def _translate_front_texts(texts):
                        clean_texts = [t for t in texts if (t or "").strip()]
                        if not clean_texts:
                            return []
                        # Download must render only. It must not depend on a live translation API.
                        return [_normalize_render_quotes(_next_front_translated_line(t)) for t in clean_texts]

                    def _extract_text_blocks(page, split_paragraphs: bool = False, aggressive_merge: bool = True):
                        extracted_blocks = []
                        for b in page.get_text("dict")["blocks"]:
                            if b.get("type") != 0:
                                continue

                            if not split_paragraphs:
                                current_text = ""
                                current_bold = None
                                current_bbox = list(b["bbox"])
                                for line in b.get("lines", []):
                                    for span in line.get("spans", []):
                                        t = span["text"]
                                        if not t.strip():
                                            current_text += t
                                            continue
                                        is_bold = "Bold" in span.get("font", "")
                                        if current_bold is None:
                                            current_bold = is_bold
                                        if is_bold != current_bold:
                                            if current_text.strip():
                                                ct = current_text.strip()
                                                only_url = bool(_re.match(r'^(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.\w+)\s*$', ct))
                                                if not ct.startswith("©") and not only_url:
                                                    extracted_blocks.append((tuple(current_bbox), ct, current_bold and len(ct) < 80))
                                            current_text = t
                                            current_bold = is_bold
                                        else:
                                            current_text += t
                                if current_text.strip() and current_bold is not None:
                                    ct = current_text.strip()
                                    only_url = bool(_re.match(r'^(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.\w+)\s*$', ct))
                                    if not ct.startswith("©") and not only_url:
                                        extracted_blocks.append((tuple(b["bbox"]), ct, current_bold and len(ct) < 80))
                                continue

                            paragraph_lines = []
                            for line in b.get("lines", []):
                                spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                                if not spans:
                                    continue
                                text = " ".join(s.get("text", "").strip() for s in spans).strip()
                                if not text or text.startswith("©"):
                                    continue
                                y0 = min(float(s["bbox"][1]) for s in spans)
                                y1 = max(float(s["bbox"][3]) for s in spans)
                                paragraph_lines.append({
                                    "text": text,
                                    "bold": any("Bold" in s.get("font", "") for s in spans),
                                    "bbox": (
                                        min(float(s["bbox"][0]) for s in spans),
                                        y0,
                                        max(float(s["bbox"][2]) for s in spans),
                                        y1,
                                    ),
                                    "y0": y0,
                                    "y1": y1,
                                })

                            current_group = []
                            for line in paragraph_lines:
                                if not current_group:
                                    current_group.append(line)
                                    continue

                                prev = current_group[-1]
                                gap = line["y0"] - prev["y1"]
                                prev_text = prev["text"].strip()
                                next_text = line["text"].strip()
                                sentence_break = bool(_re.search(r'[.!?:"”]$', prev_text))
                                continuation = bool(next_text[:1].islower())
                                new_paragraph = gap > 8 or (gap > 4 and sentence_break and not continuation)
                                if new_paragraph:
                                    text = " ".join(item["text"] for item in current_group).strip()
                                    only_url = bool(_re.match(r'^(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.\w+)\s*$', text))
                                    if text and not only_url:
                                        bbox = (
                                            min(item["bbox"][0] for item in current_group),
                                            min(item["bbox"][1] for item in current_group),
                                            max(item["bbox"][2] for item in current_group),
                                            max(item["bbox"][3] for item in current_group),
                                        )
                                        is_bold = current_group[0]["bold"] and len(text) < 120
                                        extracted_blocks.append((bbox, text, is_bold))
                                    current_group = [line]
                                else:
                                    current_group.append(line)

                            if current_group:
                                text = " ".join(item["text"] for item in current_group).strip()
                                only_url = bool(_re.match(r'^(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.\w+)\s*$', text))
                                if text and not only_url:
                                    bbox = (
                                        min(item["bbox"][0] for item in current_group),
                                        min(item["bbox"][1] for item in current_group),
                                        max(item["bbox"][2] for item in current_group),
                                        max(item["bbox"][3] for item in current_group),
                                    )
                                    is_bold = current_group[0]["bold"] and len(text) < 120
                                    extracted_blocks.append((bbox, text, is_bold))
                        if split_paragraphs and extracted_blocks:
                            merged_blocks = []
                            for bbox, text, is_bold in extracted_blocks:
                                if not merged_blocks:
                                    merged_blocks.append([list(bbox), text, is_bold])
                                    continue

                                prev_bbox, prev_text, prev_bold = merged_blocks[-1]
                                same_column = abs(prev_bbox[0] - bbox[0]) < 20 and abs(prev_bbox[2] - bbox[2]) < 80
                                vertical_gap = bbox[1] - prev_bbox[3]
                                prev_incomplete = not _re.search(r'[.!?:"”]$', prev_text.strip())
                                next_continuation = bool(text[:1].islower()) or bool(_re.match(r'^(the\b|copy\b|copyright\b|used by\b|all rights\b)', text.strip(), _re.IGNORECASE))
                                legal_continuation = bool(_re.match(r'^(the\b|copy\b|copyright\b|used by\b|all rights\b|yashandiswa\b|kodzero\b|munew\b|king james\b|version\b|de la bible\b)', text.strip(), _re.IGNORECASE))
                                merge_adjacent = False
                                if aggressive_merge:
                                    merge_adjacent = (
                                        same_column
                                        and vertical_gap <= 18
                                        and (
                                            (prev_bold or is_bold)
                                            or ((prev_incomplete and next_continuation) and len(prev_text) < 120 and len(text) < 120)
                                            or (legal_continuation and len(prev_text) < 160 and len(text) < 160)
                                        )
                                    )

                                if merge_adjacent:
                                    prev_bbox[0] = min(prev_bbox[0], bbox[0])
                                    prev_bbox[1] = min(prev_bbox[1], bbox[1])
                                    prev_bbox[2] = max(prev_bbox[2], bbox[2])
                                    prev_bbox[3] = max(prev_bbox[3], bbox[3])
                                    merged_blocks[-1][1] = f"{prev_text} {text}".strip()
                                    merged_blocks[-1][2] = False if len(merged_blocks[-1][1]) > 120 else (prev_bold and is_bold)
                                else:
                                    merged_blocks.append([list(bbox), text, False if len(text) > 120 else is_bold])

                            extracted_blocks = [(tuple(b), t, bold) for b, t, bold in merged_blocks]

                        return extracted_blocks

                    standard_front_base_doc = _fitz.open(f"/app/storage/{book.file_path}")

                    def _reset_page_to_clean_base(page, page_num):
                        page.add_redact_annot(page.rect, fill=(1, 1, 1))
                        page.apply_redactions()
                        page.show_pdf_page(page.rect, standard_front_base_doc, page_num, overlay=True)

                    def _insert_fitted_textbox(page, rect, text, *, bold=False, align=0, sizes=(12, 11, 10, 9, 8)):
                        content = (text or "").strip()
                        if not content:
                            return False
                        fontname = overlay_bold_name if bold else overlay_regular_name
                        fontfile = overlay_bold_file if bold else overlay_regular_file
                        for fs in sizes:
                            result = page.insert_textbox(
                                _fitz.Rect(rect),
                                _normalize_render_quotes(content),
                                fontsize=fs,
                                fontname=fontname,
                                fontfile=fontfile,
                                color=(0, 0, 0),
                                align=align,
                                overlay=True,
                            )
                            if result >= -2:
                                return True
                        return False

                    def _render_standard_promo_page(page):
                        title_src = (
                            "Whether you are searching for a Bible College, Christian University, "
                            "Theological Seminary or Christian College, you have come to the right place!"
                        )
                        line2_src = (
                            "Team Impact Christian University is an accredited online Christian learning "
                            "facility that caters for all levels of anointed Christian study."
                        )
                        line3_src = "Team Impact Christian University"
                        line4_src = "The house-hold name in ministry training"
                        website_src = "www.tiuniversity.com"
                        email_src = "info@tiuniversity.com"

                        title_tr, line2_tr, line3_tr, line4_tr, website_tr, email_tr = _batch_translate(
                            [title_src, line2_src, line3_src, line4_src, website_src, email_src],
                            source_code,
                            target_code,
                        )

                        for rect in (
                            _fitz.Rect(18, 20, page.rect.x1 - 18, 265),
                            _fitz.Rect(150, 520, page.rect.x1 - 150, 610),
                        ):
                            page.add_redact_annot(rect, fill=(1, 1, 1))
                        page.apply_redactions()

                        _insert_fitted_textbox(page, _fitz.Rect(26, 40, page.rect.x1 - 26, 88), title_tr, bold=False, align=1, sizes=(14, 13, 12, 11))
                        _insert_fitted_textbox(page, _fitz.Rect(40, 98, page.rect.x1 - 40, 172), line2_tr, bold=False, align=1, sizes=(12, 11, 10, 9, 8))
                        _insert_fitted_textbox(page, _fitz.Rect(110, 180, page.rect.x1 - 110, 214), line3_tr, bold=False, align=1, sizes=(13, 12, 11, 10))
                        _insert_fitted_textbox(page, _fitz.Rect(110, 218, page.rect.x1 - 110, 252), line4_tr, bold=False, align=1, sizes=(11, 10, 9, 8))
                        website_rect = _fitz.Rect(190, 540, page.rect.x1 - 190, 560)
                        email_rect = _fitz.Rect(185, 563, page.rect.x1 - 185, 585)
                        _insert_fitted_textbox(page, website_rect, website_tr, bold=False, align=1, sizes=(11, 10, 9))
                        _insert_fitted_textbox(page, email_rect, email_tr, bold=False, align=1, sizes=(11, 10, 9))
                        page.insert_link({
                            "kind": _fitz.LINK_URI,
                            "from": website_rect,
                            "uri": "https://www.tiuniversity.com",
                        })
                        page.insert_link({
                            "kind": _fitz.LINK_URI,
                            "from": email_rect,
                            "uri": "mailto:info@tiuniversity.com",
                        })

                    def _render_standard_preface_page(page, page_num):
                        title_src = "CHRISTIAN FOUNDATIONS"
                        para1_src = (
                            "This book is designed to provide condensed information. It is not intended to reprint "
                            "all the information that is otherwise available, but instead to complement, amplify and "
                            "supplement other texts. You are urged to read all the available material, learn as much "
                            "as possible and tailor the information to your individual needs. Every effort has been "
                            "made to make this book as complete and as accurate as possible. However, there may be "
                            "mistakes, both typographical and in content. Therefore, this text should be used only as "
                            "a general guide and not as the ultimate source of information. The author shall have "
                            "neither liability nor responsibility to any person or entity with respect to any loss or "
                            "damage caused, or alleged to have been caused, directly or indirectly, by the information "
                            "contained in this book."
                        )
                        para2_src = (
                            "No unauthorized copy of this book may be made and/or distributed in any way, whether "
                            "by copy or digital transfer to any other persons other than the person for which it is intended."
                        )
                        address_lines_src = [
                            "Published in South Africa by JOY MINISTRIES",
                            "P.O. Box 15611, Lambton, Germiston",
                            "South Africa. 1414",
                            "www.joyministries.com",
                            "Email: admin@joyministries.com",
                        ]
                        scripture_src = (
                            "All scripture quotations, unless otherwise indicated, are taken from the New King James "
                            "Version of the Bible. Copyright © 1982 by Thomas Nelson, Inc. Used by permission. "
                            "All rights reserved."
                        )

                        translated_strings = _batch_translate(
                            [title_src, para1_src, para2_src, *address_lines_src, scripture_src],
                            source_code,
                            target_code,
                        )
                        title_tr = translated_strings[0]
                        para1_tr = translated_strings[1]
                        para2_tr = translated_strings[2]
                        address_lines_tr = translated_strings[3:8]
                        scripture_tr = translated_strings[8]

                        title_rect = _fitz.Rect(80, 72, 515, 104)
                        para1_rect = _fitz.Rect(35, 100, 560, 258)
                        para2_rect = _fitz.Rect(30, 258, 565, 304)
                        address_clear_rect = _fitz.Rect(90, 306, 505, 370)
                        scripture_rect = _fitz.Rect(20, 374, 575, 454)

                        for rect in (title_rect, para1_rect, para2_rect, address_clear_rect, scripture_rect):
                            page.add_redact_annot(rect, fill=(1, 1, 1))
                        page.apply_redactions()

                        _insert_fitted_textbox(page, title_rect, title_tr, bold=True, align=1, sizes=(18, 17, 16, 15))
                        _insert_fitted_textbox(page, para1_rect, para1_tr, bold=False, align=0, sizes=(11, 10, 9, 8, 7))
                        _insert_fitted_textbox(page, para2_rect, para2_tr, bold=False, align=0, sizes=(11, 10, 9, 8, 7))
                        _insert_fitted_textbox(page, scripture_rect, scripture_tr, bold=False, align=0, sizes=(10, 9, 8, 7))

                        line_height = 12
                        address_y = 312
                        for idx, line in enumerate(address_lines_tr):
                            rect = _fitz.Rect(95, address_y + idx * line_height, 500, address_y + idx * line_height + 14)
                            _insert_fitted_textbox(page, rect, line, bold=False, align=1, sizes=(10, 9, 8))

                        website_rect = _fitz.Rect(150, address_y + 3 * line_height - 1, 445, address_y + 3 * line_height + 13)
                        email_rect = _fitz.Rect(120, address_y + 4 * line_height - 1, 475, address_y + 4 * line_height + 13)
                        page.insert_link({
                            "kind": _fitz.LINK_URI,
                            "from": website_rect,
                            "uri": "https://www.joyministries.com",
                        })
                        page.insert_link({
                            "kind": _fitz.LINK_URI,
                            "from": email_rect,
                            "uri": "mailto:admin@joyministries.com",
                        })

                    # --- Translate front matter in-place using overlay method ---
                    for page_num in range(front_matter_end_idx + 1):
                        # Workbook front matter is rebuilt from stored translated text below.
                        # Do not mutate original pages here, because cover/title pages are preserved exactly.
                        if workbook_like:
                            continue
                        page = orig_doc[page_num]
                        if page_num == 0:
                            continue  # keep uploaded cover exactly as-is

                        # Page 2 (index 1): translate span-by-span preserving exact position/size/color
                        if page_num == 1 and not workbook_like:
                            line_records = []
                            for block in page.get_text("dict").get("blocks", []):
                                if block.get("type") != 0:
                                    continue
                                for line in block.get("lines", []):
                                    spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
                                    if not spans:
                                        continue
                                    text_value = "".join(span.get("text", "") for span in spans).strip()
                                    if not text_value or text_value.startswith("©"):
                                        continue
                                    bbox = (
                                        min(float(span["bbox"][0]) for span in spans),
                                        min(float(span["bbox"][1]) for span in spans),
                                        max(float(span["bbox"][2]) for span in spans),
                                        max(float(span["bbox"][3]) for span in spans),
                                    )
                                    first = spans[0]
                                    c = first.get("color", 0)
                                    color = ((c >> 16 & 255)/255, (c >> 8 & 255)/255, (c & 255)/255)
                                    line_records.append({
                                        "bbox": bbox,
                                        "text": text_value,
                                        "size": first.get("size", 10),
                                        "bold": any("Bold" in span.get("font", "") for span in spans),
                                        "color": color,
                                        "origin_y": max(float(span.get("origin", (0, bbox[3]))[1]) for span in spans),
                                    })
                            if line_records:
                                for rec in line_records:
                                    page.add_redact_annot(_fitz.Rect(rec["bbox"]), fill=(1, 1, 1))
                                page.apply_redactions()
                                page_cx = page.rect.width / 2
                                for rec in line_records:
                                    trans = _translate_front_texts([rec["text"]])[0]
                                    fs = rec["size"]
                                    fontname = overlay_bold_name if rec["bold"] else overlay_regular_name
                                    fontfile = overlay_bold_file if rec["bold"] else overlay_regular_file
                                    tw = _fitz.get_text_length(trans, fontname="helv", fontsize=fs)
                                    x = page_cx - tw / 2
                                    y = rec["origin_y"]
                                    page.insert_text(_fitz.Point(x, y), trans, fontsize=fs, fontname=fontname, fontfile=fontfile, color=rec["color"])
                            continue
                        # Translate text blocks
                        split_front_matter_paragraphs = page_num in {2, 6}
                        text_blocks = _extract_text_blocks(
                            page,
                            split_paragraphs=split_front_matter_paragraphs,
                            aggressive_merge=False,
                        )
                        is_toc_page = _is_toc_page(page, text_blocks)
                        if is_toc_page and text_blocks:
                            def _is_toc_block(text):
                                value = (text or "").strip()
                                upper = value.upper()
                                return (
                                    "....." in value
                                    or "….." in value
                                    or "TABLE OF CONTENTS" in upper
                                    or "INHOUD" in upper
                                    or "YALIYOMO" in upper
                                    or "ZVIRI MUKATI" in upper
                                    or "TABLE DES" in upper
                                    or "ÍNDICE" in upper
                                    or "JEDWALI" in upper
                                    or "ATỌKA" in upper
                                )

                            filtered_blocks = []
                            seen_toc_texts = set()
                            for tb in text_blocks:
                                if not _is_toc_block(tb[1]):
                                    continue
                                normalized_text = _re.sub(r"\s+", " ", (tb[1] or "").strip()).upper()
                                if not normalized_text or normalized_text in seen_toc_texts:
                                    continue
                                seen_toc_texts.add(normalized_text)
                                filtered_blocks.append(tb)
                            text_blocks = filtered_blocks
                        if text_blocks:
                            translated = _translate_front_texts([t for _, t, _ in text_blocks])
                            if page_num == 2 and not is_toc_page:
                                # New-format books no longer use the old chart section on the
                                # examination page. Wipe the lower visual area so any baked-in
                                # chart/image content from the source PDF cannot survive.
                                page.draw_rect(
                                    _fitz.Rect(0, 215, page.rect.x1, page.rect.y1 - 28),
                                    color=(1, 1, 1),
                                    fill=(1, 1, 1),
                                    overlay=True,
                                )
                            if page_num == 4 and any(
                                marker in page.get_text("text", sort=True).upper()
                                for marker in ("CHRISTIAN FOUNDATIONS", "JOY MINISTRIES", "PUBLISHED IN SOUTH AFRICA")
                            ):
                                _render_standard_preface_page(page, page_num)
                                continue
                            elif is_toc_page:
                                toc_title = next((
                                    trans
                                    for (_bbox, orig, _b), trans in zip(text_blocks, translated)
                                    if any(
                                        marker in orig.upper()
                                        for marker in (
                                            "TABLE OF CONTENTS",
                                            "INHOUDSOPGAWE",
                                            "INHOUDS",
                                            "YALIYOMO",
                                            "ZVIRI MUKATI",
                                            "TABLE DES",
                                            "ÍNDICE",
                                            "JEDWALI",
                                            "ATỌKA",
                                        )
                                    )
                                ), translated[0] if translated else "Table of Contents")

                                def _clean_toc_entry(value):
                                    line = (value or "").strip()
                                    line = _re.sub(r'\.{2,}.*$', '', line).strip()
                                    line = _re.sub(r'\s*[-–—]?\s*\d+\s*$', '', line).strip()
                                    line = _re.sub(r'\s+', ' ', line)
                                    return line.strip(' -–—')

                                def _starts_toc_entry(value):
                                    candidate = (value or "").strip()
                                    if not candidate:
                                        return False
                                    if introduction_pattern.match(candidate):
                                        return True
                                    if _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+\d+\s*[:\-–]?\s*\D', candidate, _re.IGNORECASE):
                                        return True
                                    if _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?\s*\D', candidate, _re.IGNORECASE):
                                        return True
                                    return any(
                                        candidate.upper().startswith(marker)
                                        for marker in (
                                            "CONCLUSION",
                                            "APPENDIX",
                                            "BIBLIOGRAPHY",
                                            "MHEDZISO",
                                            "MABHUKU EMABHUKU",
                                            "OKUQUKETHWE",
                                            "ISIPHETHO",
                                            "ISENGEZO",
                                        )
                                    )

                                raw_toc_lines = [
                                    _clean_toc_entry(trans)
                                    for (_bbox, orig, _b), trans in zip(text_blocks, translated)
                                    if "....." in orig or "….." in orig
                                ]
                                toc_lines = []
                                for raw_line in raw_toc_lines:
                                    if not raw_line:
                                        continue
                                    upper_raw = raw_line.upper()
                                    if any(
                                        marker in upper_raw
                                        for marker in (
                                            "TABLE OF CONTENTS",
                                            "INHOUDSOPGAWE",
                                            "YALIYOMO",
                                            "ZVIRI MUKATI",
                                            "OKUQUKETHWE",
                                            "TABLE DES",
                                            "ÍNDICE",
                                            "ATỌKA",
                                        )
                                    ):
                                        continue
                                    if toc_lines and not _starts_toc_entry(raw_line):
                                        toc_lines[-1] = f"{toc_lines[-1]} {raw_line}".strip()
                                    else:
                                        toc_lines.append(raw_line)

                                page.add_redact_annot(page.rect, fill=(1, 1, 1))
                                page.apply_redactions()
                                _insert_fitted_textbox(
                                    page,
                                    _fitz.Rect(60, 95, page.rect.x1 - 60, 130),
                                    toc_title,
                                    bold=True,
                                    align=1,
                                    sizes=(20, 18, 16, 15, 14),
                                )
                                y = 168
                                for line in toc_lines:
                                    if y > page.rect.y1 - 48:
                                        break
                                    page.insert_text(
                                        _fitz.Point(70, y),
                                        line,
                                        fontsize=12,
                                        fontname=overlay_regular_name,
                                        fontfile=overlay_regular_file,
                                        color=(0,0,0),
                                        overlay=True,
                                    )
                                    y += 28
                                continue
                            else:
                                page_upper = page.get_text("text", sort=True).upper()
                                is_publishing_page = any(
                                    marker in page_upper
                                    for marker in (
                                        "PUBLISHED IN SOUTH AFRICA",
                                        "JOY MINISTRIES",
                                        "COPY OF THIS BOOK",
                                        "ALL RIGHTS RESERVED",
                                    )
                                )
                                if split_front_matter_paragraphs:
                                    page.add_redact_annot(page.rect, fill=(1, 1, 1))
                                    page.apply_redactions()
                                else:
                                    for (bbox, _, _b), _trans in zip(text_blocks, translated):
                                        page.add_redact_annot(_fitz.Rect(bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2), fill=(1,1,1))
                                    page.apply_redactions()
                                # Track y position per bbox to stack sub-blocks vertically
                                y_cursor = {}
                                pending_warning_tail_skip = False
                                for (bbox, orig_text, is_bold), trans in zip(text_blocks, translated):
                                    rect = _fitz.Rect(bbox)
                                    upper_orig = (orig_text or "").strip().upper()
                                    if pending_warning_tail_skip:
                                        if len(upper_orig) <= 100 and any(
                                            marker in upper_orig for marker in ("COURSE CODE", "STUDENT NUMBER", "INCLUDED")
                                        ):
                                            continue
                                        pending_warning_tail_skip = False
                                    # TOC page (index 5): expand dotted lines to full page width
                                    if is_toc_page and ("....." in orig_text or "….." in orig_text):
                                        import re as _re2
                                        m = _re2.search(r'(\d+)\s*$', trans.rstrip('.').strip())
                                        pagenum = m.group(1) if m else ""
                                        title = _re2.sub(r'\.{2,}.*', '', trans).strip()
                                        title = _re2.sub(r'\s*\d+\s*$', '', title).strip()
                                        left_x, right_x = rect.x0, page.rect.x1 - rect.x0
                                        fs = 9.0
                                        title_w = _fitz.get_text_length(title, fontname="helv", fontsize=fs)
                                        num_w = _fitz.get_text_length(pagenum, fontname="helv", fontsize=fs) if pagenum else 0
                                        dot_w = _fitz.get_text_length(".", fontname="helv", fontsize=fs)
                                        gap = (right_x - left_x) - title_w - num_w
                                        dots = "." * max(3, int(gap / dot_w))
                                        y = rect.y1 - 1
                                        page.insert_text(_fitz.Point(left_x, y), title, fontsize=fs, fontname=overlay_regular_name, fontfile=overlay_regular_file, color=(0,0,0))
                                        page.insert_text(_fitz.Point(left_x + title_w, y), dots, fontsize=fs, fontname="helv", color=(0,0,0))
                                        if pagenum:
                                            page.insert_text(_fitz.Point(right_x - num_w, y), pagenum, fontsize=fs, fontname="helv", color=(0,0,0))
                                    else:
                                        if "PLEASE ENSURE" in orig_text.upper():
                                            bbox_key = (round(bbox[0]), round(bbox[1]))
                                            y_start = y_cursor.get(bbox_key, rect.y0)
                                            cleaned_trans = " ".join((trans or "").split())
                                            warning_match = _re.search(r"([A-ZÀ-Þ][A-ZÀ-Þ\s,.;:’'\"-]{12,})$", cleaned_trans)
                                            if warning_match:
                                                paragraph_tr = cleaned_trans[:warning_match.start()].strip()
                                                warning_tr = warning_match.group(1).strip()
                                            else:
                                                paragraph_tr = cleaned_trans
                                                warning_tr = ""

                                            para_rect = _fitz.Rect(rect.x0, y_start, page.rect.x1 - 57, page.rect.y1 - 20)
                                            body_fs = 10
                                            warning_y = y_start + 72
                                            for fs in [10, 9, 8]:
                                                result = page.insert_textbox(
                                                    para_rect,
                                                    paragraph_tr,
                                                    fontsize=fs,
                                                    fontname=overlay_regular_name,
                                                    fontfile=overlay_regular_file,
                                                    color=(0, 0, 0),
                                                )
                                                if result >= 0:
                                                    body_fs = fs
                                                    tw = _fitz.get_text_length(paragraph_tr, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(para_rect.width), 1)))
                                                    warning_y = y_start + n_lines * fs * 1.35 + fs * 0.95
                                                    break

                                            if warning_tr:
                                                warning_rect = _fitz.Rect(rect.x0, warning_y, page.rect.x1 - 30, page.rect.y1 - 20)
                                                warning_text = " ".join(warning_tr.split())
                                                for fs in [11, 10, 9]:
                                                    result = page.insert_textbox(
                                                        warning_rect,
                                                        warning_text,
                                                        fontsize=fs,
                                                        fontname=overlay_bold_name,
                                                        fontfile=overlay_bold_file,
                                                        color=(0, 0, 0),
                                                        align=0,
                                                    )
                                                    if result >= 0:
                                                        tw = _fitz.get_text_length(warning_text, fontname="helv", fontsize=fs)
                                                        n_lines = max(1, -(-int(tw) // max(int(warning_rect.width), 1)))
                                                        y_cursor[bbox_key] = warning_y + n_lines * fs * 1.35 + fs * 0.35
                                                        break
                                                else:
                                                    y_cursor[bbox_key] = warning_y + body_fs * 2.2
                                            else:
                                                y_cursor[bbox_key] = warning_y
                                            pending_warning_tail_skip = True
                                            continue

                                        front_matter_body = split_front_matter_paragraphs and len(orig_text) > 40
                                        front_matter_warning = any(
                                            marker in orig_text.lower()
                                            for marker in [
                                                "please ensure",
                                                "ndapota",
                                            ]
                                        )
                                        force_plain = front_matter_body or any(
                                            marker in orig_text.lower()
                                            for marker in [
                                                "copyright",
                                                "published in",
                                                "all rights reserved",
                                                "copy of this book",
                                                "digital transfer",
                                                "joy ministries",
                                                "p.o. box",
                                                "email:",
                                            ]
                                        )
                                        use_bold = front_matter_warning or (is_bold and not force_plain)
                                        if front_matter_warning:
                                            fontfile_use = overlay_bold_file
                                            fontname_use = overlay_bold_name
                                            fs_use = 11
                                        else:
                                            fontfile_use = overlay_bold_file if use_bold else overlay_regular_file
                                            fontname_use = overlay_bold_name if use_bold else overlay_regular_name
                                            fs_use = 13 if use_bold else 10
                                        bbox_key = (round(bbox[0]), round(bbox[1]))
                                        y_start = y_cursor.get(bbox_key, rect.y0)
                                        front_matter_heading = split_front_matter_paragraphs and use_bold and len(orig_text) <= 80
                                        render_x1 = page.rect.x1 - 30 if front_matter_warning else (
                                            page.rect.x1 - 57 if (front_matter_body or front_matter_heading) else rect.x1
                                        )
                                        render_rect = _fitz.Rect(rect.x0, y_start, render_x1, page.rect.y1 - 20)
                                        bullet_items = []
                                        address_items = []
                                        forced_lines = []
                                        if front_matter_warning:
                                            forced_lines = [" ".join(trans.split())]
                                        if "•" in trans or "•" in orig_text:
                                            bullet_items = [item.strip(" •") for item in trans.split("•") if item.strip(" •")]
                                        elif (
                                            page_num == 6
                                            and len(orig_text.strip()) <= 32
                                            and (
                                                "2nd century" in orig_text.lower()
                                                or "century ad" in orig_text.lower()
                                                or _re.fullmatch(r"2\s*nd\.?", orig_text.strip(), _re.IGNORECASE)
                                                or _re.fullmatch(r"2", orig_text.strip())
                                            )
                                        ):
                                            # Redraw this century note once as a controlled overlay below.
                                            continue
                                        if bullet_items:
                                            for fs in [fs_use, fs_use-2, 7]:
                                                item_y = y_start
                                                fits = True
                                                for bullet_item in bullet_items:
                                                    bullet_label = f"• {bullet_item}"
                                                    item_rect = _fitz.Rect(render_rect.x0, item_y, render_rect.x1, page.rect.y1 - 20)
                                                    result = page.insert_textbox(item_rect, bullet_label, fontsize=fs, fontname=fontname_use, fontfile=fontfile_use, color=(0,0,0))
                                                    if result < 0:
                                                        fits = False
                                                        break
                                                    tw = _fitz.get_text_length(bullet_label, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(render_rect.width), 1)))
                                                    item_y += n_lines * fs * 1.35 + fs * 0.35
                                                if fits:
                                                    y_cursor[bbox_key] = item_y + fs * 0.35
                                                    break
                                        elif forced_lines:
                                            for fs in [fs_use, fs_use-2, 7]:
                                                item_y = y_start
                                                fits = True
                                                for forced_line in forced_lines:
                                                    item_rect = _fitz.Rect(render_rect.x0, item_y, render_rect.x1, page.rect.y1 - 20)
                                                    result = page.insert_textbox(item_rect, forced_line, fontsize=fs, fontname=fontname_use, fontfile=fontfile_use, color=(0,0,0), align=0)
                                                    if result < 0:
                                                        fits = False
                                                        break
                                                    tw = _fitz.get_text_length(forced_line, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(render_rect.width), 1)))
                                                    item_y += n_lines * fs * 1.35 + fs * 0.45
                                                if fits:
                                                    y_cursor[bbox_key] = item_y + fs * 0.35
                                                    break
                                        elif address_items:
                                            for fs in [fs_use, fs_use-2, 7]:
                                                item_y = y_start
                                                fits = True
                                                for address_item in address_items:
                                                    item_rect = _fitz.Rect(render_rect.x0, item_y, render_rect.x1, page.rect.y1 - 20)
                                                    result = page.insert_textbox(item_rect, address_item, fontsize=fs, fontname=fontname_use, fontfile=fontfile_use, color=(0,0,0), align=1)
                                                    if result < 0:
                                                        fits = False
                                                        break
                                                    tw = _fitz.get_text_length(address_item, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(render_rect.width), 1)))
                                                    item_y += n_lines * fs * 1.35 + fs * 0.35
                                                if fits:
                                                    y_cursor[bbox_key] = item_y + fs * 0.35
                                                    break
                                        else:
                                            for fs in [fs_use, fs_use-2, 7]:
                                                result = page.insert_textbox(render_rect, trans, fontsize=fs, fontname=fontname_use, fontfile=fontfile_use, color=(0,0,0))
                                                if result >= 0:
                                                    # Estimate height used and advance cursor
                                                    tw = _fitz.get_text_length(trans, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(render_rect.width), 1)))
                                                    gap_after = fs * 1.5 if use_bold else fs * 0.9
                                                    y_cursor[bbox_key] = y_start + n_lines * fs * 1.35 + gap_after
                                                    break

                                if page_num == 6:
                                    century_line = _batch_translate(["2nd Century AD."], source_code, target_code)[0]
                                    century_rect = _fitz.Rect(56, 436, 250, 452)
                                    page.draw_rect(century_rect, color=(1,1,1), fill=(1,1,1), overlay=True)
                                    page.insert_text(
                                        _fitz.Point(58, 447),
                                        century_line,
                                        fontsize=10,
                                        fontname=overlay_regular_name,
                                        fontfile=overlay_regular_file,
                                        color=(0,0,0),
                                        overlay=True,
                                    )
                    # --- Build body from stored translation using original PDF line styles ---
                    heading_style = ParagraphStyle("H", fontName=reportlab_bold_name, fontSize=15, spaceBefore=4, spaceAfter=2, leading=15, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    chapter_heading_style = ParagraphStyle("HC", fontName=reportlab_bold_name, fontSize=15, spaceBefore=4, spaceAfter=2, leading=15, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    intro_title_style = ParagraphStyle("IT", fontName=reportlab_bold_name, fontSize=15, spaceBefore=3, spaceAfter=1, leading=15, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    subhead_style = ParagraphStyle("SH", fontName=reportlab_bold_name, fontSize=9.5, spaceBefore=2, spaceAfter=1, leading=10.5, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    warning_line_style = ParagraphStyle("WARN", fontName=reportlab_bold_name, fontSize=8, spaceBefore=3, spaceAfter=1, leading=9.5, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    toc_line_style = ParagraphStyle("TOC", fontName=reportlab_regular_name, fontSize=12, spaceBefore=0, spaceAfter=2, leading=10.5, alignment=TA_LEFT, splitLongWords=0)
                    body_style = ParagraphStyle("B", fontName=reportlab_regular_name, fontSize=10, spaceBefore=0, spaceAfter=0, leading=10.5, alignment=TA_LEFT, splitLongWords=0)
                    body_style_bold = ParagraphStyle("BB", fontName=reportlab_bold_name, fontSize=10, spaceBefore=0, spaceAfter=0, leading=10.5, alignment=TA_LEFT, splitLongWords=0)
                    reference_style = ParagraphStyle("REF", fontName=reportlab_regular_name, fontSize=8, spaceBefore=0, spaceAfter=0, leading=9, alignment=TA_LEFT, wordWrap="CJK")
                    table_cell_style = ParagraphStyle("TC", fontName=reportlab_regular_name, fontSize=9.5, spaceBefore=0, spaceAfter=0, leading=10.5, alignment=TA_LEFT, splitLongWords=0)
                    table_header_style = ParagraphStyle("TH", fontName=reportlab_bold_name, fontSize=9.5, spaceBefore=0, spaceAfter=0, leading=10.5, alignment=TA_LEFT, splitLongWords=0)
                    indent_style = ParagraphStyle("IND", fontName=reportlab_regular_name, fontSize=10,
                        leftIndent=16, spaceBefore=0, spaceAfter=0, leading=10.5, alignment=TA_LEFT, splitLongWords=0)

                    def _new_body_doc(buffer):
                        return SimpleDocTemplate(
                            buffer,
                            pagesize=A4,
                            leftMargin=0.58*inch,
                            rightMargin=0.58*inch,
                            topMargin=0.65*inch,
                            bottomMargin=0.65*inch,
                        )

                    def _line_is_bold(spans):
                        total_chars = sum(len(s.get("text", "")) for s in spans)
                        if not total_chars:
                            return False
                        bold_chars = sum(
                            len(s.get("text", ""))
                            for s in spans
                            if "bold" in s.get("font", "").lower()
                        )
                        return bold_chars >= total_chars * 0.45

                    body_end_page_exclusive = max(body_start_page_idx, len(orig_doc) - 2)

                    def _source_line_records():
                        records = []
                        start_page = min(max(body_start_page_idx, 0), len(orig_doc))
                        end_page = min(max(body_end_page_exclusive, start_page), len(orig_doc))

                        def _normalize_line(value):
                            return _re.sub(r"\s+", " ", value or "").strip()

                        for source_page_num in range(start_page, end_page):
                            page = orig_doc[source_page_num]
                            page_dict = page.get_text("dict", sort=True)
                            styled_lines = []
                            previous_y1 = None
                            previous_text = ""
                            for block in page_dict.get("blocks", []):
                                if block.get("type") != 0:
                                    continue
                                for line in block.get("lines", []):
                                    spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                                    if not spans:
                                        continue
                                    styled_text = "".join(s.get("text", "") for s in spans).strip()
                                    if not styled_text:
                                        continue
                                    y0 = min(float(s.get("bbox", [0, 0, 0, 0])[1]) for s in spans)
                                    y1 = max(float(s.get("bbox", [0, 0, 0, 0])[3]) for s in spans)
                                    gap = (y0 - previous_y1) if previous_y1 is not None else 0
                                    # A sentence ending on the previous visual line is not
                                    # enough to start a new paragraph. PDF/DOCX extraction often
                                    # wraps normal body paragraphs line-by-line; only a clear
                                    # paragraph gap should block later line joining.
                                    starts_paragraph = previous_y1 is None or gap > 8
                                    span_x0s = sorted(float(s.get("bbox", [0, 0, 0, 0])[0]) for s in spans if s.get("text", "").strip())
                                    large_x_gaps = sum(1 for a, b in zip(span_x0s, span_x0s[1:]) if b - a > 85)
                                    styled_lines.append({
                                        "text": styled_text,
                                        "normalized": _normalize_line(styled_text),
                                        "bold": _line_is_bold(spans),
                                        "size": max(float(s.get("size", 11)) for s in spans),
                                        "y0": y0,
                                        "y1": y1,
                                        "starts_paragraph": starts_paragraph,
                                        "table_like": large_x_gaps >= 2 or bool(_re.search(r"\S+\s{8,}\S+\s{8,}\S+", styled_text)),
                                    })
                                    previous_y1 = y1
                                    previous_text = styled_text

                            style_cursor = 0
                            for extracted_line in page.get_text("text", sort=True).splitlines():
                                original_text = extracted_line.strip()
                                if not original_text:
                                    continue
                                normalized = _normalize_line(original_text)
                                matched_style = None
                                for idx in range(style_cursor, len(styled_lines)):
                                    styled = styled_lines[idx]
                                    if (
                                        normalized == styled["normalized"]
                                        or normalized in styled["normalized"]
                                        or styled["normalized"] in normalized
                                    ):
                                        matched_style = styled
                                        style_cursor = idx + 1
                                        break
                                if not matched_style:
                                    matched_style = {"bold": False, "size": 11, "starts_paragraph": False, "table_like": False}
                                records.append({
                                    "page_number": source_page_num + 1,
                                    "text": original_text,
                                    "bold": matched_style["bold"],
                                    "size": matched_style["size"],
                                    "starts_paragraph": matched_style.get("starts_paragraph", False),
                                    "table_like": matched_style.get("table_like", False),
                                })
                        return records

                    def _skip_body_record(record):
                        original = record["text"].strip()
                        if _re.match(r'^(?:[A-Z]{2,}\d{3}|I-[A-Z]{2,}\d{3})\b.+\b\d+\s*$', original, _re.IGNORECASE):
                            return True
                        if original.startswith("CC101 Christian Foundations"):
                            return True
                        if _re.match(r'^(CC101|BH505)\b', original, _re.IGNORECASE):
                            return True
                        if (
                            len(original) <= 100
                            and _re.search(r'\b(CC101|BH505)\b', original, _re.IGNORECASE)
                            and _re.search(r'\b\d+\b$', original)
                        ):
                            return True
                        if _re.fullmatch(r"\d+", original):
                            return True
                        return False

                    def _skip_translated_footer_line(text):
                        value = (text or "").strip()
                        if not value:
                            return False
                        upper = value.upper()
                        if _re.fullmatch(r"\d+", value):
                            return True
                        if _re.match(r'^(?:I[- ]?)?[A-Z]{2,}\d{3}\b.+\b\d+\s*(?:[•*\-])?\s*$', upper):
                            return True
                        if _re.match(r'^(?:I[- ]?)?DC210\b.+UKUHLAZIYWA.+\b\d+\s*(?:[•*\-])?\s*$', upper):
                            return True
                        if "BH505" in upper and _re.search(r"\b\d+\b$", upper):
                            return True
                        if "CC101" in upper and _re.search(r"\b\d+\b$", upper):
                            return True
                        if "APOSTOLIC EXPANSION" in upper and ("BH505" in upper or _re.search(r"\b\d+\b$", upper)):
                            return True
                        if "KUWEDZERA KWEVAAPOSTORI" in upper and ("BH505" in upper or _re.search(r"\b\d+\b$", upper)):
                            return True
                        if "CHRISTIAN FOUNDATIONS" in upper and ("CC101" in upper or _re.search(r"\b\d+\b$", upper)):
                            return True
                        if "NHEYO DZECHIKRISTU" in upper and ("CC101" in upper or _re.search(r"\b\d+\b$", upper)):
                            return True
                        return False

                    def _strip_translated_footer_prefix(text):
                        value = (text or "").strip()
                        if not value:
                            return value
                        # Handles merged footer+heading lines like:
                        # I-DC210 UKUHLAZIYWA KWEZEMVELO 52 KUFANELE...
                        value = _re.sub(
                            r'^(?:I[- ]?)?[A-Z]{2,}\d{3}\b\s+[^0-9\n]{6,}?\s+\d{1,4}\s+(?=[A-ZÀ-Þ0-9"“])',
                            '',
                            value,
                            count=1,
                        ).strip()
                        value = _re.sub(
                            r'\s+(?:I[- ]?)?[A-Z]{2,}\d{3}\b\s+[^0-9\n]{6,}?\s+\d{1,4}\s*$',
                            '',
                            value,
                            count=1,
                        ).strip()
                        return value

                    def _is_bible_reference_chapter_line(text):
                        value = (text or "").strip()
                        if not value:
                            return False
                        marker_re = r'(?:Isahluko|Izahluko|Sura(?:\s+ya)?|Sura|Chapter|Chapters|Hoofstuk|Hoofstukke|Chitsauko|Zvitsauko)'
                        if not _re.match(rf'^{marker_re}\s+\d+(?:[-–]\d+)?\s*:', value, _re.IGNORECASE):
                            return False
                        # Workbooks such as DC210/BG302 use dash-style real chapter headings in the TOC.
                        # In those books, colon-style chapter lines inside the body are Bible/scripture references.
                        try:
                            allows_colon_chapters = _body_allows_colon_chapter_headings_runtime
                        except NameError:
                            allows_colon_chapters = False
                        if not allows_colon_chapters:
                            return True
                        return False

                    def _starts_new_body_block(text):
                        value = (text or "").strip()
                        if _is_bible_reference_chapter_line(value):
                            return False
                        if not value:
                            return False
                        if _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]\s+\D', value, _re.IGNORECASE):
                            return True
                        if _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', value, _re.IGNORECASE):
                            return True
                        if value.startswith("• "):
                            return True
                        if _re.match(r'^\d+\. ', value):
                            return True
                        if _re.match(r'^[a-zA-Z]\) ', value):
                            return True
                        if _re.match(r'^\([ivxabc]+\)', value, _re.IGNORECASE):
                            return True
                        return False

                    def _is_parenthetical_tail(text):
                        value = (text or "").strip()
                        return len(value) <= 24 and bool(_re.fullmatch(r'\([^)]+\)', value))

                    def _is_form_or_checklist_line(text):
                        value = (text or "").strip()
                        if not value:
                            return False
                        if value.startswith("_____") or "_____" in value:
                            return True
                        if _re.match(r'^[-–—]\s*\S+', value):
                            return True
                        if _re.match(r'^[a-zA-Z]\.\s+\S+', value):
                            return True
                        if _re.match(r'^[a-zA-Z]\)\s+\S+', value):
                            return True
                        return False

                    def _should_join_with_previous(prev_text, current_text):
                        prev = (prev_text or "").strip()
                        curr = (current_text or "").strip()
                        if not prev or not curr:
                            return False
                        if _is_form_or_checklist_line(curr) or _is_form_or_checklist_line(prev):
                            # Lettered workbook prompts often wrap across source lines;
                            # keep their continuation with the prompt. Blank/checklist
                            # lines must remain separate.
                            if (
                                _re.match(r'^[a-zA-Z]\.\s+\S+', prev)
                                and not _is_form_or_checklist_line(curr)
                                and not _starts_new_body_block(curr)
                                and not _re.search(r'[.!?]\s*$', prev)
                            ):
                                return True
                            return False
                        if _is_parenthetical_tail(curr):
                            return True
                        if _starts_new_body_block(curr):
                            return False
                        if prev.endswith((" -", " –", "“", "\"", "(", "/", ":", ";")):
                            return True
                        connector_tail = _re.search(
                            r'\b(?:and|or|of|to|the|a|an|na|ya|wa|la|za|kwa|katika|ili|de|van|en|du|des)$',
                            prev,
                            _re.IGNORECASE,
                        )
                        if connector_tail and curr[:1].islower():
                            return True
                        return False

                    def _split_embedded_chapter_marker(text):
                        value = (text or "").strip()
                        if not value:
                            return [text]
                        parts = _re.split(
                            r'(?=\b(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D)',
                            value,
                            maxsplit=1,
                            flags=_re.IGNORECASE,
                        )
                        if len(parts) == 2 and parts[0].strip():
                            return [parts[0].strip(), parts[1].strip()]
                        return [text]

                    def _is_toc_like_line(value):
                        candidate = (value or "").strip()
                        if not candidate:
                            return False
                        if _re.search(r'\.{2,}\s*\d+\s*$', candidate):
                            return True
                        if candidate.count(".") >= 8:
                            return True
                        return False

                    def _is_toc_heading_like_line(value):
                        candidate = (value or "").strip().upper()
                        if not candidate:
                            return False
                        return any(
                            marker in candidate
                            for marker in (
                                "TABLE OF CONTENTS",
                                "INHOUDSOPGAWE",
                                "YALIYOMO",
                                "ZVIRI MUKATI",
                                "OKUQUKETHWE",
                                "TABLE DES",
                                "ÍNDICE",
                                "ATỌKA",
                            )
                        )

                    def _is_body_heading_candidate(value):
                        candidate = (value or "").strip()
                        if not candidate:
                            return False
                        if _is_toc_like_line(candidate) or _is_toc_heading_like_line(candidate):
                            return False
                        if introduction_pattern.match(candidate) and "....." not in candidate:
                            return True
                        if _re.match(
                            r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D',
                            candidate,
                            _re.IGNORECASE,
                        ):
                            return True
                        return False

                    def _is_standalone_body_line(text):
                        value = (text or "").strip()
                        if not value:
                            return False
                        if _starts_new_body_block(value):
                            return True
                        if _is_form_or_checklist_line(value):
                            return True
                        if _is_toc_like_line(value) or _is_toc_heading_like_line(value):
                            return True
                        if _re.match(r'^\d+:\d+', value):
                            return True
                        if _re.match(r"^[A-ZÀ-Þ0-9\s,\"”’'().:-]{8,}$", value) and len(value) <= 140:
                            return True
                        return False

                    def _find_body_start_index(lines):
                        for idx, line in enumerate(lines):
                            candidate = (line or "").strip()
                            if not candidate or _is_toc_like_line(candidate) or _is_toc_heading_like_line(candidate):
                                continue
                            if not _is_body_heading_candidate(candidate):
                                continue
                            lookahead = []
                            for next_line in lines[idx + 1:]:
                                nxt = (next_line or "").strip()
                                if not nxt:
                                    continue
                                lookahead.append(nxt)
                                if len(lookahead) >= 4:
                                    break
                            if not lookahead:
                                continue
                            if any(
                                not _is_toc_like_line(nxt)
                                and not _is_toc_heading_like_line(nxt)
                                and not _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', nxt, _re.IGNORECASE)
                                for nxt in lookahead
                            ):
                                return idx
                        return 0

                    all_translated_lines = rendered_translated_text.split("\n")

                    def _exam_heading_like_line(value):
                        candidate = (value or "").strip()
                        return bool(_re.match(r'^(EXAMINATION|UKUHLOLWA|EKSAMEN|KUONGORORA|EXAMEN|ÉPREUVE)\b', candidate, _re.IGNORECASE))

                    def _course_title_like_line(value):
                        candidate = (value or "").strip()
                        return bool(_re.search(r'\b[A-Z]{2,}\d{3}\b', candidate))

                    def _clean_toc_entry_text(value):
                        candidate = (value or "").strip()
                        candidate = _re.sub(r'\.{2,}.*$', '', candidate).strip()
                        candidate = _re.sub(r'\s*[-–—]?\s*\d+\s*$', '', candidate).strip()
                        candidate = _re.sub(r'\s+', ' ', candidate)
                        return candidate.strip(' -–—')

                    def _starts_toc_entry_text(value):
                        candidate = (value or "").strip()
                        if not candidate:
                            return False
                        if introduction_pattern.match(candidate):
                            return True
                        if _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', candidate, _re.IGNORECASE):
                            return True
                        if _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?\s*\D', candidate, _re.IGNORECASE):
                            return True
                        return any(
                            candidate.upper().startswith(marker)
                            for marker in (
                                'CONCLUSION', 'APPENDIX', 'BIBLIOGRAPHY', 'MHEDZISO', 'MABHUKU EMABHUKU', 'ISINGENISO', 'ISANDULELO',
                            )
                        )

                    def _next_nonempty_cleaned_line(lines, start_idx):
                        idx = start_idx
                        while idx < len(lines):
                            candidate = (lines[idx] or "").strip()
                            if candidate:
                                return candidate, _clean_toc_entry_text(candidate)
                            idx += 1
                        return "", ""

                    def _explode_toc_entry_text(value):
                        cleaned = _clean_toc_entry_text(value)
                        if not cleaned:
                            return []
                        # Some workbook translations store multiple TOC entries in one long line.
                        # Split them back out at known entry markers and then trim each segment.
                        marker_re = _re.compile(
                            r'(?=(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO(?:\s+[^-–]{1,40})?|HOOFSTUK|ÌSỌRÍ|SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING|CONCLUSION|APPENDIX|BIBLIOGRAPHY|MHEDZISO|MABHUKU EMABHUKU|ISINGENISO(?:\s+SENKQUBO|\s+SESIFUNDO)?|ISANDULELO|OKUQUKETHWE|PREFACE)\b)',
                            _re.IGNORECASE,
                        )
                        starts = sorted(set(match.start() for match in marker_re.finditer(cleaned)))
                        if not starts:
                            return [cleaned]
                        if starts[0] != 0:
                            starts = [0] + starts
                        parts = []
                        for idx, start in enumerate(starts):
                            end = starts[idx + 1] if idx + 1 < len(starts) else len(cleaned)
                            part = cleaned[start:end].strip(' -–—')
                            part = _re.sub(r'\s+', ' ', part).strip()
                            if part:
                                parts.append(part)
                        normalized_parts = []
                        for part in parts:
                            if normalized_parts and part.upper() == normalized_parts[-1].upper():
                                continue
                            normalized_parts.append(part)
                        return normalized_parts

                    def _looks_like_toc_entry_title(candidate):
                        value = _clean_toc_entry_text(candidate)
                        if not value:
                            return False
                        if len(value) > 120:
                            return False
                        if _re.search(r'[;!?]', value):
                            return False
                        if value.count('.') > 1:
                            return False
                        words = _re.findall(r"[\wÀ-ÿ’'-]+", value)
                        if len(words) > 16:
                            return False
                        if any(w[:1].islower() for w in words[1:] if len(w) > 2):
                            return False
                        return True

                    def _is_workbook_toc_entry_line(value):
                        candidate = _clean_toc_entry_text(value)
                        if not candidate or not _looks_like_toc_entry_title(candidate):
                            return False
                        if _is_toc_heading_like_line(candidate) or _exam_heading_like_line(candidate):
                            return False
                        if introduction_pattern.match(candidate) and "....." not in candidate:
                            return True
                        if _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', candidate, _re.IGNORECASE):
                            return True
                        if _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?\s*\D', candidate, _re.IGNORECASE):
                            return True
                        return any(
                            candidate.upper().startswith(marker)
                            for marker in (
                                'CONCLUSION', 'APPENDIX', 'BIBLIOGRAPHY', 'MHEDZISO',
                                'MABHUKU EMABHUKU', 'ISITHASISELO', 'PREFACE', 'ISANDULELO',
                            )
                        )

                    def _derive_workbook_toc_entries(lines):
                        entries = []
                        seen = set()
                        for raw in lines:
                            candidate = (raw or '').strip()
                            if not candidate:
                                continue
                            for part in _explode_toc_entry_text(candidate):
                                normalized = _clean_toc_entry_text(part)
                                if not normalized:
                                    continue
                                if not _is_workbook_toc_entry_line(normalized):
                                    continue
                                key = normalized.upper()
                                if key in seen:
                                    continue
                                seen.add(key)
                                entries.append(normalized)
                        return entries

                    def _derive_body_toc_entries(lines, allow_colon_chapters=False, limit=0):
                        entries = []
                        seen = set()
                        seen_chapter_or_section = False
                        heading_connector_re = _re.compile(
                            r"\b(?:OF|TO|FOR|AND|YA|WA|NA|KWA|KUELEKEA|KUHUSU|ILI|VAN|EN|NAAR|DE|DU|DES|LA|LE|LES|DEL)\s*\Z",
                            _re.IGNORECASE,
                        )
                        completed_lines = []
                        _line_idx = 0
                        while _line_idx < len(lines):
                            _line = (lines[_line_idx] or "").strip()
                            if heading_connector_re.search(_line) and _line_idx + 1 < len(lines):
                                _next_line = (lines[_line_idx + 1] or "").strip()
                                _next_words = _re.findall(r"[\wÀ-ÿ’'-]+", _next_line)
                                _short_title_tail = bool(_next_words) and len(_next_words) <= 5 and not _re.search(r'[.!?"“”]', _next_line)
                                _first_word = _re.match(r"^([\wÀ-ÿ’'-]+)(?:\s+.+)?$", _next_line)
                                if _short_title_tail:
                                    completed_lines.append(f"{_line} {_next_line}")
                                    _line_idx += 1
                                elif _first_word:
                                    completed_lines.append(f"{_line} {_first_word.group(1)}")
                                    _line_idx += 1
                                else:
                                    completed_lines.append(_line)
                            else:
                                completed_lines.append(_line)
                            _line_idx += 1
                        lines = completed_lines
                        chapter_dash_re = _re.compile(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[-–]\s+\D', _re.IGNORECASE)
                        chapter_colon_re = _re.compile(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*:\s+\D', _re.IGNORECASE)
                        section_re = _re.compile(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?\s*\D', _re.IGNORECASE)
                        terminal_markers = ('CONCLUSION', 'APPENDIX', 'BIBLIOGRAPHY', 'MHEDZISO', 'MABHUKU EMABHUKU', 'ISITHASISELO', 'PREFACE', 'ISANDULELO')
                        for raw in lines:
                            candidate = (raw or '').strip()
                            if not candidate:
                                continue
                            for part in _explode_toc_entry_text(candidate):
                                normalized = _clean_toc_entry_text(part)
                                if not normalized or _is_toc_heading_like_line(normalized):
                                    continue
                                upper = normalized.upper()
                                starts_like_heading = bool(normalized[:1].isupper())
                                first_token = (normalized.split() or [''])[0]
                                section_marker_is_heading = first_token.isupper()
                                is_intro = bool(introduction_pattern.match(normalized)) and not seen_chapter_or_section
                                is_section = starts_like_heading and section_marker_is_heading and bool(section_re.match(normalized))
                                is_chapter = starts_like_heading and (bool(chapter_dash_re.match(normalized)) or (allow_colon_chapters and bool(chapter_colon_re.match(normalized))))
                                is_major = is_intro or is_section or is_chapter or any(upper.startswith(marker) for marker in terminal_markers)
                                if not is_major:
                                    continue
                                if upper in seen:
                                    continue
                                seen.add(upper)
                                entries.append(normalized)
                                if is_section or is_chapter:
                                    seen_chapter_or_section = True
                                if limit and len(entries) >= limit:
                                    return entries
                        return entries

                    def _is_body_start_heading(value):
                        candidate = (value or '').strip()
                        if not candidate:
                            return False
                        return bool(
                            introduction_pattern.match(candidate)
                            or chapter_1_pattern.match(candidate)
                            or _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', candidate, _re.IGNORECASE)
                        )

                    raw_lines = all_translated_lines
                    workbook_front_story = []
                    workbook_front_cutoff_index = None
                    toc_title_text = None
                    toc_entries = []
                    toc_end_index = None
                    intro_heading_after_toc = None
                    intro_title_text = None
                    body_heading_after_toc = None
                    toc_heading_index = next((i for i, line in enumerate(raw_lines) if _is_toc_heading_like_line(line)), None)
                    if toc_heading_index is not None:
                        toc_title_text = _clean_toc_entry_text(raw_lines[toc_heading_index]) or raw_lines[toc_heading_index].strip()
                        idx = toc_heading_index + 1
                        while idx < len(raw_lines):
                            candidate = (raw_lines[idx] or '').strip()
                            if not candidate:
                                idx += 1
                                continue
                            cleaned = _clean_toc_entry_text(candidate)
                            if not cleaned:
                                idx += 1
                                continue
                            # Stop TOC when we hit long prose or a non-TOC introduction heading.
                            next_raw, next_cleaned = _next_nonempty_cleaned_line(raw_lines, idx + 1)
                            if introduction_pattern.match(cleaned) and next_cleaned and not _starts_toc_entry_text(next_cleaned):
                                intro_heading_after_toc = cleaned
                                break
                            exploded_parts = _explode_toc_entry_text(cleaned)
                            if not exploded_parts:
                                idx += 1
                                continue
                            stop_toc = False
                            for part in exploded_parts:
                                normalized = _clean_toc_entry_text(part)
                                if not normalized:
                                    continue
                                if toc_title_text and normalized.upper() == toc_title_text.upper():
                                    continue
                                if introduction_pattern.match(normalized) and next_cleaned and not _starts_toc_entry_text(next_cleaned):
                                    intro_heading_after_toc = normalized
                                    stop_toc = True
                                    break
                                is_entry = _starts_toc_entry_text(normalized)
                                if not is_entry:
                                    stop_toc = True
                                    break
                                else:
                                    if not toc_entries or toc_entries[-1].upper() != normalized.upper():
                                        toc_entries.append(normalized)
                            if stop_toc:
                                break
                            idx += 1
                        toc_end_index = idx
                    body_start_index = _find_body_start_index(raw_lines)
                    if workbook_like:
                        workbook_body_start_index = body_start_index
                        if toc_heading_index is not None:
                            idx = toc_heading_index + 1
                            while idx < len(raw_lines):
                                candidate = (raw_lines[idx] or '').strip()
                                if not candidate:
                                    idx += 1
                                    continue
                                next_raw, next_cleaned = _next_nonempty_cleaned_line(raw_lines, idx + 1)
                                is_workbook_body_heading = bool(
                                    introduction_pattern.match(candidate)
                                    or chapter_1_pattern.match(candidate)
                                    or _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', candidate, _re.IGNORECASE)
                                )
                                if is_workbook_body_heading and not _is_toc_like_line(candidate):
                                    workbook_body_start_index = idx
                                    body_heading_after_toc = _clean_toc_entry_text(candidate) or candidate
                                    if introduction_pattern.match(candidate):
                                        intro_heading_after_toc = body_heading_after_toc
                                    break
                                if is_workbook_body_heading and next_cleaned and not _starts_toc_entry_text(next_cleaned):
                                    workbook_body_start_index = idx
                                    body_heading_after_toc = _clean_toc_entry_text(candidate) or candidate
                                    if introduction_pattern.match(candidate):
                                        intro_heading_after_toc = body_heading_after_toc
                                    break
                                idx += 1
                        body_start_index = workbook_body_start_index
                        if body_start_index < len(raw_lines):
                            first_body_candidate = (raw_lines[body_start_index] or '').strip()
                            if first_body_candidate:
                                if not intro_heading_after_toc and introduction_pattern.match(first_body_candidate):
                                    intro_heading_after_toc = _clean_toc_entry_text(first_body_candidate) or first_body_candidate
                                if not body_heading_after_toc and (
                                    _is_body_start_heading(first_body_candidate)
                                    or chapter_1_pattern.match(first_body_candidate)
                                    or _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', first_body_candidate, _re.IGNORECASE)
                                ):
                                    body_heading_after_toc = _clean_toc_entry_text(first_body_candidate) or first_body_candidate
                        def _raw_index_after_nonempty(lines, count):
                            seen = 0
                            for _idx, _line in enumerate(lines):
                                if (_line or "").strip():
                                    seen += 1
                                    if seen >= count:
                                        return _idx + 1
                            return min(len(lines), count)

                        front_start_index = _raw_index_after_nonempty(raw_lines, _cover_line_count)
                        if _cached_front_matter_available:
                            for _idx, _line in enumerate(raw_lines[front_start_index:body_start_index], front_start_index):
                                _upper_line = (_line or "").strip().upper()
                                if any(_m in _upper_line for _m in ("TEAM IMPACT", "IYUNIVESITHI", "YUNIVHESITI", "UNIVERSITY")):
                                    front_start_index = _idx
                                    break
                        # Keep workbook cover page exactly as the uploaded PDF.
                        # Front-matter translation starts after the cover.
                        cover_lines = []
                        title_page_lines = []
                        front_lines = raw_lines[front_start_index:body_start_index]
                        exam_idx = next((i for i, line in enumerate(front_lines) if _exam_heading_like_line(line)), None)
                        toc_rel_idx = next((i for i, line in enumerate(front_lines) if _is_toc_heading_like_line(line)), None)
                        manual_lines = front_lines[:exam_idx] if exam_idx is not None else []
                        leading_title_lines = []
                        while manual_lines:
                            first_manual = (manual_lines[0] or "").strip()
                            if _course_title_like_line(first_manual) or (len(first_manual) <= 90 and _re.search(r"\b(?:BH|BG|DC|CC)\d{3}\b|\b(?:Moses|Mose|uMose)\b", first_manual, _re.IGNORECASE)):
                                leading_title_lines.append(manual_lines.pop(0))
                                continue
                            break
                        if leading_title_lines:
                            title_page_lines = leading_title_lines + title_page_lines
                        exam_lines = front_lines[exam_idx:toc_rel_idx] if (exam_idx is not None and toc_rel_idx is not None) else (front_lines[exam_idx:] if exam_idx is not None else [])
                        # Drop title/footer fragments that PDF extraction can place after the exam page and before TOC.
                        while exam_lines:
                            last_exam = (exam_lines[-1] or "").strip()
                            if not last_exam:
                                exam_lines.pop()
                                continue
                            if len(last_exam) <= 90 and (_course_title_like_line(last_exam) or _re.search(r"\b(?:BH|BG|DC|CC)\d{3}\b|\b(?:Moses|Mose)\b", last_exam, _re.IGNORECASE) or "umose" in last_exam.lower()):
                                exam_lines.pop()
                                continue
                            break
                        if exam_lines:
                            _title_split_idx = next((i for i, line in enumerate(exam_lines[1:], 1) if _course_title_like_line(line) or _re.search(r"\b(BH|BG|DC|CC)\d{3}\b", line or "", _re.IGNORECASE)), None)
                            if _title_split_idx is not None:
                                title_page_lines = exam_lines[_title_split_idx:]
                                exam_lines = exam_lines[:_title_split_idx]
                        # Generic workbook front-matter slot mapping.
                        # Use original PDF page roles/counts, not translated keywords, so all languages follow one path.
                        _slot_body_start_index = None
                        _slot_title_lines = []
                        _slot_manual_lines = []
                        _slot_exam_lines = []
                        _slot_toc_lines = []

                        def _orig_nonempty_count(_page_idx):
                            if _page_idx < 0 or _page_idx >= len(orig_doc):
                                return 0
                            return len([_ln for _ln in orig_doc[_page_idx].get_text("text", sort=True).splitlines() if _ln.strip()])

                        def _orig_page_text_upper(_page_idx):
                            if _page_idx < 0 or _page_idx >= len(orig_doc):
                                return ""
                            return orig_doc[_page_idx].get_text("text", sort=True).upper()

                        if _stored_translated_lines:
                            _course_code_from_original = ""
                            if len(orig_doc) > 1:
                                _p1_joined_for_code = " ".join([ln.strip() for ln in orig_doc[1].get_text("text", sort=True).splitlines() if ln.strip()])
                                _code_match = _re.search(r"\b(?:BH|BG|DC|CC)\d{3}\b", _p1_joined_for_code, _re.IGNORECASE)
                                _course_code_from_original = _code_match.group(0).upper() if _code_match else ""

                            _title_idx = 1 if len(_stored_translated_lines) > 1 else None
                            if _course_code_from_original:
                                _title_idx = next((i for i, ln in enumerate(_stored_translated_lines[:12]) if _course_code_from_original in (ln or '').upper()), _title_idx)

                            _email_idx = next((i for i, ln in enumerate(_stored_translated_lines) if "dean@tiuniversity.com" in (ln or '').lower()), None)
                            _dot_idx = next((i for i, ln in enumerate(_stored_translated_lines) if i > ((_email_idx or 0) + 1) and _re.search(r'\.{5,}|…{2,}', ln or '')), None)

                            if _title_idx is not None and _email_idx is not None and _dot_idx is not None:
                                _exam_candidates = []
                                for _i in range(max((_title_idx or 0) + 1, _email_idx - 14), _email_idx + 1):
                                    _line = (_stored_translated_lines[_i] or '').strip()
                                    if not _line or "@" in _line or len(_line) > 90:
                                        continue
                                    if _re.search(r'[.!?]$', _line):
                                        continue
                                    if _re.search(r'©|copyright|hakimiliki|kopiereg|haki zote|regte voorbehou|reserved', _line, _re.IGNORECASE):
                                        continue
                                    _exam_candidates.append(_i)
                                _exam_start_idx = _exam_candidates[-1] if _exam_candidates else max((_title_idx or 0) + 1, _email_idx - 6)

                                _toc_start_idx = _dot_idx
                                _prev = (_stored_translated_lines[_dot_idx - 1] or '').strip() if _dot_idx > 0 else ""
                                if _prev and len(_prev) <= 90 and not _re.search(r'[.!?]$', _prev) and "@" not in _prev:
                                    _toc_start_idx = _dot_idx - 1

                                _toc_end_idx = _dot_idx + 1
                                while _toc_end_idx < len(_stored_translated_lines):
                                    _line = (_stored_translated_lines[_toc_end_idx] or '').strip()
                                    if not _line:
                                        _toc_end_idx += 1
                                        continue
                                    if _re.search(r'\.{5,}|…{2,}', _line):
                                        _toc_end_idx += 1
                                        continue
                                    # Some translators split a TOC entry from its dot-leader/page-number line.
                                    _next = (_stored_translated_lines[_toc_end_idx + 1] or '').strip() if _toc_end_idx + 1 < len(_stored_translated_lines) else ""
                                    if len(_line) <= 130 and _next and _re.search(r'\.{5,}|…{2,}', _next):
                                        _toc_end_idx += 1
                                        continue
                                    break

                                _slot_title_lines = _stored_translated_lines[_title_idx:_title_idx + 1]
                                _slot_manual_lines = _stored_translated_lines[_title_idx + 1:_exam_start_idx]
                                _slot_exam_lines = _stored_translated_lines[_exam_start_idx:_toc_start_idx]
                                _slot_toc_lines = _stored_translated_lines[_toc_start_idx:_toc_end_idx]
                                _slot_body_start_index = _toc_end_idx

                        if _slot_body_start_index is None and _stored_translated_lines and len(orig_doc) >= 5:
                            _title_only_idx = None
                            if len(orig_doc) > 1:
                                _p1_lines_for_slot = [ln.strip() for ln in orig_doc[1].get_text("text", sort=True).splitlines() if ln.strip()]
                                _p1_joined_for_slot = " ".join(_p1_lines_for_slot)
                                if _p1_lines_for_slot and len(_p1_lines_for_slot) <= 3 and len(_p1_joined_for_slot) <= 120 and not _re.search(r"HOW TO USE|EXAMINATION|TABLE OF CONTENTS", _p1_joined_for_slot, _re.IGNORECASE):
                                    _title_only_idx = 1

                            _search_start = 2 if _title_only_idx == 1 else 1
                            _exam_page_idx = next((i for i in range(_search_start, min(10, len(orig_doc))) if "EXAMINATION" in _orig_page_text_upper(i)), None)
                            _toc_page_idx = next((i for i in range(_search_start, min(12, len(orig_doc))) if "TABLE OF CONTENTS" in _orig_page_text_upper(i)), None)
                            if _exam_page_idx is not None and _toc_page_idx is not None and _exam_page_idx < _toc_page_idx:
                                _slot_cursor = _orig_nonempty_count(0)
                                if _title_only_idx is not None:
                                    _title_count = _orig_nonempty_count(_title_only_idx)
                                    _slot_title_lines = _stored_translated_lines[_slot_cursor:_slot_cursor + _title_count]
                                    _slot_cursor += _title_count
                                _manual_start = _search_start
                                _manual_count = sum(_orig_nonempty_count(i) for i in range(_manual_start, _exam_page_idx))
                                _slot_manual_lines = _stored_translated_lines[_slot_cursor:_slot_cursor + _manual_count]
                                _slot_cursor += _manual_count
                                _exam_count = sum(_orig_nonempty_count(i) for i in range(_exam_page_idx, _toc_page_idx))
                                _slot_exam_lines = _stored_translated_lines[_slot_cursor:_slot_cursor + _exam_count]
                                _slot_cursor += _exam_count
                                _toc_count = _orig_nonempty_count(_toc_page_idx)
                                _slot_toc_lines = _stored_translated_lines[_slot_cursor:_slot_cursor + _toc_count]
                                _slot_cursor += _toc_count
                                _slot_body_start_index = _slot_cursor

                        raw_toc_lines = raw_lines[toc_heading_index + 1:body_start_index] if (toc_heading_index is not None and body_start_index > toc_heading_index) else []
                        _slot_mapping_active = _slot_body_start_index is not None
                        if _slot_mapping_active:
                            title_page_lines = _slot_title_lines
                            manual_lines = _slot_manual_lines
                            exam_lines = _slot_exam_lines
                            raw_toc_lines = _slot_toc_lines
                            raw_lines = _stored_translated_lines
                            body_start_index = _slot_body_start_index
                            if raw_toc_lines:
                                _slot_toc_set = {(_ln or '').strip() for _ln in raw_toc_lines if (_ln or '').strip()}
                                exam_lines = [
                                    _ln for _ln in exam_lines
                                    if (_ln or '').strip() not in _slot_toc_set and not _re.search(r'\.{5,}', _ln or '')
                                ]
                            _log.getLogger(__name__).warning(f'workbook slot map title={title_page_lines[:2]!r} manual_count={len(manual_lines)} exam_count={len(exam_lines)} toc_count={len(raw_toc_lines)} body_start={body_start_index}')
                        if raw_toc_lines and not body_heading_after_toc:
                            for raw_line in raw_toc_lines:
                                candidate = _clean_toc_entry_text(raw_line)
                                if not candidate:
                                    continue
                                if _is_body_start_heading(candidate) or chapter_1_pattern.match(candidate) or _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', candidate, _re.IGNORECASE):
                                    body_heading_after_toc = candidate
                                    if introduction_pattern.match(candidate):
                                        intro_heading_after_toc = candidate
                                    break
                        import logging as _log
                        _log.getLogger(__name__).warning(f'workbook toc split intro={intro_heading_after_toc!r} body_heading={body_heading_after_toc!r} raw_first={raw_toc_lines[:3]!r}')
                        intro_title_text = next(
                            (
                                _clean_toc_entry_text(line)
                                for line in raw_toc_lines
                                if introduction_pattern.match(_clean_toc_entry_text(line) or line.strip())
                            ),
                            intro_heading_after_toc,
                        )
                        seen_toc_entries = set()
                        toc_entries = []
                        for toc_line in raw_toc_lines:
                            cleaned_line = _clean_toc_entry_text(toc_line)
                            if not cleaned_line:
                                continue
                            if body_heading_after_toc and cleaned_line.upper().startswith(body_heading_after_toc.upper()) and not _slot_mapping_active:
                                break
                            for part in _explode_toc_entry_text(cleaned_line):
                                normalized = _clean_toc_entry_text(part)
                                if not normalized:
                                    continue
                                if body_heading_after_toc and normalized.upper().startswith(body_heading_after_toc.upper()) and not _slot_mapping_active:
                                    break
                                if toc_title_text and normalized.upper() == toc_title_text.upper():
                                    continue
                                if not _is_workbook_toc_entry_line(normalized):
                                    continue
                                key = normalized.upper()
                                if key in seen_toc_entries:
                                    continue
                                seen_toc_entries.add(key)
                                toc_entries.append(normalized)
                        if _slot_body_start_index is not None and raw_toc_lines and not toc_entries:
                            _fallback_toc = []
                            _seen_fallback_toc = set()
                            for _toc_line in raw_toc_lines:
                                _clean = _clean_toc_entry_text(_toc_line)
                                if not _clean:
                                    continue
                                if toc_title_text and _clean.upper() == toc_title_text.upper():
                                    continue
                                _clean = _re.sub(r'\s*\.{3,}\s*\d+\s*$', '', _clean).strip()
                                _clean = _re.sub(r'\s+\d+\s*$', '', _clean).strip()
                                if not _clean:
                                    continue
                                _key = _clean.upper()
                                if _key in _seen_fallback_toc:
                                    continue
                                _seen_fallback_toc.add(_key)
                                _fallback_toc.append(_clean)
                            if _fallback_toc:
                                toc_entries = _fallback_toc
                                if not toc_title_text:
                                    toc_title_text = _clean_toc_entry_text(raw_toc_lines[0]) or 'Table of Contents'

                        def _merge_front_matter_paragraph_lines(lines, *, preserve_first_heading=False):
                            merged = []
                            buffer = []

                            def _is_front_heading(value, idx):
                                candidate = (value or '').strip()
                                if not candidate:
                                    return True
                                if preserve_first_heading and idx == 0 and len(candidate) <= 90:
                                    return True
                                if _exam_heading_like_line(candidate) or _is_toc_heading_like_line(candidate):
                                    return True
                                if len(candidate) <= 140 and candidate.isupper():
                                    return True
                                if _course_title_like_line(candidate):
                                    return True
                                return False

                            def _flush():
                                nonlocal buffer
                                if buffer:
                                    merged.append(_re.sub(r'\s+', ' ', ' '.join(buffer)).strip())
                                    buffer = []

                            def _should_join_front(prev, curr):
                                prev = (prev or '').strip()
                                curr = (curr or '').strip()
                                if not prev or not curr:
                                    return False
                                if _is_toc_heading_like_line(curr) or _exam_heading_like_line(curr):
                                    return False
                                if curr.isupper() and len(curr) <= 140:
                                    return False
                                if _re.search(r'\b(?:and|or|of|to|the|a|an|na|ya|kwa|katika|ili|wa|la|za|van|en|de|du|des)$', prev, _re.IGNORECASE):
                                    return True
                                if not _re.search(r'[.!?:;"”)]\s*$', prev):
                                    return True
                                if curr[:1].islower():
                                    return True
                                return False

                            for idx, raw in enumerate(lines or []):
                                line = (raw or '').strip()
                                if not line:
                                    _flush()
                                    continue
                                if _is_front_heading(line, idx):
                                    _flush()
                                    merged.append(line)
                                    continue
                                if buffer and _should_join_front(buffer[-1], line):
                                    buffer.append(line)
                                else:
                                    _flush()
                                    buffer.append(line)
                            _flush()
                            return merged

                        if cover_lines:
                            for _idx, line in enumerate(cover_lines):
                                safe_line = _normalize_render_quotes(line).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                if _idx == 0:
                                    workbook_front_story.append(Spacer(1, 0.55*inch))
                                    workbook_front_story.append(Paragraph(safe_line, ParagraphStyle("COVER_TITLE", parent=heading_style, fontSize=18, leading=22, alignment=1)))
                                else:
                                    workbook_front_story.append(Spacer(1, 0.18*inch))
                                    workbook_front_story.append(Paragraph(safe_line, ParagraphStyle("COVER_SUB", parent=heading_style, fontSize=16, leading=20, alignment=1)))
                            workbook_front_story.append(PageBreak())
                        if manual_lines:
                            manual_lines = _merge_front_matter_paragraph_lines(manual_lines, preserve_first_heading=True)
                            workbook_front_story.append(Spacer(1, 0.2*inch))
                            for idx, line in enumerate(manual_lines):
                                safe_line = _normalize_render_quotes(line).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                                if idx == 0 and len(line) <= 90:
                                    workbook_front_story.append(Paragraph(safe_line, heading_style))
                                elif line.isupper() and len(line) <= 90:
                                    workbook_front_story.append(Paragraph(safe_line, subhead_style))
                                else:
                                    workbook_front_story.append(Paragraph(safe_line, body_style))
                            workbook_front_story.append(PageBreak())
                        if exam_lines:
                            exam_lines = _merge_front_matter_paragraph_lines(exam_lines, preserve_first_heading=True)
                            def _is_front_matter_updated_line(_line: str) -> bool:
                                _text = (_line or '').strip()
                                if not _text:
                                    return False
                                return bool(_re.match(
                                    r'^(?:updated|opgedateer|kubuyekezwe|yakagadziridzwa|hersien|revised|mis[eè]\s+[àa]\s+jour|actualizado|atualizado)\b',
                                    _text,
                                    _re.IGNORECASE,
                                ))
                            _merged_exam_lines = []
                            _i = 0
                            while _i < len(exam_lines):
                                _line = (exam_lines[_i] or '').strip()
                                _upper = _line.upper()
                                if (
                                    _line
                                    and any(_marker in _upper for _marker in ('PLEASE ENSURE', 'TAFADHALI HAKIKISHA', 'MAAK ASSEBLIEF', 'NDAPOTA'))
                                ):
                                    _parts = [_line]
                                    _j = _i + 1
                                    while _j < len(exam_lines) and len(_parts) < 4:
                                        _next = (exam_lines[_j] or '').strip()
                                        _next_upper = _next.upper()
                                        if not _next:
                                            _j += 1
                                            continue
                                        if not _next_upper.isupper():
                                            break
                                        _parts.append(_next)
                                        _j += 1
                                        if any(_end in _next_upper for _end in ('INCLUDED', 'INGESLUIT', 'IMEJUMUISHWA', 'ZVASANGANISWA')):
                                            break
                                    _merged_exam_lines.append(' '.join(_parts))
                                    _i = _j
                                    continue
                                _merged_exam_lines.append(_line)
                                _i += 1
                            exam_lines = _merged_exam_lines
                            _inserted_updated_page_break = False
                            for idx, line in enumerate(exam_lines):
                                if idx > 0 and not _inserted_updated_page_break and _is_front_matter_updated_line(line):
                                    workbook_front_story.append(PageBreak())
                                    _inserted_updated_page_break = True
                                _warning_end = _re.search(r'\b(INCLUDED|INGESLUIT|IMEJUMUISHWA|ZVASANGANISWA)\b\.?', line or '', _re.IGNORECASE)
                                if _warning_end and any(_marker in (line or '').upper() for _marker in ('PLEASE ENSURE', 'TAFADHALI HAKIKISHA', 'MAAK ASSEBLIEF', 'NDAPOTA')):
                                    line = line[:_warning_end.end()].strip()
                                    line = _re.sub(r'\s+NI\s+IMEJUMUISHWA\b', ' IMEJUMUISHWA', line, flags=_re.IGNORECASE)
                                safe_line = _normalize_render_quotes(line).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                                if idx == 0:
                                    workbook_front_story.append(Paragraph(safe_line, heading_style))
                                elif line.isupper() and any(_marker in line.upper() for _marker in ('PLEASE ENSURE', 'TAFADHALI HAKIKISHA', 'MAAK ASSEBLIEF', 'NDAPOTA')):
                                    workbook_front_story.append(Paragraph(safe_line, warning_line_style))
                                elif line.isupper() and len(line) <= 140:
                                    workbook_front_story.append(Paragraph(safe_line, subhead_style))
                                else:
                                    workbook_front_story.append(Paragraph(safe_line, body_style))
                            workbook_front_story.append(PageBreak())
                        # title_page_lines are rendered as the translated title-only page during assembly
                        # so the workbook cover/title/manual page order remains stable.
                        if len(toc_entries) < 4:
                            fallback_toc_entries = _derive_workbook_toc_entries(raw_toc_lines)
                            if len(fallback_toc_entries) > len(toc_entries):
                                toc_entries = fallback_toc_entries
                        # If translation collapsed the TOC, recover entries from translated body headings.
                        # The original TOC decides whether chapter headings are dash-style or colon-style,
                        # preventing Bible-reference lines from being promoted into the TOC.
                        if body_start_index < len(raw_lines):
                            original_toc_entries = []
                            for _page_idx in range(0, min(12, len(orig_doc))):
                                if 'TABLE OF CONTENTS' in _orig_page_text_upper(_page_idx):
                                    original_toc_entries = _derive_workbook_toc_entries(orig_doc[_page_idx].get_text('text', sort=True).splitlines())
                                    break
                            allow_colon_chapters = any(_re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*:', _entry, _re.IGNORECASE) for _entry in original_toc_entries)
                            body_toc_entries = _derive_body_toc_entries(
                                raw_lines[body_start_index:],
                                allow_colon_chapters=allow_colon_chapters,
                                limit=0,
                            )
                            def _toc_entry_needs_completion(_entry):
                                return bool(_re.search(r"\b(?:OF|TO|FOR|AND|YA|WA|NA|KWA|KUELEKEA|KUHUSU|ILI|VAN|EN|NAAR|DE|DU|DES|LA|LE|LES|DEL)\s*$", _entry or "", _re.IGNORECASE))
                            def _toc_entries_are_more_complete(_body_entries, _toc_entries):
                                if not _body_entries or len(_body_entries) < len(_toc_entries):
                                    return False
                                for _old, _new in zip(_toc_entries, _body_entries):
                                    if _toc_entry_needs_completion(_old) and len((_new or "").split()) > len((_old or "").split()):
                                        return True
                                return False
                            if (not toc_entries or len(toc_entries) < 4) and len(body_toc_entries) > len(toc_entries):
                                toc_entries = body_toc_entries
                            elif _toc_entries_are_more_complete(body_toc_entries, toc_entries):
                                toc_entries = body_toc_entries
                        if toc_entries:
                            intro_heading_after_toc = next(
                                (entry for entry in toc_entries if introduction_pattern.match(entry)),
                                intro_heading_after_toc,
                            )
                            body_heading_after_toc = next(
                                (
                                    entry for entry in toc_entries
                                    if _is_body_start_heading(entry)
                                    or chapter_1_pattern.match(entry)
                                    or _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', entry, _re.IGNORECASE)
                                ),
                                body_heading_after_toc,
                            )
                        intro_title_text = intro_heading_after_toc
                        if toc_entries and toc_title_text:
                            def _final_workbook_toc_cleanup(_entries):
                                _cleaned_entries = []
                                _seen_entries = set()
                                _seen_chapter = False
                                _chapter_re = _re.compile(r'^(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[-–:]\s+\D', _re.IGNORECASE)
                                _section_re = _re.compile(r'^(?:SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?\s*\D', _re.IGNORECASE)
                                _terminal_re = _re.compile(r'^(?:CONCLUSION|APPENDIX|AANHANGSEL|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|MHEDZISO|HITIMISHO|MABHUKU EMABHUKU|ISITHASISELO|PREFACE|ISANDULELO)\b', _re.IGNORECASE)
                                for _entry in _entries or []:
                                    _value = _clean_toc_entry_text(_entry)
                                    if not _value:
                                        continue
                                    _is_intro = bool(introduction_pattern.match(_value)) and not _seen_chapter
                                    _is_major = _is_intro or bool(_chapter_re.match(_value)) or bool(_section_re.match(_value)) or bool(_terminal_re.match(_value))
                                    if not _is_major or not _looks_like_toc_entry_title(_value):
                                        continue
                                    if _seen_chapter and introduction_pattern.match(_value):
                                        continue
                                    _key = _re.sub(r'\s+', ' ', _value).strip().upper()
                                    if _key in _seen_entries:
                                        continue
                                    _seen_entries.add(_key)
                                    _cleaned_entries.append(_value)
                                    if _chapter_re.match(_value) or _section_re.match(_value):
                                        _seen_chapter = True
                                return _cleaned_entries
                            render_toc_entries = _final_workbook_toc_cleanup(toc_entries) or toc_entries
                            def _toc_canon(_value):
                                return _re.sub(r'[^A-Z0-9]+', '', _re.sub(r"\s+", " ", (_value or '').strip()).upper())
                            toc_title_value = _re.sub(r"\s+", " ", (toc_title_text or "").strip()).upper()
                            body_heading_value = _re.sub(r"\s+", " ", (body_heading_after_toc or "").strip()).upper()
                            intro_heading_value = _re.sub(r"\s+", " ", (intro_heading_after_toc or "").strip()).upper()
                            toc_aliases = {_toc_canon(toc_title_value), _toc_canon(body_heading_value), _toc_canon(intro_heading_value)}
                            render_toc_entries = [
                                _entry for _entry in render_toc_entries
                                if _toc_canon(_entry) not in toc_aliases
                                and not _is_body_start_heading(_entry)
                                and not chapter_1_pattern.match(_entry or '')
                            ]
                            import logging as _log
                            _log.getLogger(__name__).warning(f'workbook front matter intro={intro_heading_after_toc!r} toc_count={len(render_toc_entries)} title={toc_title_text!r}')
                            title_safe = _normalize_render_quotes(toc_title_text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                            toc_block_lines = []
                            workbook_front_story.append(Spacer(1, 0.25*inch))
                            for cleaned in render_toc_entries:
                                safe_line = _normalize_render_quotes(cleaned).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                if not safe_line:
                                    continue
                                if toc_block_lines and toc_block_lines[-1].strip().upper() == safe_line.strip().upper():
                                    continue
                                toc_block_lines.append(safe_line)
                            if toc_block_lines and toc_block_lines[0].strip().upper() == title_safe.strip().upper():
                                toc_block_lines = toc_block_lines[1:]
                            toc_block = "<br/>".join(toc_block_lines)
                            if toc_block:
                                workbook_front_story.append(Paragraph(toc_block, ParagraphStyle("WORKBOOK_TOC_BLOCK", parent=toc_line_style, fontSize=12, leading=18, alignment=TA_LEFT, spaceAfter=0, spaceBefore=0)))
                            workbook_front_cutoff_index = body_start_index
                    if toc_end_index is not None and not ('_slot_mapping_active' in locals() and _slot_mapping_active):
                        body_start_index = max(body_start_index, toc_end_index)
                    if workbook_front_cutoff_index is not None and not ('_slot_mapping_active' in locals() and _slot_mapping_active):
                        body_start_index = max(body_start_index, workbook_front_cutoff_index)
                    raw_lines = raw_lines[body_start_index:]
                    first_nonempty_idx = next((i for i, line in enumerate(raw_lines) if (line or '').strip()), None)
                    if first_nonempty_idx is not None:
                        first_nonempty = (raw_lines[first_nonempty_idx] or '').strip()
                        import logging as _log
                        _log.getLogger(__name__).warning(f'body first_nonempty={first_nonempty!r} body_heading={body_heading_after_toc!r} intro={intro_title_text!r}')
                    source_records = _source_line_records()
                    source_index = 0
                    translated_records = []
                    paragraph_buffer = []
                    paragraph_experiment_enabled = isinstance(cache_variant, str) and 'platypus-paragraph-experiment' in cache_variant

                    def _peek_source_record():
                        if source_index >= len(source_records):
                            return None
                        return source_records[source_index]

                    def _take_source_record():
                        nonlocal source_index
                        if source_index >= len(source_records):
                            return None
                        record = source_records[source_index]
                        source_index += 1
                        return record

                    def _looks_like_source_subheading(text, source_record):
                        value = (text or "").strip()
                        if not value or not source_record:
                            return False
                        if _starts_new_body_block(value):
                            return True
                        if value.endswith(":") and len(value) <= 100:
                            return True
                        source_bold = bool(source_record.get("bold"))
                        source_size = float(source_record.get("size", 11) or 11)
                        words = _re.findall(r'[\wÀ-ÿ-]+', value)
                        word_count = len(words)
                        ends_sentence = bool(_re.search(r'[.!?]$', value))
                        title_caseish = all(
                            w[:1].isupper() or w.isupper()
                            for w in words
                            if len(w) > 2
                        ) if words else False
                        if source_bold and source_size >= 11.5 and word_count <= 14 and not ends_sentence:
                            return True
                        if source_bold and title_caseish and word_count <= 16 and len(value) <= 120:
                            return True
                        if title_caseish and word_count <= 10 and len(value) <= 90 and not ends_sentence:
                            return True
                        return False

                    def _looks_like_isolated_translated_heading(text, prev_text, next_text, source_record):
                        value = (text or "").strip()
                        if not value:
                            return False
                        if _starts_new_body_block(value):
                            return True
                        if _looks_like_source_subheading(value, source_record):
                            return True
                        prev_blank = not (prev_text or "").strip()
                        next_blank = not (next_text or "").strip()
                        if len(value) > 120:
                            return False
                        if value.endswith(":"):
                            return True
                        if _re.search(r'[.!?]$', value):
                            return False
                        words = _re.findall(r'[\wÀ-ÿ-]+', value)
                        if not words:
                            return False
                        word_count = len(words)
                        title_caseish = all(
                            w[:1].isupper() or w.isupper()
                            for w in words
                            if len(w) > 2
                        )
                        next_value = (next_text or "").strip()
                        next_looks_body = len(next_value) > 60 or len(_re.findall(r'[\wÀ-ÿ-]+', next_value)) >= 10
                        if word_count <= 8 and title_caseish and next_looks_body:
                            return True
                        if not (prev_blank or next_blank):
                            return False
                        return word_count <= 16 and title_caseish

                    def _split_trailing_subheading(text, source_record):
                        value = (text or "").strip()
                        if not value or not _re.search(r'[?!"”:]\s+', value):
                            return None
                        match = _re.match(r'^(.*?[?!"”:])\s+(.+)$', value)
                        if not match:
                            return None
                        prefix, tail = match.group(1).strip(), match.group(2).strip()
                        if not tail or len(tail) > 90 or _re.search(r'[.!?]$', tail):
                            return None
                        words = _re.findall(r'[\wÀ-ÿ-]+', tail)
                        if not words or len(words) > 10:
                            return None
                        title_caseish = all(
                            w[:1].isupper() or w.isupper()
                            for w in words
                            if len(w) > 2
                        )
                        if not title_caseish:
                            return None
                        if not _looks_like_source_subheading(tail, source_record) and not _looks_like_isolated_translated_heading(tail, "", "", source_record):
                            return None
                        return prefix, tail

                    def _flush_paragraph_buffer():
                        nonlocal paragraph_buffer
                        if not paragraph_buffer:
                            return
                        text = " ".join(part.strip() for part in paragraph_buffer if part and part.strip()).strip()
                        if text:
                            source_record = _take_source_record()
                            if source_record is not None:
                                translated_records.append({
                                    "text": text,
                                    "source": source_record,
                                })
                        paragraph_buffer = []

                    def _looks_like_hard_boundary_line(text, source_record):
                        value = (text or '').strip()
                        if not value:
                            return True
                        if _starts_new_body_block(value):
                            return True
                        if _is_toc_heading_like_line(value) or _is_toc_like_line(value):
                            return True
                        if _is_form_or_checklist_line(value):
                            return True
                        if value.startswith('• '):
                            return True
                        if _re.match(r'^\(?[ivxabc]+\)', value, _re.IGNORECASE):
                            return True
                        if _re.match(r'^\d+(?:\.|:)\s+', value):
                            return True
                        if _looks_like_source_subheading(value, source_record):
                            return True
                        if len(value) <= 140 and value.isupper():
                            return True
                        return False

                    def _should_join_experiment(prev_text, current_text, current_source):
                        prev = (prev_text or '').strip()
                        curr = (current_text or '').strip()
                        if not prev or not curr:
                            return False
                        if _looks_like_hard_boundary_line(curr, current_source):
                            return False
                        if _re.search(r'\b(?:and|or|of|to|the|a|an|na|ya|wa|la|za|kwa|katika|ili|de|van|en|du|des)$', prev, _re.IGNORECASE):
                            return True
                        if not _re.search(r'[.!?:;"”)]\s*$', prev):
                            return True
                        if curr[:1].islower():
                            return True
                        return False

                    def _current_buffer_looks_like_subheading():
                        if not paragraph_buffer:
                            return False
                        return _looks_like_source_subheading(paragraph_buffer[0].strip(), _peek_source_record())

                    def _last_translated_record_looks_like_subheading():
                        if not translated_records:
                            return False
                        last = translated_records[-1]
                        return _looks_like_source_subheading(last.get("text", "").strip(), last.get("source"))

                    for idx, line in enumerate(raw_lines):
                        p = line.strip()
                        prev_line = raw_lines[idx - 1] if idx > 0 else ""
                        next_line = raw_lines[idx + 1] if idx + 1 < len(raw_lines) else ""
                        current_source = _peek_source_record()
                        if not p:
                            _flush_paragraph_buffer()
                            continue
                        if p in (":", ";"):
                            if paragraph_buffer:
                                paragraph_buffer[-1] = paragraph_buffer[-1].rstrip() + p
                                _take_source_record()
                                continue
                            if translated_records:
                                translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + p
                                _take_source_record()
                                continue
                        if current_source and current_source.get("table_like"):
                            _flush_paragraph_buffer()
                            source_record = _take_source_record()
                            if source_record is None:
                                break
                            translated_records.append({"text": line, "source": source_record})
                            continue
                        if current_source and current_source.get("starts_paragraph") and paragraph_buffer:
                            prev_buffer_text = paragraph_buffer[-1].strip() if paragraph_buffer else ""
                            continuation_after_connector = bool(
                                _re.search(r'\b(?:and|or|na|ya|kwa|of|to|the|a|an|de|van|en)$', prev_buffer_text, _re.IGNORECASE)
                                and p
                                and not _starts_new_body_block(p)
                                and not _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source)
                            )
                            if paragraph_experiment_enabled and _should_join_experiment(prev_buffer_text, p, current_source):
                                continuation_after_connector = True
                            if not continuation_after_connector:
                                _flush_paragraph_buffer()
                        if _current_buffer_looks_like_subheading():
                            _flush_paragraph_buffer()
                        if _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source):
                            _flush_paragraph_buffer()
                        split_parts = _split_embedded_chapter_marker(line) if p else [line]
                        if len(split_parts) == 2:
                            _flush_paragraph_buffer()
                            source_record = _take_source_record()
                            if source_record is None:
                                break
                            prefix_part, chapter_part = split_parts
                            if translated_records and prefix_part and not _last_translated_record_looks_like_subheading() and _should_join_with_previous(translated_records[-1]["text"], prefix_part):
                                translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + prefix_part.strip()
                            elif prefix_part.strip():
                                translated_records.append({
                                    "text": prefix_part,
                                    "source": source_record,
                                })
                            translated_records.append({
                                "text": chapter_part,
                                "source": source_record,
                            })
                            continue
                        trailing_subheading_parts = _split_trailing_subheading(p, current_source)
                        if trailing_subheading_parts:
                            _flush_paragraph_buffer()
                            source_record = _take_source_record()
                            if source_record is None:
                                break
                            prefix_part, subheading_part = trailing_subheading_parts
                            if prefix_part:
                                translated_records.append({
                                    "text": prefix_part,
                                    "source": source_record,
                                })
                            translated_records.append({
                                "text": subheading_part,
                                "source": source_record,
                            })
                            continue
                        if translated_records and p[:1].islower() and not _looks_like_hard_boundary_line(p, current_source) and _re.search(r'\b(?:and|or|of|to|the|a|an|na|ya|wa|la|za|kwa|katika|ili|de|van|en|du|des)$', translated_records[-1]["text"].strip(), _re.IGNORECASE):
                            translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + p
                            continue
                        if paragraph_buffer and p[:1].islower() and not _looks_like_hard_boundary_line(p, current_source) and _re.search(r'\b(?:and|or|of|to|the|a|an|na|ya|wa|la|za|kwa|katika|ili|de|van|en|du|des)$', paragraph_buffer[-1].strip(), _re.IGNORECASE):
                            paragraph_buffer[-1] = paragraph_buffer[-1].rstrip() + " " + p
                            continue
                        if paragraph_buffer and _re.match(r'^\d+:\d+', p) and not _current_buffer_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")):
                            paragraph_buffer[-1] = paragraph_buffer[-1].rstrip() + " " + p
                        elif paragraph_buffer and (_should_join_with_previous(paragraph_buffer[-1], p) or (paragraph_experiment_enabled and _should_join_experiment(paragraph_buffer[-1], p, current_source))) and not _current_buffer_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")):
                            paragraph_buffer[-1] = paragraph_buffer[-1].rstrip() + " " + p
                        elif (
                            _looks_like_source_subheading(p, current_source)
                            or _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source)
                            or _is_standalone_body_line(p)
                        ):
                            _flush_paragraph_buffer()
                            source_record = _take_source_record()
                            if source_record is None:
                                break
                            if p.startswith("• "):
                                bullet_split = _re.match(r'^(•\s*["“].+?["”])\s+(.+)$', p)
                                if bullet_split:
                                    translated_records.append({
                                        "text": bullet_split.group(1),
                                        "source": source_record,
                                    })
                                    translated_records.append({
                                        "text": bullet_split.group(2),
                                        "source": source_record,
                                    })
                                else:
                                    translated_records.append({
                                        "text": line,
                                        "source": source_record,
                                    })
                            else:
                                translated_records.append({
                                    "text": line,
                                    "source": source_record,
                                })
                        elif translated_records and p and _re.match(r'^\d+:\d+', p) and not _last_translated_record_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")) and not _looks_like_source_subheading(p, current_source) and not _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source):
                            translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + p
                        elif translated_records and p and (_should_join_with_previous(translated_records[-1]["text"], p) or (paragraph_experiment_enabled and _should_join_experiment(translated_records[-1]["text"], p, current_source))) and not _last_translated_record_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")) and not _looks_like_source_subheading(p, current_source) and not _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source):
                            translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + p
                        else:
                            _flush_paragraph_buffer()
                            source_record = _take_source_record()
                            if source_record is None:
                                break
                            translated_records.append({
                                "text": line,
                                "source": source_record,
                            })

                    _flush_paragraph_buffer()

                    def _normalize_lettered_prompt_fragments(records):
                        normalized = []
                        idx = 0
                        while idx < len(records):
                            rec = records[idx]
                            text = (rec.get("text") or "").strip()
                            if _re.match(r'^\d+\.?$', text) and idx + 1 < len(records):
                                next_rec = records[idx + 1]
                                next_text = (next_rec.get("text") or "").strip()
                                next_words = _re.findall(r"\b[\wÀ-ÿ-]+\b", next_text)
                                if (
                                    next_text
                                    and len(next_text) <= 120
                                    and len(next_words) <= 14
                                    and not _starts_new_body_block(next_text)
                                    and not _is_toc_like_line(next_text)
                                ):
                                    normalized.append({**rec, "text": text.rstrip('.') + ". " + next_text})
                                    idx += 2
                                    continue
                            if (
                                _re.match(r'^[a-zA-Z]\.\s+\S+', text)
                                and not _re.search(r'[.!?]\s*$', text)
                                and idx + 1 < len(records)
                            ):
                                next_rec = records[idx + 1]
                                next_text = (next_rec.get("text") or "").strip()
                                if next_text in (":", ";"):
                                    normalized.append({**rec, "text": text.rstrip() + next_text})
                                    idx += 2
                                    continue
                                if (
                                    next_text
                                    and not _starts_new_body_block(next_text)
                                    and not _is_toc_heading_like_line(next_text)
                                    and not _is_toc_like_line(next_text)
                                    and not _looks_like_source_subheading(next_text, next_rec.get("source"))
                                    and len(text) <= 45
                                ):
                                    normalized.append({**rec, "text": text.rstrip() + " " + next_text})
                                    idx += 2
                                    continue
                            normalized.append(rec)
                            idx += 1
                        return normalized

                    def _normalize_fragmented_chapter_titles(records):
                        normalized = []
                        idx = 0
                        heading_start_re = _re.compile(
                            r'^(?:'
                            r'(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–:]{1,40})'
                            r'|'
                            r'(?:SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+'
                            r')\s*[:\-–]\s*(?:\D.*)?$',
                            _re.IGNORECASE,
                        )
                        incomplete_heading_re = _re.compile(
                            r'^(?:'
                            r'(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–:]{1,40})'
                            r'|'
                            r'(?:SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+'
                            r')\s*[:\-–]\s*$',
                            _re.IGNORECASE,
                        )
                        heading_connector_re = _re.compile(
                            r'\b(?:OF|TO|FOR|AND|YA|WA|NA|KWA|KUELEKEA|KUHUSU|ILI|VAN|EN|NAAR|DE|DU|DES|LA|LE|LES|DEL)\s*$',
                            _re.IGNORECASE,
                        )
                        while idx < len(records):
                            rec = records[idx]
                            text = (rec.get("text") or "").strip()
                            if heading_start_re.match(text):
                                if heading_connector_re.search(text) and idx + 1 < len(records):
                                    next_rec = records[idx + 1]
                                    next_text = (next_rec.get("text") or "").strip()
                                    if next_text and not heading_start_re.match(next_text) and not introduction_pattern.match(next_text):
                                        first_word_match = _re.match(r"^(?P<word>[\wÀ-ÿ’'-]+)(?P<rest>\s+.+)?$", next_text)
                                        if first_word_match:
                                            first_word = first_word_match.group('word').strip()
                                            rest_text = (first_word_match.group('rest') or '').strip()
                                            joined = _re.sub(r'\s+', ' ', f"{text} {first_word}").strip()
                                            normalized.append({**rec, "text": joined})
                                            if rest_text:
                                                normalized.append({**next_rec, "text": rest_text})
                                            idx += 2
                                            continue
                                parts = [text]
                                look = idx + 1
                                while look < len(records) and len(parts) < 5:
                                    next_text = (records[look].get("text") or "").strip()
                                    next_upper = next_text.upper()
                                    words = _re.findall(r"\b[\wÀ-ÿ-]+\b", next_text)
                                    short_heading_tail = (
                                        next_text
                                        and len(next_text) <= 48
                                        and len(words) <= 6
                                        and next_upper == next_text
                                        and not heading_start_re.match(next_text)
                                        and not introduction_pattern.match(next_text)
                                    )
                                    if not short_heading_tail:
                                        break
                                    parts.append(next_text)
                                    look += 1
                                    if not incomplete_heading_re.match(parts[-2]):
                                        # Continue only for very short all-caps tails such as
                                        # translated Old/New Testament fragments.
                                        if len(parts) >= 3:
                                            break
                                if len(parts) > 1:
                                    joined = " ".join(parts)
                                    joined = _re.sub(r'\s+', ' ', joined).strip()
                                    joined = _re.sub(r':\s*(?:ENDALA\s+I[TT]H?ESTAMENT[EI]|I[TT]H?ESTAMENT[EI]\s+ENDALA)\b', ': ITESTAMENTE ENDALA', joined, flags=_re.IGNORECASE)
                                    joined = _re.sub(r':\s*(?:ELISHA\s+I[TT]H?ESTAMENT[EI]|I[TT]H?ESTAMENT[EI]\s+ELISHA)\b', ': ITESTAMENTE ELISHA', joined, flags=_re.IGNORECASE)
                                    rec = {**rec, "text": joined}
                                    idx = look
                                else:
                                    idx += 1
                                normalized.append(rec)
                                continue
                            idx += 1
                            normalized.append(rec)
                        return normalized

                    def _split_inline_intro_heading_records(records):
                        split_records = []
                        heading_re = r'(?:INTRODUCTION|NHANGANYAYA|ISINGENISO|ISANDULELO|INTRODUCCI[ÓO]N|UTANGULIZI|INTRODUÇÃO|EINFÜHRUNG|PREFACE|DIBAJI)'
                        for rec in records:
                            text = (rec.get("text") or "").strip()
                            if not text:
                                split_records.append(rec)
                                continue
                            start_match = _re.match(rf'^(?P<head>{heading_re})\s+(?P<body>.{{40,}})$', text, _re.IGNORECASE)
                            if start_match:
                                split_records.append({**rec, "text": start_match.group('head').strip()})
                                split_records.append({**rec, "text": start_match.group('body').strip()})
                                continue
                            inline_match = _re.search(
                                rf'(?P<prefix>.*?[.!?]|.*?\([^)]{{1,80}}\)|.*?\b(?:Dr|Dkt|Rev|Mchungaji|Prof)\.?\s+[A-ZÀ-Þ][\wÀ-ÿ.-]+(?:\s+[A-ZÀ-Þ][\wÀ-ÿ.-]+)?)\s+(?P<head>{heading_re})\s+(?P<body>.{{40,}})$',
                                text,
                                _re.IGNORECASE,
                            )
                            if inline_match:
                                prefix = inline_match.group('prefix').strip()
                                head = inline_match.group('head').strip()
                                body = inline_match.group('body').strip()
                                if prefix:
                                    split_records.append({**rec, "text": prefix})
                                split_records.append({**rec, "text": head})
                                split_records.append({**rec, "text": body})
                                continue
                            split_records.append(rec)
                        return split_records

                    def _split_inline_allcaps_subheading_records(records):
                        split_records = []

                        def _valid_inline_allcaps_heading(value):
                            heading = _re.sub(r'\s+', ' ', (value or '')).strip()
                            heading_words = _re.findall(r'\b[\wÀ-ÿ-]+\b', heading)
                            return (
                                heading
                                and heading == heading.upper()
                                and 1 <= len(heading_words) <= 8
                                and not _starts_new_body_block(heading)
                                and not heading.startswith("SICELA")
                            )

                        for rec in records:
                            text = (rec.get("text") or "").strip()
                            colon_heading_matches = list(_re.finditer(r'(?<!\w)([A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{2,80}:)\s+', text))
                            if colon_heading_matches:
                                cursor = 0
                                emitted = False
                                for idx, heading_match in enumerate(colon_heading_matches):
                                    heading = _re.sub(r'\s+', ' ', heading_match.group(1)).strip()
                                    if not _valid_inline_allcaps_heading(heading):
                                        continue
                                    next_start = colon_heading_matches[idx + 1].start() if idx + 1 < len(colon_heading_matches) else len(text)
                                    prefix = text[cursor:heading_match.start()].strip()
                                    body = text[heading_match.end():next_start].strip()
                                    if prefix:
                                        split_records.append({**rec, "text": prefix})
                                    split_records.append({**rec, "text": heading})
                                    if body:
                                        split_records.append({**rec, "text": body})
                                    cursor = next_start
                                    emitted = True
                                if emitted:
                                    tail = text[cursor:].strip()
                                    if tail:
                                        split_records.append({**rec, "text": tail})
                                    continue
                            match = _re.match(r'^([A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{5,80})\s+(\S.{30,})$', text)
                            if match:
                                heading = _re.sub(r'\s+', ' ', match.group(1)).strip()
                                body = match.group(2).strip()
                                if _valid_inline_allcaps_heading(heading):
                                    split_records.append({**rec, "text": heading})
                                    split_records.append({**rec, "text": body})
                                    continue
                            no_colon_inline_match = _re.search(
                                r'(?P<prefix>.*[.!?)])\s+(?P<head>[A-ZÀ-Þ][A-ZÀ-Þ0-9]+(?:\s+[A-ZÀ-Þ][A-ZÀ-Þ0-9]+){1,7})\s+(?P<body>[A-ZÀ-Þ][a-zà-ÿ].{30,})$',
                                text,
                            )
                            if no_colon_inline_match:
                                prefix = no_colon_inline_match.group('prefix').strip()
                                heading = _re.sub(r'\s+', ' ', no_colon_inline_match.group('head')).strip()
                                body = no_colon_inline_match.group('body').strip()
                                if _valid_inline_allcaps_heading(heading):
                                    if prefix:
                                        split_records.append({**rec, "text": prefix})
                                    split_records.append({**rec, "text": heading})
                                    split_records.append({**rec, "text": body})
                                    continue
                            inline_match = _re.search(
                                r'(?P<prefix>.*[.!?)])\s+(?P<head>[A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{2,50})\s+(?P<body>\S.{30,})$',
                                text,
                            )
                            if inline_match:
                                prefix = inline_match.group('prefix').strip()
                                heading = _re.sub(r'\s+', ' ', inline_match.group('head')).strip()
                                body = inline_match.group('body').strip()
                                if _valid_inline_allcaps_heading(heading):
                                    if prefix:
                                        split_records.append({**rec, "text": prefix})
                                    split_records.append({**rec, "text": heading})
                                    split_records.append({**rec, "text": body})
                                    continue
                            tail_heading_match = _re.search(
                                r'(?P<prefix>.*[.!?])\s+(?P<head>[A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{2,50})$',
                                text,
                            )
                            if tail_heading_match:
                                prefix = tail_heading_match.group('prefix').strip()
                                heading = _re.sub(r'\s+', ' ', tail_heading_match.group('head')).strip()
                                if _valid_inline_allcaps_heading(heading):
                                    if prefix:
                                        split_records.append({**rec, "text": prefix})
                                    split_records.append({**rec, "text": heading})
                                    continue
                            split_records.append(rec)
                        return split_records

                    def _known_three_column_table_rows():
                        return [
                            ['INKUNDLA YANGAPHANDLE', 'INDAWO ENGCWELE', 'INDAWO ENGCWELE KAKHULU'],
                            ['Isambulo seNdodana', 'Isambulo sikaMoya', 'Isambulo sikaYise'],
                            ['Indlela', 'Iqiniso', 'Indlela'],
                            ['Umzimba', 'Ingqondo', 'Umoya'],
                            ['Impilo ebuswa yinyama', 'Impilo ebuswa ngumphefumulo', 'Impilo ebuswa ngumoya'],
                            ['Ukubuza', 'Ukuzwa', 'Ukulalela/ukuvuma'],
                            ['Ubisi', 'Isinkwa', 'Inyama'],
                            ['Izolo', 'Namuhla', 'Okuphakade'],
                            ['Ukugcotshwa Kwabakholwayo', 'Ukugcotshwa Kwabapristi', 'Ukugcotshwa Kobukhosi'],
                            ['Intando Evumayo', 'Intando Eyamukelekayo', 'Intando Ephelele'],
                            ['Amashumi amathathu', 'Amashumi ayisithupha', 'Ikhulu'],
                            ['Okuhle', 'Kangcono', 'Okuhle Kakhulu'],
                        ]

                    def _known_counselor_levels_table_rows():
                        return [
                            ['Izinga Lokusebenza', 'Uhlobo Lomeluleki', 'Umsebenzi'],
                            ['1. Umuntu ngamunye', 'Umeluleki WobuKristu Womuntu Ngamunye', 'Ukuphelela komoya, umphefumulo nomzimba'],
                            ['2. Umndeni', 'Abelaphi/Abeluleki Bomndeni', 'Ukubuyiselwa komndeni'],
                            ['3. Ibandla', 'Umeluleki Womfundisi', 'Ubunye eBandleni'],
                            ['4. Umphakathi', 'Umeluleki Womphakathi/Weziprofetho', 'Ukuthuthukiswa kwesiko likaHosana emiphakathini'],
                            ['5. Izizwe', 'Umeluleki Wabaphostoli', 'Ukwelashwa kwezizwe nokulungiselela uMlobokazi kaKristu'],
                        ]

                    def _split_known_counselor_levels_table_record(rec):
                        original = (rec.get("text") or "").strip()
                        value = _re.sub(r'\s+', ' ', original)
                        header = 'Izinga Lokusebenza Uhlobo Lomsebenzi Womeluleki'
                        start = value.find(header)
                        if start < 0:
                            return None
                        end_markers = [
                            ' Njengoba le khosi ',
                            ' Njengoba lesi sifundo ',
                            ' As this course ',
                        ]
                        end_positions = [value.find(marker, start + len(header)) for marker in end_markers]
                        end_positions = [pos for pos in end_positions if pos >= 0]
                        end = min(end_positions) if end_positions else len(value)
                        before = value[:start].strip()
                        after = value[end:].strip()
                        parts = []
                        if before:
                            parts.append({**rec, "text": before})
                        parts.append({**rec, "text": "", "table_rows": _known_counselor_levels_table_rows()})
                        if after:
                            parts.append({**rec, "text": after})
                        return parts

                    def _split_known_three_column_table_record(rec):
                        original = (rec.get("text") or "").strip()
                        value = _re.sub(r'\s+', ' ', original)
                        header = 'INKUNDLA YANGAPHANDLE INDAWO ENGCWELE INDAWO ENGCWELE KAKHULU'
                        start = value.find(header)
                        if start < 0:
                            return None
                        end_markers = [' ISIPHETHO ', ' ISIPHELO ', ' CONCLUSION ']
                        end_positions = [value.find(marker, start + len(header)) for marker in end_markers]
                        end_positions = [pos for pos in end_positions if pos >= 0]
                        end = min(end_positions) if end_positions else len(value)
                        parts = []
                        before = value[:start].strip()
                        after = value[end:].strip()
                        if before:
                            parts.append({**rec, "text": before})
                        parts.append({**rec, "text": "", "table_rows": _known_three_column_table_rows()})
                        if after:
                            parts.append({**rec, "text": after})
                        return parts

                    def _recover_known_three_column_table(text):
                        value = _re.sub(r'\s+', ' ', (text or '').strip())
                        header = 'INKUNDLA YANGAPHANDLE INDAWO ENGCWELE INDAWO ENGCWELE KAKHULU '
                        if not value.startswith(header):
                            return None
                        return _known_three_column_table_rows()

                    def _mark_table_records(records):
                        marked = []
                        pending_table = []
                        skipping_known_table_tail = False
                        skipping_counselor_table_tail = False

                        def _flush_table():
                            nonlocal pending_table
                            if pending_table:
                                marked.append({"text": "", "source": pending_table[0].get("source"), "table_rows": [row["cells"] for row in pending_table]})
                                pending_table = []

                        def _tail_end_index(value):
                            upper = f" {value.upper()} "
                            indexes = []
                            for marker in (' ISIPHETHO ', ' ISIPHELO ', ' CONCLUSION '):
                                pos = upper.find(marker)
                                if pos >= 0:
                                    indexes.append(max(0, pos - 1))
                            return min(indexes) if indexes else -1

                        def _counselor_tail_end_index(value):
                            upper = f" {value.upper()} "
                            indexes = []
                            for marker in (' NJENGOBA LE KHOSI ', ' NJENGOBA LESI SIFUNDO ', ' AS THIS COURSE '):
                                pos = upper.find(marker)
                                if pos >= 0:
                                    indexes.append(max(0, pos - 1))
                            return min(indexes) if indexes else -1

                        for rec in records:
                            text = (rec.get("text") or "").strip()
                            if skipping_known_table_tail:
                                end_idx = _tail_end_index(text)
                                if end_idx >= 0:
                                    skipping_known_table_tail = False
                                    remainder = text[end_idx:].strip()
                                    if remainder:
                                        marked.append({**rec, "text": remainder})
                                continue
                            if skipping_counselor_table_tail:
                                end_idx = _counselor_tail_end_index(text)
                                if end_idx >= 0:
                                    skipping_counselor_table_tail = False
                                    remainder = text[end_idx:].strip()
                                    if remainder:
                                        marked.append({**rec, "text": remainder})
                                continue
                            split_table = _split_known_three_column_table_record(rec)
                            if split_table:
                                _flush_table()
                                marked.extend(split_table)
                                has_after_heading = any(_tail_end_index(part.get("text", "")) == 0 for part in split_table if part.get("text"))
                                if not has_after_heading:
                                    skipping_known_table_tail = True
                                continue
                            split_counselor_table = _split_known_counselor_levels_table_record(rec)
                            if split_counselor_table:
                                _flush_table()
                                marked.extend(split_counselor_table)
                                has_after_body = any(_counselor_tail_end_index(part.get("text", "")) == 0 for part in split_counselor_table if part.get("text"))
                                if not has_after_body:
                                    skipping_counselor_table_tail = True
                                continue
                            recovered = _recover_known_three_column_table(text)
                            if recovered:
                                _flush_table()
                                marked.append({**rec, "text": "", "table_rows": recovered})
                                skipping_known_table_tail = True
                                continue
                            source = rec.get("source") or {}
                            if source.get("table_like") and _re.search(r'\S+\s{4,}\S+', text):
                                cells = [c.strip() for c in _re.split(r'\s{4,}', text) if c.strip()]
                                if len(cells) >= 2:
                                    pending_table.append({"cells": cells, "source": source})
                                    continue
                            _flush_table()
                            marked.append(rec)
                        _flush_table()
                        return marked

                    def _split_inline_lettered_dot_records(records):
                        split_records = []
                        marker_re = _re.compile(r'(?<!\w)([a-z])\.\s+', _re.IGNORECASE)

                        def _split_marker_segment(segment):
                            match = _re.match(r'^([a-z])\.\s+(.+)$', segment.strip(), _re.IGNORECASE)
                            if not match:
                                return [("body", segment.strip())]
                            letter = match.group(1)
                            rest = match.group(2).strip()
                            words = _re.findall(r'\b[\wÀ-ÿ-]+\b', rest)
                            heading_len = 1
                            for candidate_len in range(min(5, len(words) // 2), 0, -1):
                                first = " ".join(words[:candidate_len]).lower()
                                second = " ".join(words[candidate_len:candidate_len * 2]).lower()
                                if first and first == second:
                                    heading_len = candidate_len
                                    break
                            heading_words = words[:heading_len]
                            heading = f"{letter}. {' '.join(heading_words)}".strip()
                            body = rest[len(" ".join(heading_words)):].strip()
                            return [("heading", heading), ("body", body)] if body else [("heading", heading)]

                        for rec in records:
                            text = (rec.get("text") or "").strip()
                            if not text or not _re.search(r'(?<!\w)[a-z]\.\s+', text):
                                split_records.append(rec)
                                continue
                            pieces = []
                            last = 0
                            for marker in marker_re.finditer(text):
                                if marker.start() > last:
                                    pieces.append(("body", text[last:marker.start()].strip()))
                                last = marker.start()
                            if last < len(text):
                                pieces.append(("marker", text[last:].strip()))
                            emitted = False
                            for kind, piece in pieces:
                                if not piece:
                                    continue
                                if kind == "marker":
                                    for sub_kind, sub_text in _split_marker_segment(piece):
                                        if not sub_text:
                                            continue
                                        split_records.append({**rec, "text": sub_text, "force_subheading": sub_kind == "heading"})
                                        emitted = True
                                else:
                                    split_records.append({**rec, "text": piece})
                                    emitted = True
                            if not emitted:
                                split_records.append(rec)
                        return split_records

                    chapter_marker_re = _re.compile(
                        r'(?=\b(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D)',
                        _re.IGNORECASE,
                    )
                    chapter_start_re = _re.compile(
                        r'^(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+.+$',
                        _re.IGNORECASE,
                    )

                    def _split_inline_chapter_heading_records(records):
                        split_records = []
                        split_markers = (
                            ' MSTARI MUHIMU:', ' MSTARI MUHIMU ', ' KEY VERSE:', ' KEY VERSE ',
                            ' SLEUTELVERS:', ' SLEUTELVERS ', ' IVESI ELIYINHLOKO:', ' IVESI ELIYINHLOKO ',
                            ' Umbono ', ' Inhloso ', ' Indima ', ' Ukubaluleka ', ' Ngokusho ',
                            ' Kodwa-ke, ', ' Manje ', ' Kuleli ', ' Le ', ' Lolu ', ' Njengoba ',
                            ' The ', ' Purpose ', ' According ', ' Role ', ' Practical ',
                        )

                        def _emit_chapter_text(rec, text):
                            if not chapter_start_re.match(text) or _is_bible_reference_chapter_line(text):
                                split_records.append({**rec, "text": text})
                                return
                            split_at = -1
                            for marker in split_markers:
                                pos = text.find(marker, 18)
                                if pos > 0:
                                    split_at = pos
                                    break
                            if split_at <= 0:
                                split_records.append({**rec, "text": text, "force_chapter": True})
                                return
                            heading = text[:split_at].strip()
                            tail = text[split_at:].strip()
                            split_records.append({**rec, "text": heading, "force_chapter": True})
                            if tail:
                                split_records.append({**rec, "text": tail, "force_subheading": len(tail) <= 100 and not _re.search(r'[.!?]$', tail)})

                        for rec in records:
                            text = (rec.get("text") or "").strip()
                            if not text:
                                split_records.append(rec)
                                continue
                            starts = [m.start() for m in chapter_marker_re.finditer(text)]
                            if not starts:
                                split_records.append(rec)
                                continue
                            if starts[0] > 0:
                                prefix = text[:starts[0]].strip()
                                if prefix:
                                    split_records.append({**rec, "text": prefix})
                            for idx, marker_start in enumerate(starts):
                                marker_end = starts[idx + 1] if idx + 1 < len(starts) else len(text)
                                chapter_text = text[marker_start:marker_end].strip()
                                if chapter_text:
                                    _emit_chapter_text(rec, chapter_text)
                        return split_records

                    def _looks_like_allcaps_subheading_text(value):
                        text_value = _re.sub(r'\s+', ' ', (value or '')).strip()
                        words = _re.findall(r'\b[\wÀ-ÿ-]+\b', text_value)
                        return (
                            bool(text_value)
                            and text_value == text_value.upper()
                            and 1 <= len(words) <= 10
                            and not _starts_new_body_block(text_value)
                            and not text_value.startswith("SICELA")
                        )

                    def _split_inline_sentence_case_subheading_records(records):
                        split_records = []
                        heading_token = r'(?:[0-9]+|[A-ZÀ-Þ][A-ZÀ-Þ0-9]+)'
                        inline_heading_re = _re.compile(
                            r'(?P<prefix>.*?[.!?)])\s+'
                            rf'(?P<head>{heading_token}(?:\s+{heading_token}){{0,9}})\s+'
                            r'(?P<body>[A-ZÀ-Þ][a-zà-ÿ].{20,})$'
                        )
                        tail_heading_re = _re.compile(
                            r'(?P<prefix>.*?[.!?)])\s+'
                            rf'(?P<head>{heading_token}(?:\s+{heading_token}){{0,9}})$'
                        )
                        for rec in records:
                            rec_text = (rec.get("text") or "").strip()
                            match = inline_heading_re.search(rec_text)
                            if match and _looks_like_allcaps_subheading_text(match.group('head')):
                                prefix = match.group('prefix').strip()
                                heading = _re.sub(r'\s+', ' ', match.group('head')).strip()
                                body = match.group('body').strip()
                                if prefix:
                                    split_records.append({**rec, "text": prefix})
                                split_records.append({**rec, "text": heading})
                                split_records.append({**rec, "text": body})
                                continue
                            match = tail_heading_re.search(rec_text)
                            if match and _looks_like_allcaps_subheading_text(match.group('head')):
                                prefix = match.group('prefix').strip()
                                heading = _re.sub(r'\s+', ' ', match.group('head')).strip()
                                if prefix:
                                    split_records.append({**rec, "text": prefix})
                                split_records.append({**rec, "text": heading})
                                continue
                            split_records.append(rec)
                        return split_records

                    def _merge_final_fragmented_heading_records(records):
                        def _is_short_heading_tail(value):
                            tail = (value or "").strip()
                            words = _re.findall(r"\b[\wÀ-ÿ-]+\b", tail)
                            return (
                                bool(tail)
                                and len(tail) <= 140
                                and len(words) <= 18
                                and not _is_toc_like_line(tail)
                                and not _starts_new_body_block(tail)
                            )

                        def _is_allcaps_heading_piece(value):
                            piece = (value or "").strip()
                            words = _re.findall(r"\b[\wÀ-ÿ-]+\b", piece)
                            return (
                                bool(piece)
                                and len(piece) <= 80
                                and 1 <= len(words) <= 10
                                and piece == piece.upper()
                                and not _is_toc_like_line(piece)
                            )

                        merged = []
                        idx = 0
                        incomplete_heading_re = _re.compile(
                            r'^(?:'
                            r'(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–:]{1,40})'
                            r'|'
                            r'(?:SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+'
                            r')\s*[:\-–]\s*$',
                            _re.IGNORECASE,
                        )
                        number_only_re = _re.compile(r'^\d+\.?$')
                        while idx < len(records):
                            rec = records[idx]
                            rec_text = (rec.get("text") or "").strip()

                            numbered_inline_body = _re.match(r'^(?P<num>(?:\d+|[lI]))\.\s+(?P<head_text>[^:]{2,90}:)\s+(?P<body>\S.+)$', rec_text)
                            if numbered_inline_body:
                                raw_num = numbered_inline_body.group("num")
                                normalized_num = "1" if raw_num in {"l", "I"} else raw_num
                                heading_text = f"{normalized_num}. {numbered_inline_body.group('head_text').strip()}"
                                merged.append({**rec, "text": heading_text, "force_subheading": True})
                                merged.append({**rec, "text": numbered_inline_body.group("body").strip(), "force_subheading": False})
                                idx += 1
                                continue

                            numbered_prefix = _re.match(r'^(?P<num>(?:\d+|[lI])\.)\s+(?P<head>[^:.;!?]{2,60})$', rec_text)
                            if numbered_prefix and idx + 1 < len(records):
                                next_rec = records[idx + 1]
                                next_text = (next_rec.get("text") or "").strip()
                                next_colon = next_text.find(':')
                                if (
                                    next_text
                                    and (
                                        (0 < next_colon <= 90 and next_text[:1].islower())
                                        or next_text.startswith(':')
                                    )
                                    and not _starts_new_body_block(next_text)
                                    and not _is_toc_like_line(next_text)
                                ):
                                    if next_text.startswith(':'):
                                        heading_tail = ':'
                                        body_tail = next_text[1:].strip()
                                    else:
                                        heading_tail = next_text[:next_colon + 1].strip()
                                        body_tail = next_text[next_colon + 1:].strip()
                                    raw_num = numbered_prefix.group("num")
                                    normalized_num = "1." if raw_num in {"l.", "I."} else raw_num
                                    heading_join = f"{numbered_prefix.group('head').strip()}{heading_tail}" if heading_tail == ':' else f"{numbered_prefix.group('head').strip()} {heading_tail}"
                                    heading = _re.sub(r'\s+', ' ', f"{normalized_num} {heading_join}").strip()
                                    merged.append({**rec, "text": heading, "force_subheading": True})
                                    if body_tail:
                                        merged.append({**next_rec, "text": body_tail, "force_subheading": False})
                                    idx += 2
                                    continue

                            key_verse_inline = _re.match(
                                r'^(?P<head>(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[-–:]\s+.+?)\s+(?P<tail>(?:MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?.*)$',
                                rec_text,
                                _re.IGNORECASE,
                            )
                            if key_verse_inline and not _is_bible_reference_chapter_line(rec_text):
                                merged.append({**rec, "text": key_verse_inline.group("head").strip(), "force_chapter": True})
                                merged.append({**rec, "text": key_verse_inline.group("tail").strip(), "force_subheading": True})
                                idx += 1
                                continue

                            is_number_fragment = bool(number_only_re.match(rec_text))
                            if incomplete_heading_re.match(rec_text) or is_number_fragment:
                                look = idx + 1
                                parts = [rec_text.rstrip('.') + "." if is_number_fragment else rec_text]
                                while look < len(records) and len(parts) < 5:
                                    next_text = (records[look].get("text") or "").strip()
                                    if not next_text:
                                        look += 1
                                        continue
                                    if not _is_short_heading_tail(next_text):
                                        break
                                    if not is_number_fragment and not _is_allcaps_heading_piece(next_text):
                                        break
                                    parts.append(next_text)
                                    look += 1
                                    if next_text.endswith(":"):
                                        break
                                if len(parts) > 1:
                                    joined = _re.sub(r'\s+', ' ', " ".join(parts)).strip()
                                    joined = _re.sub(r':\s*(?:YA\s+KALE\s+AGANO|AGANO\s+LA\s+KALE|ENDALA\s+I[TT]H?ESTAMENT[EI]|I[TT]H?ESTAMENT[EI]\s+ENDALA)\b', ': AGANO LA KALE', joined, flags=_re.IGNORECASE)
                                    joined = _re.sub(r':\s*(?:AGANO\s+JIPYA|ELISHA\s+I[TT]H?ESTAMENT[EI]|I[TT]H?ESTAMENT[EI]\s+ELISHA)\b', ': AGANO JIPYA', joined, flags=_re.IGNORECASE)
                                    merged.append({
                                        **rec,
                                        "text": joined,
                                        "force_chapter": bool(_re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)', rec_text, _re.IGNORECASE)),
                                        "force_subheading": bool(number_only_re.match(rec_text)),
                                    })
                                    idx = look
                                    continue

                            if (
                                _is_allcaps_heading_piece(rec_text)
                                and not rec.get("force_chapter")
                                and not rec.get("force_subheading")
                                and not _re.match(r'^(?:MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?', rec_text, _re.IGNORECASE)
                            ):
                                look = idx + 1
                                parts = [rec_text]
                                while look < len(records) and len(parts) < 4:
                                    next_text = (records[look].get("text") or "").strip()
                                    if not next_text:
                                        look += 1
                                        continue
                                    next_rec = records[look]
                                    if (
                                        not _is_allcaps_heading_piece(next_text)
                                        or next_rec.get("force_chapter")
                                        or next_rec.get("force_subheading")
                                        or _re.match(r'^(?:MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?', next_text, _re.IGNORECASE)
                                    ):
                                        break
                                    parts.append(next_text)
                                    look += 1
                                    if next_text.endswith(":"):
                                        break
                                if len(parts) > 1:
                                    joined = _re.sub(r'\s+', ' ', " ".join(parts)).strip()
                                    merged.append({**rec, "text": joined, "force_subheading": True})
                                    idx = look
                                    continue

                            merged.append(rec)
                            idx += 1
                        return merged

                    def _split_oversized_body_paragraph_records(records):
                        marker_re = _re.compile(
                            r'(?=\b(?:'
                            r'Kwanza|Pili|Tatu|Nne|Tano|Sita|Saba|Kisha|Hatimaye|Kwa\s+mfano|Kama\s+vile|'
                            r'First|Second|Third|Fourth|Fifth|Finally|For\s+example|For\s+instance|As\s+with|'
                            r'Eerstens|Tweedens|Derdens|Vierdens|Laastens|Byvoorbeeld|'
                            r'Okokuqala|Okwesibili|Okwesithathu|Ekugcineni|Ngokwesibonelo|'
                            r'Chekutanga|Chechipiri|Chechitatu|Pakupedzisira|Semuenzaniso'
                            r')\s*:)',
                            _re.IGNORECASE,
                        )
                        sentence_re = _re.compile(r'(?<=[.!?])\s+(?=["“]?[A-ZÀ-Þ0-9])')

                        def _word_count(value):
                            return len(_re.findall(r'\S+', value or ''))

                        def _should_skip_split(rec, value):
                            if not value or _word_count(value) < 85:
                                return True
                            if rec.get("table_rows") or rec.get("force_chapter") or rec.get("force_subheading") or rec.get("page_break"):
                                return True
                            if _starts_new_body_block(value) or _is_toc_like_line(value) or _is_form_or_checklist_line(value):
                                return True
                            if value.startswith("• ") or _re.match(r'^\(?[ivxabc]+\)', value, _re.IGNORECASE):
                                return True
                            if len(value) <= 160 and (value.isupper() or _looks_like_allcaps_subheading_text(value)):
                                return True
                            return False

                        def _split_segment(segment):
                            segment = _re.sub(r'\s+', ' ', (segment or '').strip())
                            if not segment:
                                return []
                            sentences = [s.strip() for s in sentence_re.split(segment) if s.strip()]
                            if len(sentences) <= 1:
                                return [segment]
                            chunks = []
                            current = []
                            current_words = 0
                            for sentence in sentences:
                                sentence_words = _word_count(sentence)
                                starts_discourse = bool(marker_re.match(sentence))
                                if current and (starts_discourse or current_words + sentence_words > 70):
                                    chunks.append(' '.join(current).strip())
                                    current = []
                                    current_words = 0
                                current.append(sentence)
                                current_words += sentence_words
                            if current:
                                chunks.append(' '.join(current).strip())
                            return chunks

                        split_records = []
                        for rec in records:
                            value = (rec.get("text") or "").strip()
                            if _should_skip_split(rec, value):
                                split_records.append(rec)
                                continue
                            marker_parts = [part.strip() for part in marker_re.split(value) if part and part.strip()]
                            chunks = []
                            for part in marker_parts:
                                chunks.extend(_split_segment(part))
                            chunks = [chunk for chunk in chunks if chunk]
                            if len(chunks) <= 1:
                                split_records.append(rec)
                                continue
                            for chunk in chunks:
                                split_records.append({**rec, "text": chunk})
                        return split_records

                    def _normalize_split_scripture_reference_records(records):
                        normalized = []
                        idx = 0
                        book_fragment_re = _re.compile(r"^\((?P<book>[A-ZÀ-Þ][\wÀ-ÿ’'-]{2,}(?:\s+[A-ZÀ-Þ]?[\wÀ-ÿ’'-]{1,}){0,3})$")
                        verse_tail_re = _re.compile(r'^(?P<ref>\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?\))(?P<body>\s+.+)?$')
                        while idx < len(records):
                            rec = records[idx]
                            rec_text = (rec.get("text") or "").strip()
                            book_match = book_fragment_re.match(rec_text)
                            if book_match and idx + 1 < len(records):
                                next_rec = records[idx + 1]
                                next_text = (next_rec.get("text") or "").strip()
                                verse_match = verse_tail_re.match(next_text)
                                if verse_match:
                                    scripture_ref = f"({book_match.group('book').strip()} {verse_match.group('ref').strip()}"
                                    normalized.append({**rec, "text": scripture_ref})
                                    body_tail = (verse_match.group('body') or '').strip()
                                    if body_tail:
                                        normalized.append({**next_rec, "text": body_tail})
                                    idx += 2
                                    continue
                            normalized.append(rec)
                            idx += 1
                        return normalized

                    def _merge_lowercase_connector_continuations(records):
                        merged_records = []
                        connector_re = _re.compile(
                            r'\b(?:and|or|of|to|the|a|an|na|ya|wa|la|za|kwa|katika|ili|de|van|en|du|des|la|le|les|el|del)$',
                            _re.IGNORECASE,
                        )
                        for rec in records:
                            rec_text = (rec.get("text") or "").strip()
                            if not rec_text:
                                continue
                            prev = merged_records[-1] if merged_records else None
                            prev_text = (prev.get("text") or "").strip() if prev else ""
                            prev_is_heading = bool(
                                prev
                                and (
                                    _starts_new_body_block(prev_text)
                                    or _looks_like_allcaps_subheading_text(prev_text)
                                )
                            )
                            if (
                                prev
                                and (
                                    rec_text[:1].islower()
                                    or bool(_re.match(r'^[A-ZÀ-Þ][a-zà-ÿ]+\b', rec_text))
                                )
                                and connector_re.search(prev_text)
                                and not prev_is_heading
                                and not rec.get("table_rows")
                                and not rec.get("page_break")
                                and not _starts_new_body_block(rec_text)
                                and not _is_form_or_checklist_line(rec_text)
                            ):
                                prev["text"] = prev_text.rstrip() + " " + rec_text
                                continue
                            merged_records.append(rec)
                        return merged_records

                    translated_records = _split_oversized_body_paragraph_records(_normalize_split_scripture_reference_records(_merge_lowercase_connector_continuations(_merge_final_fragmented_heading_records(_split_inline_sentence_case_subheading_records(_mark_table_records(_split_inline_lettered_dot_records(_split_inline_chapter_heading_records(_split_inline_allcaps_subheading_records(_split_inline_intro_heading_records(_normalize_lettered_prompt_fragments(_normalize_fragmented_chapter_titles(translated_records))))))))))))

                    # Let ReportLab flow body text naturally. Hard source-page breaks
                    # orphan headings and split workbook prompts from their answers.

                    def _chapter_heading_number(value):
                        match = _re.match(
                            r'^(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*(\d+)\s*[:\-–]\s+\D',
                            (value or "").strip(),
                            _re.IGNORECASE,
                        )
                        return int(match.group(1)) if match else None

                    def _is_numbered_subhead_line(text, source_record):
                        content = _re.sub(r'^\d+\.\s*', '', (text or '')).strip()
                        if not content:
                            return False
                        source_bold = bool(source_record and source_record["bold"])
                        source_size = float(source_record["size"] if source_record else 11)
                        words = _re.findall(r'\b[\wÀ-ÿ-]+\b', content)
                        word_count = len(words)
                        ends_sentence = bool(_re.search(r'[.!?:"”]$', content))
                        contains_connector = bool(_re.search(r'\b(and|or|but|with|without|because|that|which|kuti|uye|kana|nekuti|pour|avec|sans|que|qui|kwete)\b', content, _re.IGNORECASE))
                        title_caseish = all(
                            w[:1].isupper() or w.isupper()
                            for w in words
                            if len(w) > 2
                        ) if words else False
                        if source_bold and source_size >= 12 and word_count <= 10 and not ends_sentence:
                            return True
                        if word_count <= 6 and not ends_sentence and not contains_connector:
                            return True
                        if word_count <= 8 and title_caseish and not contains_connector and not ends_sentence:
                            return True
                        return False

                    chapter_heading_lookup = {}
                    for line in raw_lines:
                        candidate = (line or "").strip()
                        if not candidate:
                            continue
                        m = _re.match(
                            r'^((?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+)(.+)$',
                            candidate,
                            _re.IGNORECASE,
                        )
                        if not m:
                            continue
                        suffix = _re.sub(r'\s+', ' ', m.group(2)).strip().upper()
                        chapter_heading_lookup[suffix] = candidate

                    def _is_body_start_heading(value):
                        candidate = (value or "").strip()
                        if not candidate:
                            return False
                        if _is_toc_like_line(candidate):
                            return False
                        if introduction_pattern.match(candidate) and "....." not in candidate:
                            return True
                        if _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*1\s*[:\-–]\s+\D', candidate, _re.IGNORECASE) and "....." not in candidate:
                            return True
                        return False

                    def _is_intro_title_line(value, source_record):
                        candidate = (value or "").strip()
                        if not candidate:
                            return False
                        if _starts_new_body_block(candidate):
                            return False
                        if len(candidate) > 70:
                            return False
                        if bool(_re.search(r'[.!?:"”]$', candidate)):
                            return False
                        source_bold = bool(source_record and source_record["bold"])
                        source_size = float(source_record["size"] if source_record else 11)
                        word_count = len(_re.findall(r'\b[\wÀ-ÿ-]+\b', candidate))
                        return source_bold or source_size >= 12 or word_count <= 5

                    def _is_tail_promo_start(value):
                        candidate = (value or "").strip()
                        upper = candidate.upper()
                        return any(
                            marker in upper
                            for marker in (
                                "WHETHER YOU ARE SEARCHING FOR A BIBLE COLLEGE",
                                "UNGAVE UCHITSVAGA BIBLE COLLEGE",
                                "SI VOUS CHERCHEZ UNE ÉCOLE BIBLIQUE",
                                "SI ESTÁ BUSCANDO UN COLEGIO BÍBLICO",
                                "TEAM IMPACT CHRISTIAN UNIVERSITY",
                                "YUNIVHESITI YECHIKWATA CHEMHEDZISIRO YECHIKRISTU",
                                "SPAN IMPAK CHRISTELIKE UNIVERSITEIT",
                                "TEAM IMPACT CHRISTLICHE UNIVERSITÄT",
                            )
                        )

                    _body_allows_colon_chapter_headings_runtime = False
                    try:
                        _original_toc_entries_for_body = []
                        for _page_idx in range(0, min(12, len(orig_doc))):
                            if 'TABLE OF CONTENTS' in _orig_page_text_upper(_page_idx):
                                _original_toc_entries_for_body = _derive_workbook_toc_entries(orig_doc[_page_idx].get_text('text', sort=True).splitlines())
                                break
                        _body_allows_colon_chapter_headings_runtime = any(
                            _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*:', _entry, _re.IGNORECASE)
                            for _entry in _original_toc_entries_for_body
                        )
                    except Exception:
                        _body_allows_colon_chapter_headings_runtime = False

                    body_sections = [[]]
                    seen_chapter_numbers = set()
                    seen_chapter_titles = set()
                    previous_body_heading = None
                    force_body_break_after_initial_heading = False
                    forced_intro_heading_pending = (intro_heading_after_toc or '').strip() or None
                    intro_heading_emitted = False
                    initial_body_heading_emitted = False
                    initial_body_heading_pending = (body_heading_after_toc or '').strip() or None
                    _rendered_source_image_pages = set()

                    def _source_page_image_flowables(source_page_number: int):
                        if not source_page_number or source_page_number < 1 or source_page_number > len(orig_doc):
                            return []
                        page = orig_doc[source_page_number - 1]
                        flowables = []
                        max_width = 6.0 * inch
                        max_height = 3.2 * inch
                        for block in page.get_text("dict").get("blocks", []):
                            if block.get("type") != 1 or not block.get("image"):
                                continue
                            bbox = block.get("bbox") or (0, 0, 0, 0)
                            width = max(float(bbox[2]) - float(bbox[0]), 1)
                            height = max(float(bbox[3]) - float(bbox[1]), 1)
                            if width < 40 or height < 40:
                                continue
                            img = RLImage(_io.BytesIO(block.get("image")))
                            scale = min(max_width / width, max_height / height, 1.0)
                            img.drawWidth = width * scale
                            img.drawHeight = height * scale
                            img.hAlign = "CENTER"
                            flowables.extend([Spacer(1, 0.08 * inch), img, Spacer(1, 0.08 * inch)])
                        return flowables

                    def _append_source_page_images(source_page_number: int):
                        if not source_page_number or source_page_number in _rendered_source_image_pages:
                            return
                        _rendered_source_image_pages.add(source_page_number)
                        for image_flowable in _source_page_image_flowables(source_page_number):
                            _append_flowable(image_flowable)

                    def _chapter_heading_key(value):
                        if not value:
                            return None
                        if not _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', value, _re.IGNORECASE):
                            return None
                        return _re.sub(r'\s+', " ", value).strip().upper()

                    def _append_flowable(flowable):
                        body_sections[-1].append(flowable)

                    def _split_body_text_for_render(text):
                        value = _re.sub(r'\n+', ' ', (text or '')).strip()
                        if len(_re.findall(r'\n', text or '')) > 1:
                            value = _re.sub(r'\n+', ' ', value)
                        words = _re.findall(r'\S+', value)
                        if len(words) < 85:
                            return [value]
                        marker_re = _re.compile(
                            r'(?=\b(?:Kwanza|Pili|Tatu|Nne|Tano|Sita|Saba|Kisha|Hatimaye|Kwa\s+mfano|'
                            r'First|Second|Third|Fourth|Fifth|Finally|For\s+example|'
                            r'Eerstens|Tweedens|Derdens|Laastens|Byvoorbeeld|'
                            r'Okokuqala|Okwesibili|Okwesithathu|Ekugcineni|Ngokwesibonelo|'
                            r'Chekutanga|Chechipiri|Chechitatu|Pakupedzisira|Semuenzaniso)\s*:)',
                            _re.IGNORECASE,
                        )
                        sentence_re = _re.compile(r'(?<=[.!?])\s+(?=["“]?[A-ZÀ-Þ0-9])')
                        raw_parts = [part.strip() for part in marker_re.split(value) if part and part.strip()]
                        chunks = []
                        for part in raw_parts:
                            sentences = [s.strip() for s in sentence_re.split(part) if s.strip()]
                            if len(sentences) <= 1:
                                chunks.append(part)
                                continue
                            current = []
                            current_words = 0
                            for sentence in sentences:
                                sentence_words = len(_re.findall(r'\S+', sentence))
                                if current and (marker_re.match(sentence) or current_words + sentence_words > 60):
                                    chunks.append(' '.join(current).strip())
                                    current = []
                                    current_words = 0
                                current.append(sentence)
                                current_words += sentence_words
                            if current:
                                chunks.append(' '.join(current).strip())
                        return [chunk for chunk in chunks if chunk] or [value]

                    def _protect_scripture_reference_breaks(text):
                        def _replace_ref(match):
                            book = _re.sub(r'\s+', '', match.group('book').strip())
                            return f"({book}{match.group('verse')})"
                        return _re.sub(
                            r"\((?P<book>(?:[1-3]\s*)?[A-ZÀ-Þ][\wÀ-ÿ’'-]+(?:\s+[A-ZÀ-Þ]?[\wÀ-ÿ’'-]+){0,3})\s+(?P<verse>\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?)\)",
                            _replace_ref,
                            text or '',
                        )

                    def _append_paragraph(text, style, *, keep_together=False):
                        is_body_para = getattr(style, 'name', '') == 'B' and not keep_together
                        parts = _split_body_text_for_render(text) if is_body_para else [text]
                        for part_idx, part in enumerate(parts):
                            part = _protect_scripture_reference_breaks(part)
                            para = Paragraph(part, style)
                            if part_idx > 0:
                                _append_flowable(Spacer(1, 0.06*inch))
                            if keep_together:
                                _append_flowable(KeepTogether([para]))
                            else:
                                _append_flowable(para)

                    def _append_heading_paragraph(text, style):
                        # Require enough remaining page space for a heading plus body text,
                        # otherwise headings can orphan at the bottom of a page.
                        _append_flowable(CondPageBreak(0.65*inch))
                        text = _protect_scripture_reference_breaks(text)
                        _append_flowable(KeepTogether([Paragraph(text, style), Spacer(1, 0.02*inch)]))

                    def _should_keep_paragraph_together(text):
                        value = (text or '').strip()
                        words = _re.findall(r'\S+', value)
                        if not words:
                            return False
                        # Only keep genuinely short prompts together. Keeping normal
                        # paragraphs together creates large blank gaps and pushes body
                        # text onto new pages.
                        if _is_form_or_checklist_line(value) or value.startswith('• '):
                            return len(words) <= 45
                        return False

                    def _chapter_title_prefixes_from_toc():
                        prefixes = []
                        seen = set()
                        for entry in toc_entries or []:
                            candidate = _clean_toc_entry_text(entry)
                            if not candidate:
                                continue
                            if not _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', candidate, _re.IGNORECASE):
                                continue
                            key = _re.sub(r'\s+', ' ', candidate).strip().upper()
                            if key in seen:
                                continue
                            seen.add(key)
                            prefixes.append(candidate)
                        prefixes.sort(key=len, reverse=True)
                        return prefixes

                    chapter_title_prefixes = _chapter_title_prefixes_from_toc()

                    def _split_known_chapter_heading_prefix(value):
                        candidate = (value or '').strip()
                        if not candidate:
                            return None
                        collapsed_candidate = _re.sub(r'\s+', ' ', candidate).strip()
                        for heading in chapter_title_prefixes:
                            collapsed_heading = _re.sub(r'\s+', ' ', heading).strip()
                            if collapsed_candidate.upper() == collapsed_heading.upper():
                                return None
                            if collapsed_candidate.upper().startswith(collapsed_heading.upper() + ' '):
                                tail = collapsed_candidate[len(collapsed_heading):].strip()
                                if tail:
                                    return collapsed_heading, tail
                        return None

                    if False and toc_entries:
                        toc_title_safe = _normalize_render_quotes((toc_title_text or 'Table of Contents')).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                        _append_flowable(Spacer(1, 0.25*inch))
                        _append_flowable(Paragraph(toc_title_safe, heading_style))
                        _append_flowable(Spacer(1, 0.18*inch))
                        for toc_entry in toc_entries:
                            safe_entry = _normalize_render_quotes(toc_entry).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                            _append_flowable(Paragraph(safe_entry, toc_line_style))
                    if forced_intro_heading_pending and not introduction_pattern.match(forced_intro_heading_pending):
                        forced_intro_heading_pending = None

                    pending_scripture_book = None
                    pending_scripture_source = None
                    render_book_fragment_re = _re.compile(r"^\((?P<book>[A-ZÀ-Þ][\wÀ-ÿ’'-]{2,}(?:\s+[A-ZÀ-Þ]?[\wÀ-ÿ’'-]{1,}){0,3})$")
                    render_verse_tail_re = _re.compile(r'^(?P<ref>\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?\))(?P<body>\s+.+)?$')

                    for record in translated_records:
                        if record.get("page_break"):
                            if pending_scripture_book:
                                _append_paragraph(_normalize_render_quotes(pending_scripture_book).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style)
                                pending_scripture_book = None
                                pending_scripture_source = None
                            if body_sections[-1]:
                                _append_flowable(PageBreak())
                            previous_body_heading = "section"
                            continue
                        p = record["text"].strip()
                        _book_fragment = render_book_fragment_re.match(p)
                        if _book_fragment and not record.get("table_rows"):
                            if pending_scripture_book:
                                _append_paragraph(_normalize_render_quotes(pending_scripture_book).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style)
                            pending_scripture_book = _book_fragment.group("book").strip()
                            pending_scripture_source = record.get("source")
                            continue
                        if pending_scripture_book:
                            _verse_tail = render_verse_tail_re.match(p)
                            if _verse_tail and not record.get("table_rows"):
                                scripture_ref = f"({pending_scripture_book}{_verse_tail.group('ref').strip()}"
                                _append_paragraph(_normalize_render_quotes(scripture_ref).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style)
                                body_tail = (_verse_tail.group('body') or '').strip()
                                pending_scripture_book = None
                                pending_scripture_source = None
                                if body_tail:
                                    p = body_tail
                                else:
                                    previous_body_heading = None
                                    continue
                            else:
                                _append_paragraph(_normalize_render_quotes(pending_scripture_book).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style)
                                pending_scripture_book = None
                                pending_scripture_source = None
                        source_record = record["source"]
                        _append_source_page_images((source_record or {}).get("page_number"))
                        force_chapter = bool(record.get("force_chapter"))
                        force_subheading = bool(record.get("force_subheading"))
                        pre_key_match = _re.search(r'\s+(MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?', p, _re.IGNORECASE)
                        if (
                            pre_key_match
                            and _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\b', p, _re.IGNORECASE)
                            and not _is_bible_reference_chapter_line(p)
                        ):
                            heading_text = p[:pre_key_match.start()].strip()
                            tail_text = p[pre_key_match.start():].strip()
                            if heading_text and tail_text:
                                if body_sections[-1] and previous_body_heading != "section":
                                    _append_flowable(PageBreak())
                                heading_safe = _normalize_render_quotes(heading_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                tail_safe = _normalize_render_quotes(tail_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                _append_flowable(Spacer(1, 0.15*inch))
                                _append_heading_paragraph(heading_safe, chapter_heading_style)
                                _append_flowable(Spacer(1, 0.12*inch))
                                _append_heading_paragraph(tail_safe, subhead_style)
                                previous_body_heading = None
                                continue
                        if record.get("table_rows"):
                            table_data = []
                            max_cols = max((len(row) for row in record["table_rows"]), default=0)
                            if max_cols > 6:
                                for row in record["table_rows"]:
                                    row_text = " ".join(str(cell).strip() for cell in row if str(cell).strip())
                                    if row_text:
                                        row_safe = _normalize_render_quotes(row_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                        _append_flowable(Paragraph(row_safe, body_style))
                                previous_body_heading = None
                                continue
                            for row_idx, row in enumerate(record["table_rows"]):
                                padded_row = list(row) + [""] * max(0, max_cols - len(row))
                                table_data.append([
                                    Paragraph(
                                        _normalize_render_quotes(str(cell)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                                        table_header_style if row_idx == 0 else table_cell_style,
                                    )
                                    for cell in padded_row
                                ])
                            col_widths = [2.25 * inch] * max_cols if max_cols == 3 else None
                            table = Table(table_data, colWidths=col_widths, repeatRows=1 if len(table_data) > 2 else 0, hAlign="LEFT")
                            table.setStyle(TableStyle([
                                ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                                ("FONTNAME", (0, 0), (-1, 0), reportlab_bold_name),
                                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                ("TOPPADDING", (0, 0), (-1, -1), 3),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ]))
                            _append_flowable(Spacer(1, 0.08*inch))
                            _append_flowable(table)
                            _append_flowable(Spacer(1, 0.08*inch))
                            previous_body_heading = None
                            continue
                        if force_chapter:
                            forced_key_match = _re.match(
                                r'^(?P<head>(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[-–:]\s+.+?)\s+(?P<tail>(?:MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?.*)$',
                                p,
                                _re.IGNORECASE,
                            )
                            if forced_key_match and not _is_bible_reference_chapter_line(p):
                                heading_text = forced_key_match.group("head").strip()
                                tail_text = forced_key_match.group("tail").strip()
                                if body_sections[-1] and previous_body_heading != "section":
                                    _append_flowable(PageBreak())
                                heading_safe = _normalize_render_quotes(heading_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                tail_safe = _normalize_render_quotes(tail_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                _append_flowable(Spacer(1, 0.15*inch))
                                _append_heading_paragraph(heading_safe, chapter_heading_style)
                                _append_flowable(Spacer(1, 0.06*inch))
                                _append_heading_paragraph(tail_safe, subhead_style)
                                previous_body_heading = None
                                continue
                            safe_forced = _normalize_render_quotes(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            if body_sections[-1] and previous_body_heading != "section":
                                _append_flowable(PageBreak())
                            _append_flowable(Spacer(1, 0.15*inch))
                            _append_heading_paragraph(safe_forced, chapter_heading_style)
                            _append_flowable(Spacer(1, 0.08*inch))
                            previous_body_heading = "chapter"
                            continue
                        if force_subheading:
                            safe_forced = _normalize_render_quotes(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_flowable(Spacer(1, 0.06*inch))
                            _append_heading_paragraph(safe_forced, subhead_style)
                            _append_flowable(Spacer(1, 0.04*inch))
                            previous_body_heading = None
                            continue
                        normalized_p = _re.sub(r'\s+', ' ', p).strip().upper()
                        if not initial_body_heading_emitted:
                            if initial_body_heading_pending and normalized_p == _re.sub(r'\s+', ' ', initial_body_heading_pending).strip().upper():
                                if body_sections[-1]:
                                    body_sections.append([])
                                safe_initial = _normalize_render_quotes(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                initial_style = heading_style if _re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]?', p, _re.IGNORECASE) else chapter_heading_style
                                _append_flowable(Spacer(1, 0.15*inch))
                                _append_heading_paragraph(safe_initial, initial_style)
                                _append_flowable(Spacer(1, 0.08*inch))
                                previous_body_heading = "section" if initial_style == heading_style else "chapter"
                                initial_body_heading_emitted = True
                                continue
                            if intro_title_text and normalized_p == _re.sub(r'\s+', ' ', intro_title_text).strip().upper():
                                if body_sections[-1]:
                                    body_sections.append([])
                                safe_initial = _normalize_render_quotes(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                _append_flowable(Spacer(1, 0.15*inch))
                                _append_heading_paragraph(safe_initial, intro_title_style)
                                _append_flowable(Spacer(1, 0.08*inch))
                                previous_body_heading = "intro"
                                intro_heading_emitted = True
                                initial_body_heading_emitted = True
                                continue
                        if intro_heading_emitted and forced_intro_heading_pending and p.upper() == forced_intro_heading_pending.upper():
                            forced_intro_heading_pending = None
                            continue
                        if initial_body_heading_emitted and initial_body_heading_pending and _re.sub(r'\s+', ' ', p).strip().upper() == _re.sub(r'\s+', ' ', initial_body_heading_pending).strip().upper():
                            continue
                        if _is_tail_promo_start(p):
                            break
                        if _skip_translated_footer_line(p):
                            continue
                        if source_record and _skip_body_record(source_record) and _skip_translated_footer_line(p):
                            continue
                        if not p:
                            _append_flowable(Spacer(1, 0.05*inch))
                            continue
                        simple_key_match = _re.search(r'\s+(MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?', p, _re.IGNORECASE)
                        if (
                            simple_key_match
                            and _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\b', p, _re.IGNORECASE)
                            and not _is_bible_reference_chapter_line(p)
                        ):
                            heading_text = p[:simple_key_match.start()].strip()
                            tail_text = p[simple_key_match.start():].strip()
                            if heading_text and tail_text:
                                if body_sections[-1] and previous_body_heading != "section":
                                    _append_flowable(PageBreak())
                                heading_safe = _normalize_render_quotes(heading_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                tail_safe = _normalize_render_quotes(tail_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                _append_flowable(Spacer(1, 0.15*inch))
                                _append_heading_paragraph(heading_safe, chapter_heading_style)
                                _append_flowable(Spacer(1, 0.12*inch))
                                _append_heading_paragraph(tail_safe, subhead_style)
                                previous_body_heading = None
                                continue
                        if p.startswith("• "):
                            bullet_rest = p[2:].strip()
                            inline_bullet_split = _re.match(r'^(["“].+?["”])\s+(.+)$', bullet_rest)
                            if inline_bullet_split:
                                bullet_only = "• " + inline_bullet_split.group(1).strip()
                                bullet_safe = _normalize_render_quotes(bullet_only).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                tail_safe = _normalize_render_quotes(inline_bullet_split.group(2).strip()).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                _append_paragraph(bullet_safe, indent_style, keep_together=True)
                                _append_paragraph(tail_safe, body_style, keep_together=_should_keep_paragraph_together(tail_text if 'tail_text' in locals() else tail_safe))
                                continue
                        normalized_upper = _re.sub(r'\s+', ' ', p).strip().upper()
                        promoted_heading = chapter_heading_lookup.get(normalized_upper)
                        if promoted_heading and not _is_bible_reference_chapter_line(p) and not _re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', p, _re.IGNORECASE):
                            promoted_num = _chapter_heading_number(promoted_heading)
                            if promoted_num and promoted_num not in seen_chapter_numbers:
                                p = promoted_heading
                        p = _normalize_render_quotes(p)
                        p = _strip_translated_footer_prefix(p)
                        if not p or p.strip() in {"•", "-", "–", "—"}:
                            continue
                        inline_ref_body, inline_references = _split_inline_url_references(p)
                        if inline_references:
                            if inline_ref_body:
                                p = inline_ref_body
                            else:
                                _append_reference_flowables(inline_references)
                                previous_body_heading = None
                                continue
                        key_verse_chapter_match = _re.match(
                            r'^(?P<head>(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[-–:]\s+.+?)\s+(?P<tail>(?:MSTARI\s+MUHIMU|KEY\s+VERSE|SLEUTELVERS|IVESI\s+ELIYINHLOKO)\s*:?.*)$',
                            p,
                            _re.IGNORECASE,
                        )
                        if key_verse_chapter_match and not _is_bible_reference_chapter_line(p):
                            heading_text = key_verse_chapter_match.group("head").strip()
                            tail_text = key_verse_chapter_match.group("tail").strip()
                            if body_sections[-1] and previous_body_heading != "section":
                                _append_flowable(PageBreak())
                            heading_safe = heading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            tail_safe = tail_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_flowable(Spacer(1, 0.15*inch))
                            _append_heading_paragraph(heading_safe, chapter_heading_style)
                            _append_flowable(Spacer(1, 0.06*inch))
                            _append_heading_paragraph(tail_safe, subhead_style)
                            previous_body_heading = None
                            continue

                        chapter_tail_match = _re.match(
                            r'^(?P<head>(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+.+?)\s+(?P<tail>Ngokusho\b.+)$',
                            p,
                            _re.IGNORECASE,
                        )
                        if chapter_tail_match:
                            heading_text = chapter_tail_match.group("head").strip()
                            tail_text = chapter_tail_match.group("tail").strip()
                            if body_sections[-1] and previous_body_heading != "section":
                                _append_flowable(PageBreak())
                            heading_safe = heading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            tail_safe = tail_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_flowable(Spacer(1, 0.15*inch))
                            _append_heading_paragraph(heading_safe, chapter_heading_style)
                            _append_flowable(Spacer(1, 0.08*inch))
                            _append_paragraph(tail_safe, body_style, keep_together=_should_keep_paragraph_together(tail_text if 'tail_text' in locals() else tail_safe))
                            if inline_references:
                                _append_reference_flowables(inline_references)
                            previous_body_heading = None
                            continue
                        if previous_body_heading == "chapter":
                            trailing_subheading_parts = _split_trailing_subheading(p, source_record)
                            if trailing_subheading_parts:
                                prefix_part, subheading_part = trailing_subheading_parts
                                if prefix_part:
                                    prefix_safe = prefix_part.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                    _append_heading_paragraph(prefix_safe, chapter_heading_style)
                                subheading_safe = subheading_part.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                _append_flowable(Spacer(1, 0.05*inch))
                                _append_heading_paragraph(subheading_safe, subhead_style)
                                previous_body_heading = None
                                continue
                        render_heading_token = r'(?:[0-9]+|[A-ZÀ-Þ][A-ZÀ-Þ0-9]+)'
                        render_inline_allcaps = _re.search(
                            r'(?P<prefix>.*?[.!?)])\s+'
                            rf'(?P<head>{render_heading_token}(?:\s+{render_heading_token}){{0,9}})\s+'
                            r'(?P<body>\S.{10,})$',
                            p,
                        )
                        if render_inline_allcaps and _looks_like_allcaps_subheading_text(render_inline_allcaps.group("head")):
                            prefix_text = render_inline_allcaps.group("prefix").strip()
                            heading_text = _re.sub(r'\s+', ' ', render_inline_allcaps.group("head")).strip()
                            tail_text = render_inline_allcaps.group("body").strip()
                            prefix_safe = prefix_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            heading_safe = heading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            tail_safe = tail_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_paragraph(prefix_safe, body_style, keep_together=False)
                            _append_flowable(Spacer(1, 0.05*inch))
                            _append_heading_paragraph(heading_safe, subhead_style)
                            _append_paragraph(tail_safe, body_style, keep_together=False)
                            previous_body_heading = None
                            continue
                        render_tail_allcaps = _re.search(
                            r'(?P<prefix>.*?[.!?)])\s+'
                            rf'(?P<head>{render_heading_token}(?:\s+{render_heading_token}){{0,9}})$',
                            p,
                        )
                        if render_tail_allcaps and _looks_like_allcaps_subheading_text(render_tail_allcaps.group("head")):
                            prefix_text = render_tail_allcaps.group("prefix").strip()
                            heading_text = _re.sub(r'\s+', ' ', render_tail_allcaps.group("head")).strip()
                            prefix_safe = prefix_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            heading_safe = heading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _append_paragraph(prefix_safe, body_style, keep_together=False)
                            _append_flowable(Spacer(1, 0.05*inch))
                            _append_heading_paragraph(heading_safe, subhead_style)
                            previous_body_heading = None
                            continue

                        known_heading_split = _split_known_chapter_heading_prefix(p)
                        if known_heading_split and not _is_bible_reference_chapter_line(p):
                            heading_text, tail_text = known_heading_split
                            heading_safe = heading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            tail_safe = tail_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            if body_sections[-1] and previous_body_heading != "section":
                                _append_flowable(PageBreak())
                            _append_flowable(Spacer(1, 0.15*inch))
                            _append_heading_paragraph(heading_safe, chapter_heading_style)
                            _append_flowable(Spacer(1, 0.08*inch))
                            tail_is_short_heading = (
                                len(tail_text) <= 90
                                and not _re.search(r'[.!?]$', tail_text)
                                and (_looks_like_isolated_translated_heading(tail_text, '', '', source_record) or tail_text.endswith(':'))
                            )
                            if tail_is_short_heading:
                                _append_heading_paragraph(tail_safe, subhead_style)
                            else:
                                _append_paragraph(tail_safe, body_style, keep_together=_should_keep_paragraph_together(tail_text))
                            previous_body_heading = None
                            continue

                        safe = p.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                        is_source_bold = bool(source_record and source_record["bold"])
                        source_size = float(source_record["size"] if source_record else 11)
                        # Pattern-based overrides (reliable regardless of source pairing)
                        is_section = bool(_re.match(r'^(SECTION|ISIGABA|SEKCJA|SEKSHENI|SIGABA|SEHEMU(?:\s+YA)?|AFDELING)\s+\d+\s*[:\-–]\s+\D', p, _re.IGNORECASE))
                        is_chapter = force_chapter or (bool(_re.match(r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D', p, _re.IGNORECASE)) and not _is_bible_reference_chapter_line(p))
                        is_allcaps = len(p) < 80 and p.isupper() and len(p) > 3
                        is_form_line = _is_form_or_checklist_line(p)
                        is_lettered = bool(_re.match(r'^[a-zA-Z]\) .{2,}', p) and len(p) < 120 and not is_form_line)
                        looks_like_sentence = (
                            len(p) > 70
                            or p.endswith((".", ",", ";", ":", "?", "!", "”"))
                            or len(_re.findall(r'\b[a-zà-ÿ]{3,}\b', p)) >= 8
                        )
                        safe_source_bold = (
                            is_source_bold
                            and source_size >= 12
                            and len(p) <= 90
                            and not looks_like_sentence
                        )
                        is_intro_heading = bool(introduction_pattern.match(p)) and "....." not in p
                        if is_section:
                            if body_sections[-1]:
                                _append_flowable(PageBreak())
                            _append_heading_paragraph(safe, heading_style)
                            _append_flowable(Spacer(1, 0.08*inch))
                            previous_body_heading = "section"
                        elif is_chapter or is_intro_heading:
                            chapter_num = _chapter_heading_number(p)
                            chapter_key = _chapter_heading_key(p)
                            if chapter_key and chapter_key in seen_chapter_titles:
                                continue
                            if chapter_num and chapter_num in seen_chapter_numbers:
                                continue
                            if is_chapter and body_sections[-1] and previous_body_heading != "section":
                                _append_flowable(PageBreak())
                            if chapter_num:
                                seen_chapter_numbers.add(chapter_num)
                            if chapter_key:
                                seen_chapter_titles.add(chapter_key)
                            _append_flowable(Spacer(1, 0.15*inch))
                            _append_heading_paragraph(safe, chapter_heading_style if is_chapter else intro_title_style)
                            _append_flowable(Spacer(1, 0.08*inch))
                            previous_body_heading = "chapter" if is_chapter else "intro"
                        elif previous_body_heading == "intro" and _is_intro_title_line(p, source_record):
                            _append_flowable(Spacer(1, 0.05*inch))
                            _append_heading_paragraph(safe, intro_title_style)
                            previous_body_heading = None
                        elif (
                            normalized_upper in chapter_heading_lookup
                            and chapter_heading_lookup[normalized_upper]
                            and _chapter_heading_number(chapter_heading_lookup[normalized_upper]) in seen_chapter_numbers
                        ):
                            # Keep summary/title echoes as subheads instead of re-promoting
                            # them into chapter headings after the real chapter title has
                            # already been emitted.
                            _append_flowable(Spacer(1, 0.05*inch))
                            _append_heading_paragraph(safe, subhead_style)
                            previous_body_heading = None
                        elif is_form_line:
                            _append_paragraph(safe, indent_style if p.startswith(("-", "–", "—")) else body_style, keep_together=True)
                            previous_body_heading = None
                        elif force_subheading or is_allcaps or is_lettered or safe_source_bold:
                            _append_flowable(Spacer(1, 0.05*inch))
                            _append_heading_paragraph(safe, subhead_style)
                            previous_body_heading = None
                        elif _re.match(r'^\d+\. ', p):
                            _append_paragraph(safe, subhead_style if _is_numbered_subhead_line(p, source_record) else body_style, keep_together=_should_keep_paragraph_together(p))
                            previous_body_heading = None
                        elif p.startswith("• "):
                            _append_paragraph(safe, indent_style, keep_together=True)
                            previous_body_heading = None
                        elif _re.match(r'^\([ivxabc]+\)', p):
                            _append_paragraph(safe, indent_style, keep_together=True)
                            previous_body_heading = None
                        else:
                            _append_paragraph(safe, body_style, keep_together=_should_keep_paragraph_together(p))
                            previous_body_heading = None
                        if inline_references:
                            _append_reference_flowables(inline_references)
                    front_bytes = b""
                    if workbook_front_story:
                        front_buf = _io.BytesIO()
                        _new_body_doc(front_buf).build(workbook_front_story)
                        front_bytes = front_buf.getvalue()

                    try:
                        body_sections = [section for section in body_sections if any(not isinstance(item, Spacer) for item in section)]
                        merged_body = _fitz.open()
                        for section in body_sections:
                            section_buf = _io.BytesIO()
                            _new_body_doc(section_buf).build(section)
                            section_pdf = _fitz.open("pdf", section_buf.getvalue())
                            merged_body.insert_pdf(section_pdf)
                        body_bytes = merged_body.tobytes(garbage=4, deflate=True)
                    except Exception as _e:
                        import logging as _log
                        _log.getLogger(__name__).warning(f"ReportLab build failed: {_e}")
                        body_bytes = b""

                    def _find_tail_promo_page_index():
                        markers = (
                            "WHETHER YOU ARE SEARCHING FOR A BIBLE COLLEGE",
                            "TEAM IMPACT CHRISTIAN UNIVERSITY",
                            "TIUNIVERSITY.COM",
                        )
                        for page_idx in range(last_page, max(-1, last_page - 4), -1):
                            page_text = orig_doc[page_idx].get_text("text", sort=True).upper()
                            if any(marker in page_text for marker in markers):
                                return page_idx
                        return None

                    def _stored_tail_promo_lines():
                        lines = [ln.strip() for ln in translation.translated_text.split("\n") if ln.strip()]
                        start = None
                        for idx in range(len(lines) - 1, -1, -1):
                            upper = lines[idx].upper()
                            if (
                                "BIBLE COLLEGE" in upper
                                or "KOLISHI LEBHAYIBHELI" in upper
                                or "KOLISHI LAMAKRISTU" in upper
                                or "THEOLOGICAL SEMINARY" in upper
                                or "SEMINARI YEZENKOLO" in upper
                            ):
                                start = idx
                                break
                        if start is None:
                            return []
                        return lines[start:start + 8]

                    def _render_tail_promo_page(page):
                        stored_lines = _stored_tail_promo_lines()
                        for block in page.get_text("dict").get("blocks", []):
                            if block.get("type") == 0:
                                page.add_redact_annot(_fitz.Rect(block["bbox"]), fill=(1, 1, 1))
                        page.apply_redactions()
                        if stored_lines:
                            title = " ".join(stored_lines[:2]).strip()
                            org = next((line for line in stored_lines if "Team Impact" in line or "TEAM IMPACT" in line or "I-Team Impact" in line), "Team Impact Christian University")
                            subtitle = next((line for line in stored_lines if line != title and line != org and "www." not in line and "@" not in line), "")
                            _insert_fitted_textbox(page, _fitz.Rect(26, 40, page.rect.x1 - 26, 95), title, bold=False, align=1, sizes=(14, 13, 12, 11, 10))
                            _insert_fitted_textbox(page, _fitz.Rect(40, 105, page.rect.x1 - 40, 175), subtitle, bold=False, align=1, sizes=(12, 11, 10, 9, 8))
                            _insert_fitted_textbox(page, _fitz.Rect(110, 185, page.rect.x1 - 110, 220), org, bold=False, align=1, sizes=(13, 12, 11, 10))
                        website_rect = _fitz.Rect(190, 540, page.rect.x1 - 190, 560)
                        email_rect = _fitz.Rect(185, 563, page.rect.x1 - 185, 585)
                        _insert_fitted_textbox(page, website_rect, "www.tiuniversity.com", bold=False, align=1, sizes=(11, 10, 9))
                        _insert_fitted_textbox(page, email_rect, "info@tiuniversity.com", bold=False, align=1, sizes=(11, 10, 9))
                        page.insert_link({"kind": _fitz.LINK_URI, "from": website_rect, "uri": "https://www.tiuniversity.com"})
                        page.insert_link({"kind": _fitz.LINK_URI, "from": email_rect, "uri": "mailto:info@tiuniversity.com"})

                    tail_promo_page_idx = _find_tail_promo_page_index()
                    if tail_promo_page_idx is not None:
                        _render_tail_promo_page(orig_doc[tail_promo_page_idx])

                    # --- Assemble: translated front matter + body + last 2 pages ---
                    mod_buf = _io.BytesIO()
                    orig_doc.save(mod_buf)
                    mod_doc = _fitz.open("pdf", mod_buf.getvalue())

                    out = _fitz.open()
                    import logging as _log
                    _log.getLogger(__name__).warning(f'assemble intro_heading={intro_title_text!r} workbook_like={workbook_like} toc_entries={len(toc_entries) if "toc_entries" in locals() else -1}')
                    if workbook_like:
                        if _cached_front_matter_available and front_bytes:
                            # Preserve uploaded cover exactly; do not translate/redact page 1.
                            out.insert_pdf(orig_doc, from_page=0, to_page=0)
                            # Some workbooks have a second, title-only page before the translatable manual page.
                            # Rebuild that page with the translated course title instead of preserving English.
                            if len(orig_doc) > 1:
                                _p1_text = [ln.strip() for ln in orig_doc[1].get_text("text", sort=True).splitlines() if ln.strip()]
                                _p1_joined = " ".join(_p1_text)
                                if _p1_text and len(_p1_text) <= 3 and len(_p1_joined) <= 120 and not _re.search(r"HOW TO USE|EXAMINATION|TABLE OF CONTENTS", _p1_joined, _re.IGNORECASE):
                                    _title_doc = _fitz.open()
                                    _title_page = _title_doc.new_page(width=orig_doc[1].rect.width, height=orig_doc[1].rect.height)
                                    _course_code_match = _re.search(r"\b(?:BH|BG|DC|CC)\d{3}\b", _p1_joined, _re.IGNORECASE)
                                    _course_code = _course_code_match.group(0).upper() if _course_code_match else ""
                                    _title_candidates = [(ln or '').strip() for ln in (title_page_lines or []) if (ln or '').strip()]
                                    _translated_title = ""
                                    if _course_code:
                                        _translated_title = next((ln for ln in _title_candidates if _course_code in ln.upper()), "")
                                        if not _translated_title:
                                            _translated_title = next((ln.strip() for ln in _stored_translated_lines[:40] if _course_code in (ln or '').upper()), "")
                                    if not _translated_title:
                                        _translated_title = next((ln for ln in _title_candidates if not _re.search(r"TEAM IMPACT|IYUNIVESITHI|YUNIVHESITI|UNIVERSITY", ln, _re.IGNORECASE)), "")
                                    if not _translated_title:
                                        _translated_title = next(iter(_title_candidates), "")
                                    if not _translated_title:
                                        _translated_title = _next_front_translated_line(_p1_joined)
                                    _log.getLogger(__name__).warning(f'title_page_selected code={_course_code!r} original={_p1_joined!r} translated={_translated_title!r} candidates={_title_candidates[:4]!r}')
                                    _insert_fitted_textbox(_title_page, _fitz.Rect(45, 45, _title_page.rect.x1 - 45, 180), _translated_title, bold=True, align=1, sizes=(18, 16, 14, 12))
                                    out.insert_pdf(_title_doc)
                            front_fitz = _fitz.open("pdf", front_bytes)
                            out.insert_pdf(front_fitz)
                        else:
                            for idx in range(0, front_matter_end_idx + 1):
                                out.insert_pdf(mod_doc, from_page=idx, to_page=idx)
                    else:
                        for idx in range(0, front_matter_end_idx + 1):
                            if _page_looks_like_toc(orig_doc[idx]):
                                continue
                            out.insert_pdf(mod_doc, from_page=idx, to_page=idx)
                    if body_bytes:
                        body_fitz = _fitz.open("pdf", body_bytes)
                        out.insert_pdf(body_fitz)
                    # Workbook translations are fully rebuilt from stored translated text.
                    # Append only the translated logo/promo page, not original English body pages.
                    if workbook_like and tail_promo_page_idx is not None:
                        promo_doc = _fitz.open()
                        promo_doc.insert_pdf(orig_doc, from_page=tail_promo_page_idx, to_page=tail_promo_page_idx)
                        out.insert_pdf(promo_doc)
                    elif not workbook_like and last_page >= body_start_page_idx:
                        out.insert_pdf(orig_doc, from_page=max(last_page - 1, body_start_page_idx), to_page=last_page)

                    def _stamp_dynamic_page_numbers(doc):
                        if len(doc) <= 1:
                            return
                        for idx in range(1, len(doc)):
                            page = doc[idx]
                            label = str(idx)
                            number_rect = _fitz.Rect(72, page.rect.y1 - 28, page.rect.x1 - 72, page.rect.y1 - 8)
                            page.insert_textbox(
                                number_rect,
                                label,
                                fontsize=10,
                                fontname=reportlab_regular_name,
                                fontfile=reportlab_regular_file,
                                color=(0, 0, 0),
                                align=1,
                                overlay=True,
                            )

                    _stamp_dynamic_page_numbers(out)

                    final_buf = _io.BytesIO()
                    out.save(final_buf)
                    content = final_buf.getvalue()
                    with open(cached_pdf_path, "wb") as f:
                        f.write(content)
                else:

                    from app.tasks.translation_tasks import _batch_translate
                    import re as _re

                    def _should_skip(text):
                        """Only skip short standalone emails/URLs/copyright lines."""
                        t = text.strip()
                        if len(t) > 200:
                            return False  # never skip large blocks
                        if _re.search(r'[\w.+-]+@[\w-]+\.\w+', t): return True  # email
                        if _re.search(r'https?://|www\.', t): return True  # URL
                        if t.startswith('©'): return True  # copyright line
                        return False

                    with open(f"/app/storage/{book.file_path}", "rb") as _f:
                        doc = _fitz.open("pdf", _f.read())

                    last_page = len(doc) - 1

                    for page_num, page in enumerate(doc):
                        if page_num == 0:
                            continue

                        # Last 2 pages: keep as-is (university ad + back cover)
                        if page_num >= last_page - 1:
                            continue

                        blocks = page.get_text("dict")["blocks"]
                        text_blocks = []
                        for b in blocks:
                            if b.get("type") != 0:
                                continue
                            all_spans = [s for l in b.get("lines", []) for s in l.get("spans", []) if s["text"].strip()]
                            if not all_spans:
                                continue
                            text = "".join(s["text"] for s in all_spans).strip()
                            # Use majority font: if most chars are non-bold, treat whole block as non-bold
                            bold_chars = sum(len(s["text"]) for s in all_spans if "Bold" in s.get("font", ""))
                            total_chars = sum(len(s["text"]) for s in all_spans)
                            is_bold = bold_chars > total_chars * 0.5
                            size = all_spans[0].get("size", 10)
                            text_blocks.append((b["bbox"], text, size, is_bold))

                        if not text_blocks:
                            continue

                        # Translate PDF blocks directly — skip trademarks/emails
                        texts = [t for _,t,_,_ in text_blocks]
                        to_translate = [(i, t) for i, t in enumerate(texts) if not _should_skip(t)]
                        translated = list(texts)  # start with originals
                        if to_translate:
                            idxs, txts = zip(*to_translate)
                            results = _batch_translate(list(txts), source_code, target_code)
                            for idx, res in zip(idxs, results):
                                translated[idx] = res

                        # Pre-calculate bullet heights to detect overflow into subsequent blocks
                        bullet_fs = 9.0
                        line_h = bullet_fs * 1.4
                        # Map block index -> (y0, expanded_bottom)
                        bullet_zones = {}
                        for i, (bbox, orig_text, fontsize, is_bold) in enumerate(text_blocks):
                            if "•" in orig_text:
                                r = _fitz.Rect(bbox)
                                avail_w = max(page.rect.x1 - r.x0 - r.x0, 1)
                                items = [it.strip() for it in translated[i].split("•") if it.strip()]
                                total_h = sum(
                                    max(1, -(-int(_fitz.get_text_length(f"• {it}", fontname="helv", fontsize=bullet_fs)) // int(avail_w))) * line_h + bullet_fs
                                    for it in items
                                )
                                bullet_zones[i] = (r.y0, r.y0 + total_h)

                        for j, ((bbox, orig_text, fontsize, is_bold), trans) in enumerate(zip(text_blocks, translated)):
                            rect = _fitz.Rect(bbox)
                            if "•" in orig_text:
                                _, new_bottom = bullet_zones[j]
                                # Redact the full original block (not just estimated expansion) to clear all original text
                                redact_rect = _fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, max(rect.y1, new_bottom) + 4)
                            else:
                                # Redact blocks that fall inside any bullet's expanded zone
                                redact_rect = _fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                                for bullet_idx, (bullet_y0, bullet_bottom) in bullet_zones.items():
                                    if bullet_y0 < rect.y0 < bullet_bottom:
                                        break
                                else:
                                    redact_rect = rect
                            page.add_redact_annot(redact_rect, fill=(1,1,1))
                        page.apply_redactions()

                        _font_regular = overlay_regular_file
                        _font_bold    = overlay_bold_file

                        for (bbox, orig_text, fontsize, is_bold), trans in zip(text_blocks, translated):
                            rect = _fitz.Rect(bbox)
                            fontfile = _font_bold if is_bold else _font_regular
                            fontname = overlay_bold_name if is_bold else overlay_regular_name
                            fs = fontsize if fontsize > 13 else 11.7

                            # TOC lines: plain entry only, no dot leaders or page numbers
                            if "....." in orig_text or "….." in orig_text:
                                import re as _re
                                toc_fs = 11.0
                                left_x = 70
                                title = _re.sub(r'\.{2,}.*$', '', trans).strip()
                                title = _re.sub(r'\s*[-–—]?\s*\d+\s*$', '', title).strip()
                                title = _re.sub(r'\s+', ' ', title)
                                y = rect.y1 - 1
                                page.insert_text(_fitz.Point(left_x, y), title, fontsize=toc_fs, fontname=fontname, fontfile=fontfile, color=(0,0,0))
                                continue

                            # Bullet blocks: split on • and render each item wrapped within page width
                            if "•" in orig_text:
                                items = [i.strip() for i in trans.split("•") if i.strip()]
                                bullet_fs = 9.0
                                line_h = bullet_fs * 1.4
                                avail_w = page.rect.x1 - rect.x0 - rect.x0  # content width
                                y = rect.y0
                                page_bottom = page.rect.y1 - 20  # leave footer margin
                                for item in items:
                                    label = f"• {item}"
                                    text_w = _fitz.get_text_length(label, fontname="helv", fontsize=bullet_fs)
                                    n_lines = max(1, -(-int(text_w) // int(avail_w)))  # ceiling division
                                    item_h = line_h * n_lines + bullet_fs
                                    if y + item_h > page_bottom:
                                        break
                                    item_rect = _fitz.Rect(rect.x0, y, rect.x0 + avail_w, y + item_h)
                                    page.insert_textbox(item_rect, label, fontsize=bullet_fs, fontname=fontname, fontfile=fontfile, color=(0,0,0))
                                    y += item_h
                                # Track where this bullet block actually ended
                                for bz_idx, (bz_y0, bz_bottom) in bullet_zones.items():
                                    if abs(bz_y0 - rect.y0) < 2:
                                        bullet_zones[bz_idx] = (bz_y0, y)  # update to actual rendered bottom
                                        break
                                continue

                            # Blocks displaced by bullet expansion: render below the bullet's actual bottom
                            displaced_by = None
                            for bz_idx, (bz_y0, bz_bottom) in bullet_zones.items():
                                if bz_y0 < rect.y0 < bz_bottom:
                                    displaced_by = bz_bottom
                                    break
                            if displaced_by is not None:
                                displaced_rect = _fitz.Rect(rect.x0, displaced_by + 4, rect.x1, displaced_by + 4 + (rect.y1 - rect.y0) * 2)
                                for scale in [fs, fs*0.85, fs*0.7, 7]:
                                    if page.insert_textbox(displaced_rect, trans, fontsize=scale, fontname=fontname, fontfile=fontfile, color=(0,0,0)) >= 0:
                                        break
                                continue

                            for scale in [fs, fs*0.85, fs*0.7, 7]:
                                result = page.insert_textbox(rect, trans, fontsize=scale, fontname=fontname, fontfile=fontfile, color=(0,0,0))
                                if result >= 0:
                                    break

                    if len(doc) > 1:
                        for idx in range(1, len(doc)):
                            page = doc[idx]
                            page.insert_textbox(
                                _fitz.Rect(72, page.rect.y1 - 28, page.rect.x1 - 72, page.rect.y1 - 8),
                                str(idx),
                                fontsize=10,
                                fontname=reportlab_regular_name,
                                fontfile=reportlab_regular_file,
                                color=(0, 0, 0),
                                align=1,
                                overlay=True,
                            )

                    buf = _io.BytesIO()
                    doc.save(buf, deflate=True, garbage=4)
                    raw_bytes = buf.getvalue()

                    # Skip format fixer — we already render at correct size with DejaVu
                    content = raw_bytes

                    with open(cached_pdf_path, "wb") as f:
                        f.write(content)

                filename = f"translation_{translation_id}.pdf"
            except Exception as e:
                import logging, traceback
                logging.getLogger(__name__).warning(f"PDF translation failed: {e}\n{traceback.format_exc()[-500:]}")
                content = None

        # .docx translation — workbook-style PDF from cached translated text.
        elif book and has_source_docx:
            try:
                import io as _io, os, re as _re
                from app.models import Language
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Image as RLImage, Table, TableStyle
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.lib.enums import TA_LEFT, TA_CENTER
                from reportlab.lib import colors
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont

                lang = db.query(Language).filter(Language.id == translation.language_id).first()
                target_code = (lang.libretranslate_code or lang.code) if lang else "sw"
                docx_font_set = _resolve_font_set(target_code)
                docx_regular_name = "DocxPdfFont"
                docx_bold_name = "DocxPdfFont-Bold"
                try:
                    pdfmetrics.registerFont(TTFont(docx_regular_name, docx_font_set["reportlab_regular_file"]))
                except Exception:
                    pass
                try:
                    pdfmetrics.registerFont(TTFont(docx_bold_name, docx_font_set["reportlab_bold_file"]))
                except Exception:
                    pass

                renderer_cache_version = "renderer_v18"
                cache_suffix = f"_translated_{translation.language_id}_{renderer_cache_version}_{translation.id}"
                if cache_variant:
                    cache_suffix = f"{cache_suffix}_{cache_variant}"
                cached_pdf_key = source_docx_path.replace(".docx", f"{cache_suffix}.pdf")
                cached_pdf_path = f"/app/storage/{cached_pdf_key}"

                if os.path.exists(cached_pdf_path) and not refresh_cache:
                    with open(cached_pdf_path, "rb") as f:
                        content = f.read()
                else:
                    # Preferred DOCX path: preserve the original DOCX structure, then let
                    # LibreOffice render PDF. This keeps Word tables/images/borders much
                    # closer to the source than rebuilding with ReportLab.
                    pdf_normalized_docx = bool(
                        getattr(book, "normalized_docx_path", None)
                        and (book.file_path or "").lower().endswith(".pdf")
                    )
                    # Use one deterministic workbook renderer by default so first render,
                    # cache refresh, and rebuild-style renders have the same layout contract.
                    # The DOCX/LibreOffice preserve path is now opt-in for diagnostics only.
                    preserve_docx_layout = True
                    try:
                        import shutil as _shutil, subprocess as _subprocess, tempfile as _tempfile
                        from app.services.docx_translation_service import apply_translated_paragraphs_to_docx_bytes

                        _soffice = _shutil.which("libreoffice") or _shutil.which("soffice")
                        if _soffice and preserve_docx_layout:
                            with open(f"/app/storage/{source_docx_path}", "rb") as _src_docx_file:
                                _translated_docx = apply_translated_paragraphs_to_docx_bytes(
                                    _src_docx_file.read(),
                                    text or "",
                                )
                            with _tempfile.TemporaryDirectory() as _tmpdir:
                                _input_docx = os.path.join(_tmpdir, "translated.docx")
                                _lo_profile = os.path.join(_tmpdir, "lo-profile")
                                os.makedirs(_lo_profile, exist_ok=True)
                                with open(_input_docx, "wb") as _tmp_docx_file:
                                    _tmp_docx_file.write(_translated_docx)
                                _subprocess.run(
                                    [
                                        _soffice,
                                        f"-env:UserInstallation=file://{_lo_profile}",
                                        "--headless",
                                        "--convert-to",
                                        "pdf",
                                        "--outdir",
                                        _tmpdir,
                                        _input_docx,
                                    ],
                                    check=True,
                                    stdout=_subprocess.PIPE,
                                    stderr=_subprocess.PIPE,
                                    timeout=120,
                                )
                                _converted_pdf = os.path.join(_tmpdir, "translated.pdf")
                                if os.path.exists(_converted_pdf):
                                    with open(_converted_pdf, "rb") as _pdf_file:
                                        content = _pdf_file.read()
                                    try:
                                        import fitz as _fitz
                                        _doc = _fitz.open(stream=content, filetype="pdf")
                                        for _page_index in range(len(_doc)):
                                            _page = _doc[_page_index]
                                            _rect = _page.rect
                                            _page.insert_text(
                                                (_rect.width / 2.0, _rect.height - 22),
                                                str(_page_index + 1),
                                                fontsize=8,
                                                fontname="helv",
                                                color=(0, 0, 0),
                                            )
                                        _buf = _doc.tobytes(deflate=True, garbage=4)
                                        _doc.close()
                                        content = _buf
                                    except Exception as _page_num_exc:
                                        import logging as _page_num_logging
                                        _page_num_logging.getLogger(__name__).warning(f"PDF page number stamping failed: {_page_num_exc}")
                                    try:
                                        from app.services.document_conversion_service import compress_pdf_bytes
                                        content = compress_pdf_bytes(content)
                                    except Exception:
                                        pass
                                    with open(cached_pdf_path, "wb") as _cache_file:
                                        _cache_file.write(content)
                                    filename = f"translation_{translation_id}.pdf"
                                    return Response(
                                        content=content,
                                        media_type="application/pdf",
                                        headers={"Content-Disposition": f"attachment; filename={filename}"},
                                    )
                    except Exception as _lo_exc:
                        import logging as _lo_logging
                        _lo_logging.getLogger(__name__).warning(f"LibreOffice DOCX PDF conversion failed; falling back to ReportLab: {_lo_exc}")

                    raw_lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
                    if raw_lines:
                        deduped_lines = []
                        prev_norm = None
                        for _line in raw_lines:
                            _norm = _re.sub(r'\s+', ' ', (_line or '').strip()).upper()
                            if _norm and _norm == prev_norm:
                                continue
                            deduped_lines.append(_line)
                            prev_norm = _norm
                        raw_lines = deduped_lines
                    if not raw_lines:
                        raise ValueError("No translated text available for DOCX PDF")

                    def _safe(value):
                        return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                    def _is_exam(line):
                        return bool(_re.match(r'^(EXAMINATION|UCHUNGUZI|EKSAMEN|KUONGORORA|UKUHLOLWA|UHLOLO)\b', line or '', _re.IGNORECASE))

                    def _is_toc(line):
                        value = (line or '').strip().upper()
                        return (
                            value in {"YALIYOMO", "ORODHA YA YALIYOMO", "TABLE OF CONTENTS", "INHOUDSOPGAWE", "OKUQUKETHWE", "ZVIRI MUKATI", "ATỌKA AKOONU", "TABLE ƊE ƊEƊƊI"}
                            or "YALIYOMO" in value and len(value) <= 40
                            or "INHOUDSOPGAWE" in value and len(value) <= 40
                            or "ATỌKA" in value and "AKOONU" in value and len(value) <= 60
                            or "TABLE ƊE" in value and len(value) <= 60
                        )

                    chapter_re = _re.compile(r'^(?:CHAPTER\s+(?:\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE)\s*[-–:]|SURA(?:\s+YA)?\s+(?:\d+|KWANZA|PILI|TATU|NNE|TANO|SITA|SABA|NANE|TISA|KUMI(?:\s+NA\s+\S+)?)\s*[-–:]|ISAHLUKO\s+[^-–:]{1,80}\s*[-–:]|HOOFSTUK\s+\S+\s*[-–:]|CHITSAUKO\s+[^-–:]{1,80}\s*[-–:]|CAP[IÍ]TULO\s+\S+\s*[-–:]|SEHEMU(?:\s+YA)?\s+\d+\s*[:\-–]|SECTION\s+\d+\s*[:\-–]|SEKSIE\s+\d+\s*[:\-–]|AFDELING\s+\d+\s*[:\-–]|AP[ÁA]\s+\d+\s*[:\-–]|TAŊRE\s+\d+\s*[:\-–]|OR[IÍ]\s+\d+\s*[:\-–]|FAANDAARE\s+\d+\s*[:\-–]|ISIGABA\s+\d+\s*[:\-–])', _re.IGNORECASE)

                    def _is_chapter(line):
                        return bool(chapter_re.match(line or ''))

                    def _is_body_chapter_reference(line, line_idx=None):
                        value = (line or '').strip()
                        if _re.match(r'^(?:SURA(?:\s+YA)?|CHAPTER|ISAHLUKO|HOOFSTUK|CHITSAUKO)\s+(?:\d+|[lI])\s*[-–]\s*\d+\s*:', value, _re.IGNORECASE):
                            return True
                        if _re.match(r'^(?:SURA(?:\s+YA)?|CHAPTER|ISAHLUKO|HOOFSTUK|CHITSAUKO)\s+\d+\s*:', value, _re.IGNORECASE):
                            if line_idx is None:
                                return True
                            return _source_heading_level_for_line(line_idx) not in (1, 2)
                        return False

                    image_by_line = {}
                    original_text_by_line = {}
                    legal_line_indices = set()
                    source_legal_lines = []
                    docx_cover_image_candidates = []
                    bold_line_indices = set()
                    numbered_line_numbers = {}
                    bullet_line_indices = set()
                    underline_prefix_indices = set()
                    underline_suffix_indices = set()
                    table_by_line = {}
                    translated_table_line_counts = {}
                    source_heading_level_by_line = {}
                    skip_table_line_indices = set()
                    try:
                        from docx import Document as _DocxDocument
                        from docx.text.paragraph import Paragraph as _DocxParagraph
                        from docx.table import Table as _DocxTable

                        _docx_source_path = source_docx_path or book.file_path
                        _docx_doc = _DocxDocument(f"/app/storage/{_docx_source_path}")
                        _line_cursor = 0
                        _number_seq = 0
                        _last_numbered_line = None

                        def _record_docx_paragraph(_para):
                            nonlocal _line_cursor, _number_seq, _last_numbered_line
                            _has_image = bool(_para._p.xpath('.//*[local-name()="drawing"]'))
                            _text = (_para.text or '').strip()
                            _style_name = (_para.style.name or '').lower() if _para.style else ''
                            _has_bold = any(bool(run.bold) for run in _para.runs if (run.text or '').strip())
                            _has_numbering = bool(_para._p.xpath('.//*[local-name()="numPr"]')) or _style_name.startswith('list')
                            _heading_match = _re.search(r"heading\s*(\d+)", _style_name or "")
                            _underlined_tab_runs = [run.text for run in _para.runs if run.underline and '\t' in (run.text or '')]
                            _current_line = _line_cursor
                            if _text:
                                original_text_by_line[_current_line] = _text
                                if _heading_match:
                                    try:
                                        source_heading_level_by_line[_current_line] = int(_heading_match.group(1))
                                    except Exception:
                                        pass
                                elif _style_name == "title":
                                    source_heading_level_by_line[_current_line] = 0
                                if _re.search(r'©|copyright|all rights reserved|scripture quotations|thomas nelson|international bible society|tyndale house|used by permission', _text, _re.IGNORECASE):
                                    legal_line_indices.add(_current_line)
                                    source_legal_lines.append(_text)
                                if 'heading' in _style_name or _has_bold or (_text.isupper() and len(_text) <= 120):
                                    bold_line_indices.add(_current_line)
                                if _underlined_tab_runs:
                                    if (_para.text or '').startswith('\t'):
                                        underline_prefix_indices.add(_current_line)
                                    else:
                                        underline_suffix_indices.add(_current_line)
                                if _has_numbering:
                                    # Do not synthesize numbers from DOCX numbering metadata.
                                    # Some source paragraphs inherit numPr/list styles even when
                                    # they are normal body text, which caused random "1." prefixes.
                                    _last_numbered_line = None
                                    _number_seq = 0
                                elif _text and not _text.endswith(':') and 'heading' not in _style_name:
                                    _last_numbered_line = None
                                    _number_seq = 0
                                if _has_image:
                                    _target_line = _current_line
                                _line_cursor += 1
                            elif _has_image:
                                _target_line = max(_line_cursor - 1, 0)
                            else:
                                return None
                            if _has_image:
                                _images = []
                                _extents = _para._p.xpath('.//*[local-name()="extent"]')
                                _display_size = None
                                if _extents:
                                    try:
                                        _cx = int(_extents[0].get('cx') or 0)
                                        _cy = int(_extents[0].get('cy') or 0)
                                        if _cx > 0 and _cy > 0:
                                            _display_size = (_cx / 914400.0 * inch, _cy / 914400.0 * inch)
                                    except Exception:
                                        _display_size = None
                                _rel_ids = _para._p.xpath('.//*[local-name()="blip"]/@*[local-name()="embed"]')
                                for _rid in _rel_ids:
                                    try:
                                        _rel = _para.part.rels.get(_rid)
                                        if _rel is not None and 'image' in getattr(_rel, 'reltype', ''):
                                            _images.append({"blob": _rel.target_part.blob, "display_size": _display_size})
                                    except Exception:
                                        pass
                                if _images:
                                    image_by_line.setdefault(_target_line, []).extend(_images)
                                    docx_cover_image_candidates.extend(_images)
                            return _current_line if _text else None

                        for _block in _docx_doc.element.body.iterchildren():
                            if _block.tag.endswith('}p'):
                                _record_docx_paragraph(_DocxParagraph(_block, _docx_doc))
                            elif _block.tag.endswith('}tbl'):
                                _table = _DocxTable(_block, _docx_doc)
                                _table_start = _line_cursor
                                _table_rows = []
                                _table_indices = []
                                for _row in _table.rows:
                                    _row_cells = []
                                    for _cell in _row.cells:
                                        _cell_indices = []
                                        for _cell_para in _cell.paragraphs:
                                            if (_cell_para.text or '').strip():
                                                _cell_idx = _record_docx_paragraph(_cell_para)
                                                if _cell_idx is not None:
                                                    _cell_indices.append(_cell_idx)
                                                    _table_indices.append(_cell_idx)
                                        _row_cells.append(_cell_indices)
                                    if any(_row_cells):
                                        _table_rows.append(_row_cells)
                                if _table_rows:
                                    table_by_line[_table_start] = _table_rows
                                    skip_table_line_indices.update(_table_indices)
                    except Exception:
                        image_by_line = {}
                        original_text_by_line = {}
                        legal_line_indices = set()
                        source_legal_lines = []
                        docx_cover_image_candidates = []
                        bold_line_indices = set()
                        numbered_line_numbers = {}
                        bullet_line_indices = set()
                        underline_prefix_indices = set()
                        underline_suffix_indices = set()
                        table_by_line = {}
                        translated_table_line_counts = {}
                        source_heading_level_by_line = {}
                        skip_table_line_indices = set()

                    def _is_legal_text(value):
                        return bool(_re.search(
                            r'©|copyright|kopiereg|all rights reserved|alle regte voorbehou|no part of this publication|geen deel van hierdie publikasie|scripture quotations|skrifaanhalings|thomas nelson|international bible society|internasionale bybelgenootskap|tyndale house|used by permission|gebruik met toestemming',
                            value or '',
                            _re.IGNORECASE,
                        ))

                    def _pick_source_legal_line(value):
                        clean = (value or '').strip()
                        lower = clean.lower()
                        candidates = source_legal_lines or []
                        if not candidates:
                            return None
                        checks = []
                        if '©' in clean and ('team impact' in lower or 'christelike universiteit' in lower or 'christian university' in lower):
                            checks.append(lambda src: '©' in src and 'team impact' in src.lower())
                        if 'thomas nelson' in lower:
                            checks.append(lambda src: 'thomas nelson' in src.lower())
                        if 'international bible society' in lower or 'internasionale bybelgenootskap' in lower:
                            checks.append(lambda src: 'international bible society' in src.lower())
                        if 'tyndale' in lower:
                            checks.append(lambda src: 'tyndale' in src.lower())
                        if 'all rights reserved' in lower or 'alle regte voorbehou' in lower or 'no part of this publication' in lower or 'geen deel van hierdie publikasie' in lower:
                            checks.append(lambda src: 'all rights reserved' in src.lower() or 'no part of this publication' in src.lower())
                        if 'copyright' in lower or 'kopiereg' in lower:
                            checks.append(lambda src: 'copyright' in src.lower())
                        if 'scripture quotations' in lower or 'skrifaanhalings' in lower:
                            checks.append(lambda src: 'scripture quotations' in src.lower())
                        for check in checks:
                            for src in candidates:
                                if check(src):
                                    return src
                        return None

                    source_to_trans_idx = {}
                    trans_to_source_idx = {}
                    _line_shift = 0
                    for _src_idx in sorted(original_text_by_line):
                        _src_text = (original_text_by_line.get(_src_idx) or "").strip()
                        _candidate_idx = _src_idx - _line_shift
                        if _src_text.lower() in {"by"} and (_candidate_idx >= len(raw_lines) or (raw_lines[_candidate_idx] or "").strip().lower() != "by"):
                            _line_shift += 1
                            continue
                        if 0 <= _candidate_idx < len(raw_lines):
                            source_to_trans_idx[_src_idx] = _candidate_idx
                            trans_to_source_idx[_candidate_idx] = _src_idx

                    def _source_heading_level_for_line(line_idx):
                        if line_idx in source_heading_level_by_line:
                            return source_heading_level_by_line.get(line_idx)
                        _src_idx = trans_to_source_idx.get(line_idx)
                        if _src_idx is None:
                            return None
                        return source_heading_level_by_line.get(_src_idx)

                    legal_override_by_line = {}
                    for _line_idx, _line in enumerate(raw_lines):
                        if _is_legal_text(_line):
                            _source_legal = original_text_by_line.get(_line_idx) if _line_idx in legal_line_indices else None
                            if not _source_legal:
                                _source_legal = _pick_source_legal_line(_line)
                            if _source_legal:
                                legal_override_by_line[_line_idx] = _source_legal.strip()

                    def _render_line_text(line_idx, line):
                        if line_idx in _publication_line_indexes:
                            value = (line or '').strip()
                        else:
                            value = legal_override_by_line.get(line_idx, (line or '').strip())
                        value = _re.sub(r'\bSpan Impak Christelike Universiteit\b', 'Team Impact Christian University', value, flags=_re.IGNORECASE)
                        value = _re.sub(r'\bTeam Impact Christelike Universiteit\b', 'Team Impact Christian University', value, flags=_re.IGNORECASE)
                        return value

                    def _with_number_prefix(line_idx, line):
                        value = _render_line_text(line_idx, line)
                        if not value:
                            return line
                        # Normalize OCR/translation confusion of numeric 1 as lowercase L.
                        value = _re.sub(r'^[lI]\.\s+', '1. ', value)
                        is_structural_heading = bool(
                            _is_toc(value)
                            or _is_chapter(value)
                            or _re.match(r'^(UTANGULIZI|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION|KURSUS\s+INLEIDING|BIBLIOGRAPHY|MAREJELEO)\b', value, _re.IGNORECASE)
                        )
                        if is_structural_heading:
                            return value
                        if line_idx in underline_prefix_indices:
                            return value if value.startswith('_____') else f"_____ {value}"
                        if line_idx in underline_suffix_indices:
                            return value if '_____' in value else f"{value} ____________________"
                        if _re.match(r'^[-*•]\s*\S+', value):
                            return value if value.startswith('•') else _re.sub(r'^[-*]\s*', '• ', value, count=1)
                        if line_idx in numbered_line_numbers:
                            if _re.match(r'^(?:\d+|[a-zA-Z])\.\s+', value):
                                return value
                            return f"{numbered_line_numbers[line_idx]}. {value}"
                        if line_idx in bullet_line_indices:
                            if _re.match(r'^[•\-*]\s+', value):
                                return value
                            return f"• {value}"
                        return value

                    _source_exam_idx = next((_idx for _idx, _txt in sorted(original_text_by_line.items()) if _idx > 1 and _is_exam(_txt)), None)
                    _source_toc_idx = next((_idx for _idx, _txt in sorted(original_text_by_line.items()) if _idx > (_source_exam_idx or 1) and _is_toc(_txt)), None)
                    exam_idx = source_to_trans_idx.get(_source_exam_idx) if _source_exam_idx is not None else None
                    toc_idx = source_to_trans_idx.get(_source_toc_idx) if _source_toc_idx is not None else None
                    if exam_idx is None:
                        exam_idx = next((i for i, ln in enumerate(raw_lines) if i > 1 and _is_exam(ln)), None)
                    if toc_idx is not None and (toc_idx >= len(raw_lines) or not _is_toc(raw_lines[toc_idx])):
                        toc_idx = None
                    if toc_idx is None:
                        toc_idx = next((i for i, ln in enumerate(raw_lines) if i > (exam_idx or 1) and _is_toc(ln)), None)
                    if exam_idx is None:
                        exam_idx = min(2, len(raw_lines))
                    if toc_idx is None:
                        toc_idx = next((i for i, ln in enumerate(raw_lines) if i > exam_idx and _is_chapter(ln)), len(raw_lines))

                    cover_lines = raw_lines[:1]
                    title_lines = raw_lines[1:2] if len(raw_lines) > 1 else []
                    manual_lines = raw_lines[2:exam_idx]
                    exam_lines = raw_lines[exam_idx:toc_idx]
                    publication_lines = []
                    _publication_line_indexes = set()
                    if exam_lines:
                        _updated_rel_idx = None
                        for _rel_i, _front_line in enumerate(exam_lines):
                            if _re.search(r'\b(UPDATED|IMESASISHWA|OPGEDATEER|KUBUYEKEZWE|YAKAGADZIRIDZWA|ÀTÚNṢE|ATUNSE|HESƊITINAAMA|HESƊITINAA|HESƊITINDE)\b', _front_line or '', _re.IGNORECASE):
                                _updated_rel_idx = _rel_i
                        if _updated_rel_idx is not None:
                            _publication_rel_start = _updated_rel_idx
                            for _candidate_idx in range(max(0, _updated_rel_idx - 3), _updated_rel_idx + 1):
                                _candidate = exam_lines[_candidate_idx] or ''
                                if _re.search(r'(TEAM\s+IMPACT|DUƊAL|JAAMI|UNIVERSITY|YUNIFÁSÍTÌ|CHRISTIAN|KIRISTA|KERECEE)', _candidate, _re.IGNORECASE):
                                    _publication_rel_start = _candidate_idx
                                    break
                            publication_lines = exam_lines[_publication_rel_start:]
                            _publication_line_indexes = set(range(_publication_rel_start, len(exam_lines)))
                            exam_lines = exam_lines[:_publication_rel_start]

                    body_start = toc_idx + 1 if toc_idx < len(raw_lines) else toc_idx
                    pre_body_toc_entries = []
                    toc_body_line_indices = set()

                    def _is_section_heading_line(value):
                        return bool(_re.match(r'^(SEHEMU(?:\s+YA)?|SECTION|ISIGABA|SEKSIE|AFDELING|AP[ÁA]|TAŊRE)\s+\d+\s*[:\-–]', value or '', _re.IGNORECASE))

                    if toc_idx < len(raw_lines):
                        for _toc_line in raw_lines[toc_idx + 1:]:
                            _toc_value = (_toc_line or "").strip()
                            if not _toc_value:
                                continue
                            if _is_toc(_toc_value):
                                continue
                            if pre_body_toc_entries and _toc_value.upper() == pre_body_toc_entries[0].upper():
                                break
                            if not pre_body_toc_entries and _is_section_heading_line(_toc_value):
                                pre_body_toc_entries.append(_toc_value)
                                body_start = toc_idx + 2
                                break
                            if _is_chapter(_toc_value) or _re.match(r'^(UTANGULIZI|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION|KURSUS\s+INLEIDING|BIBLIOGRAPHY|MAREJELEO|CONCLUSION|HITIMISHO)\b', _toc_value, _re.IGNORECASE):
                                pre_body_toc_entries.append(_toc_value)
                                continue
                            if not pre_body_toc_entries:
                                break
                            break
                        if pre_body_toc_entries and not _is_section_heading_line(pre_body_toc_entries[0]):
                            body_start = toc_idx + 1 + len(pre_body_toc_entries)
                    if pdf_normalized_docx:
                        # DOCX-converted PDFs often contain only a TOC title, not real TOC rows.
                        # Use copied headings for the synthesized TOC, but keep those headings in the body.
                        body_start = toc_idx + 1 if toc_idx < len(raw_lines) else toc_idx
                        pre_body_toc_entries = []
                    toc_body_line_indices = set(range(toc_idx + 1, body_start)) if toc_idx < body_start else set()
                    body_pairs = list(enumerate(raw_lines[body_start:], start=body_start))

                    _source_body_start_idx = None
                    if _source_toc_idx is not None:
                        for _src_idx in sorted(original_text_by_line):
                            if _src_idx <= _source_toc_idx:
                                continue
                            if source_heading_level_by_line.get(_src_idx) in (1, 2):
                                _source_body_start_idx = source_to_trans_idx.get(_src_idx)
                                break
                    if _source_body_start_idx is not None and body_pairs and _source_body_start_idx < body_pairs[0][0]:
                        body_pairs = [(i, raw_lines[i]) for i in range(_source_body_start_idx, body_pairs[0][0]) if i < len(raw_lines)] + body_pairs

                    # Never allow the first chapter opener to disappear during TOC/front-matter slicing.
                    # Some translated workbooks place CHAPTER ONE/HOOFSTUK EEN in the TOC region and
                    # then start body text at KEY VERSE/INTRODUCTION, which drops the visible chapter title.
                    _first_chapter_pair = next(
                        (
                            (_idx, _line)
                            for _idx, _line in enumerate(raw_lines)
                            if _is_chapter(_line)
                            and not _is_body_chapter_reference(_line, _idx)
                            and _re.search(r'\b(?:1|ONE|EEN|KWANZA|OKUQALA|KUTANGA|UMWE)\b', _line or '', _re.IGNORECASE)
                        ),
                        None,
                    )
                    if _first_chapter_pair is not None:
                        _first_chapter_idx, _first_chapter_line = _first_chapter_pair
                        _body_has_first_chapter = any(
                            ((_line or '').strip().upper() == (_first_chapter_line or '').strip().upper())
                            for _, _line in body_pairs[:12]
                        )
                        _body_starts_after_first_chapter = body_pairs and body_pairs[0][0] > _first_chapter_idx
                        if not _body_has_first_chapter and _body_starts_after_first_chapter:
                            body_pairs.insert(0, _first_chapter_pair)

                    def _is_closing_promo_start(value):
                        clean = (value or '').strip()
                        return bool(_re.match(
                            r'^(?:if\s+you\s+are\s+looking\s+for|iwe\s+unatafuta|of\s+jy\s+nou\s+soek|uma\s+ufuna|kungakhathaliseki\s+ukuthi\s+ufuna)\b',
                            clean,
                            _re.IGNORECASE,
                        ))

                    closing_pairs = []
                    _closing_start_pos = next(
                        (pos for pos, (_, _line) in enumerate(body_pairs) if _is_closing_promo_start(_line)),
                        None,
                    )
                    if _closing_start_pos is not None:
                        closing_pairs = body_pairs[_closing_start_pos:]
                        body_pairs = body_pairs[:_closing_start_pos]

                    body_lines = [ln for _, ln in body_pairs]
                    has_sectioned_structure = any(
                        _re.match(r'^(SEHEMU(?:\s+YA)?|SECTION|ISIGABA|SEKSIE|AFDELING|AP[ÁA]|TAŊRE)\s+\d+\s*[:\-–]', ln or '', _re.IGNORECASE)
                        for ln in (body_lines + pre_body_toc_entries)
                    )
                    def _is_bible_book_subhead(value):
                        clean = (value or '').strip()
                        if not clean:
                            return False
                        return bool(_re.match(
                            r'^(?:[1I]|2|3|II|III|I{1,3})\s+(?:SAMUEL|KINGS|KONINGS|KRONIEKE|CHRONICLES|CORINTHIANS|KORINTIERS|KORINTE|THESSALONIANS|THESSALONISENSE|TIMOTHY|TIMOTEUS|PETER|PETRUS|JOHN|JOHANNES|UJOHANE|YOHANE|JUAN|VA(?:KORINDE|TESARONIKA|TIMOTI)|PETRO)\b',
                            clean,
                            _re.IGNORECASE,
                        ))

                    def _source_level_looks_like_heading(value, source_level):
                        clean = (value or '').strip()
                        if source_level not in (1, 2) or not clean:
                            return False
                        if _is_bible_book_subhead(clean):
                            return False
                        if _is_chapter(clean) or _is_section_heading_line(clean):
                            return True
                        if _re.match(r'^(?:PREFACE|INTRODUCTION|NHANGANYAYA|UTANGULIZI|ISINGENISO|DIBAJI|KURSUS\s+INLEIDING|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO)\s*$', clean, _re.IGNORECASE):
                            return True
                        return bool(clean.isupper() and len(clean) <= 120)

                    def _is_major_start_heading(value, line_idx=None):
                        clean = (value or '').strip()
                        if not clean or _is_body_chapter_reference(clean, line_idx):
                            return False
                        # Sections are headings but not standalone page starts in the source books.
                        # Plain INTRODUCTION/ISINGENISO/NHANGANYAYA inside chapters are subheads,
                        # so they must not force a new page. Course-level introduction labels still do.
                        return bool(
                            (_is_chapter(clean) and not _is_section_heading_line(clean) and not _is_body_chapter_reference(clean, line_idx))
                            or _re.match(
                                r'^(?:COURSE\s+INTRODUCTION|KURSUS\s+INLEIDING|NHANGANYAYA\s+YEKOSI|ISINGENISO\s+SENKQUBO|ISINGENISO\s+SESIFUNDO|PREFACE|DIBAJI|UTANGULIZI|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO)\s*$',
                                clean,
                                _re.IGNORECASE,
                            )
                        )

                    def _is_render_heading(line, line_idx=None):
                        value = (line or '').strip()
                        if not value:
                            return False
                        _source_level = _source_heading_level_for_line(line_idx)
                        if _source_level_looks_like_heading(value, _source_level):
                            return True
                        if _re.match(r'^(UTANGULIZI|NHANGANYAYA|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION|KURSUS\s+INLEIDING|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO)\b', value, _re.IGNORECASE):
                            return bool(value.isupper() or line_idx in bold_line_indices or len(value.split()) <= 3)
                        if not _is_chapter(value):
                            return False
                        if value.isupper():
                            return True
                        if has_sectioned_structure and _is_chapter(value) and not _is_body_chapter_reference(value, line_idx):
                            return True
                        return bool(_re.match(r'^(SEHEMU|SECTION|ISIGABA|SEKSIE|AFDELING)\b', value, _re.IGNORECASE))

                    def _is_toc_entry_heading(line, line_idx=None):
                        value = (line or '').strip()
                        if not value or _is_body_chapter_reference(value, line_idx):
                            return False
                        # For DOCX-derived books, synthesize TOCs from source Heading 1 only.
                        # This prevents translated body paragraphs or Heading 2 subheads from
                        # entering the TOC when the translated TOC page is incomplete.
                        if line_idx is not None and trans_to_source_idx.get(line_idx) is not None:
                            if _source_heading_level_for_line(line_idx) != 1:
                                return False
                        if _is_chapter(value) or _is_section_heading_line(value):
                            return True
                        if _re.match(
                            r'^(UTANGULIZI|NHANGANYAYA|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION|COURSE\s+INTRODUCTION|KURSUS\s+INLEIDING|NHANGANYAYA\s+YEKOSI|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO|APPENDIX|AANHANGSEL|CHIMWE\s+CHINHU\s+CHEKUWEDZERA)\b',
                            value,
                            _re.IGNORECASE,
                        ):
                            return True
                        return False

                    toc_entries = list(pre_body_toc_entries)
                    if len(toc_entries) < 4:
                        for line_idx, ln in body_pairs:
                            if _is_toc_entry_heading(ln, line_idx):
                                if ln not in toc_entries:
                                    toc_entries.append(ln)
                    if not toc_entries and toc_idx < len(raw_lines):
                        toc_entries = [ln for ln in raw_lines[toc_idx + 1: min(toc_idx + 20, len(raw_lines))] if ln]
                    if toc_entries and 'toc_title' in locals():
                        toc_title_value = _re.sub(r"\s+", " ", (toc_title or "").strip()).upper()
                        if toc_title_value:
                            toc_entries = [
                                ln for ln in toc_entries
                                if _re.sub(r"\s+", " ", (ln or "").strip()).upper() != toc_title_value
                            ]

                    def _is_synthesized_toc_heading(value, line_idx=None):
                        clean = (value or "").strip()
                        if not clean or _is_body_chapter_reference(clean, line_idx):
                            return False
                        if _is_closing_promo_start(clean):
                            return False
                        if _is_section_heading_line(clean) or _is_chapter(clean):
                            return True
                        return bool(_re.match(
                            r'^(?:PREFACE|INTRODUCTION|NHANGANYAYA|UTANGULIZI|ISINGENISO|DIBAJI|KURSUS\s+INLEIDING|BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO)\s*$',
                            clean,
                            _re.IGNORECASE,
                        ))

                    if pdf_normalized_docx:
                        synthesized_toc_entries = []
                        seen_synthesized_toc = set()
                        for _line_idx, _line in body_pairs:
                            candidate = (_line or "").strip()
                            if _is_closing_promo_start(candidate):
                                break
                            if not _is_synthesized_toc_heading(candidate, _line_idx):
                                continue
                            key = _re.sub(r"\s+", " ", candidate).strip().upper()
                            if key in seen_synthesized_toc:
                                continue
                            seen_synthesized_toc.add(key)
                            synthesized_toc_entries.append(candidate)
                        if len(synthesized_toc_entries) >= 3:
                            toc_entries = synthesized_toc_entries

                    buf = _io.BytesIO()
                    doc = SimpleDocTemplate(
                        buf,
                        pagesize=A4,
                        leftMargin=0.62 * inch,
                        rightMargin=0.62 * inch,
                        topMargin=0.68 * inch,
                        bottomMargin=0.68 * inch,
                    )

                    title_style = ParagraphStyle("DocxTitle", fontName=docx_bold_name, fontSize=18, leading=18, alignment=TA_LEFT, spaceAfter=0, splitLongWords=0)
                    cover_style = ParagraphStyle("DocxCover", fontName=docx_bold_name, fontSize=16, leading=16, alignment=TA_CENTER, spaceAfter=0, splitLongWords=0)
                    heading_style = ParagraphStyle("DocxHeading", fontName=docx_bold_name, fontSize=15, leading=15, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    subhead_style = ParagraphStyle("DocxSub", fontName=docx_bold_name, fontSize=9.5, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    body_style = ParagraphStyle("DocxBody", fontName=docx_regular_name, fontSize=10, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    table_cell_style = ParagraphStyle("DocxTableCell", fontName=docx_regular_name, fontSize=8.5, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    table_header_style = ParagraphStyle("DocxTableHeader", fontName=docx_bold_name, fontSize=8.5, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    toc_style = ParagraphStyle("DocxToc", fontName=docx_regular_name, fontSize=12, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)
                    warn_style = ParagraphStyle("DocxWarn", fontName=docx_bold_name, fontSize=9, leading=10.5, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, splitLongWords=0)

                    story = []

                    def _render_original_docx_first_page_image():
                        try:
                            import shutil as _shutil, subprocess as _subprocess, tempfile as _tempfile
                            import fitz as _fitz
                            _soffice_cover = _shutil.which("libreoffice") or _shutil.which("soffice")
                            if not _soffice_cover or not source_docx_path:
                                return None
                            with _tempfile.TemporaryDirectory() as _tmpdir:
                                _profile = os.path.join(_tmpdir, "lo-profile-cover")
                                os.makedirs(_profile, exist_ok=True)
                                _subprocess.run(
                                    [
                                        _soffice_cover,
                                        f"-env:UserInstallation=file://{_profile}",
                                        "--headless",
                                        "--convert-to",
                                        "pdf",
                                        "--outdir",
                                        _tmpdir,
                                        f"/app/storage/{source_docx_path}",
                                    ],
                                    check=True,
                                    stdout=_subprocess.PIPE,
                                    stderr=_subprocess.PIPE,
                                    timeout=120,
                                )
                                _pdfs = [os.path.join(_tmpdir, _name) for _name in os.listdir(_tmpdir) if _name.lower().endswith(".pdf")]
                                if not _pdfs:
                                    return None
                                _doc_pdf = _fitz.open(_pdfs[0])
                                if not len(_doc_pdf):
                                    _doc_pdf.close()
                                    return None
                                _page = _doc_pdf[0]
                                _pix = _page.get_pixmap(matrix=_fitz.Matrix(1.6, 1.6), alpha=False)
                                _png = _pix.tobytes("png")
                                _doc_pdf.close()
                                return _png
                        except Exception as _cover_exc:
                            import logging as _cover_logging
                            _cover_logging.getLogger(__name__).warning(f"DOCX first-page cover render failed: {_cover_exc}")
                            return None

                    original_docx_first_page_image = None
                    if not pdf_normalized_docx:
                        original_docx_first_page_image = _render_original_docx_first_page_image()

                    def _append_images_for_line(line_idx):
                        for _img_item in image_by_line.get(line_idx, []):
                            try:
                                _img_bytes = _img_item.get("blob") if isinstance(_img_item, dict) else _img_item
                                _display_size = _img_item.get("display_size") if isinstance(_img_item, dict) else None
                                _img_buf = _io.BytesIO(_img_bytes)
                                _img = RLImage(_img_buf)
                                if _display_size:
                                    _img.drawWidth, _img.drawHeight = _display_size
                                _max_w = min(A4[0] - doc.leftMargin - doc.rightMargin, 3.0 * inch)
                                _max_h = 2.0 * inch
                                _scale = min(_max_w / float(_img.drawWidth or 1), _max_h / float(_img.drawHeight or 1), 1.0)
                                _img.drawWidth *= _scale
                                _img.drawHeight *= _scale
                                story.append(Spacer(1, 0.08 * inch))
                                story.append(_img)
                                story.append(Spacer(1, 0.08 * inch))
                            except Exception:
                                continue

                    def _append_table_for_line(line_idx):
                        rows = table_by_line.get(line_idx)
                        if not rows:
                            return False
                        max_cols = max((len(row) for row in rows), default=0)
                        if max_cols < 2:
                            return False
                        table_data = []
                        _table_cursor = line_idx
                        _available_table_lines = sum(max(len(_cell), 1) for _row in rows for _cell in _row)
                        _translated_table_lines = translated_table_line_counts.get(line_idx, _available_table_lines)
                        _table_end = min(len(raw_lines), line_idx + min(_available_table_lines, _translated_table_lines))
                        for row_idx, row in enumerate(rows):
                            padded = list(row) + [[] for _ in range(max_cols - len(row))]
                            rendered_row = []
                            for cell_indices in padded:
                                _cell_line_count = max(len(cell_indices), 1)
                                _cell_lines = []
                                for _ in range(_cell_line_count):
                                    if _table_cursor < _table_end:
                                        _cell_lines.append(raw_lines[_table_cursor])
                                    _table_cursor += 1
                                cell_text = "<br/>".join(_safe(_with_number_prefix(_table_cursor - len(_cell_lines) + _offset, _line)) for _offset, _line in enumerate(_cell_lines) if _line)
                                rendered_row.append(Paragraph(cell_text or " ", table_header_style if row_idx == 0 else table_cell_style))
                            table_data.append(rendered_row)
                        available_width = A4[0] - doc.leftMargin - doc.rightMargin
                        if max_cols == 3:
                            first_col_text = " ".join(raw_lines[i] for row in rows for cell in row[:1] for i in cell if i < len(raw_lines))
                            second_col_text = " ".join(raw_lines[i] for row in rows for cell in row[1:2] for i in cell if i < len(raw_lines))
                            if len(first_col_text) < 80 and len(second_col_text) < 80:
                                col_widths = [0.95 * inch, 1.05 * inch, max(available_width - 2.0 * inch, 2.5 * inch)]
                            else:
                                col_widths = [available_width / max_cols] * max_cols
                        else:
                            col_widths = [available_width / max_cols] * max_cols
                        table = Table(table_data, colWidths=col_widths, repeatRows=1 if len(table_data) > 1 else 0, hAlign="LEFT")
                        table.setStyle(TableStyle([
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]))
                        story.append(Spacer(1, 0.08 * inch))
                        story.append(table)
                        story.append(Spacer(1, 0.08 * inch))
                        return True

                    def _append_original_docx_cover_page():
                        if not original_docx_first_page_image:
                            return False
                        try:
                            _img = RLImage(_io.BytesIO(original_docx_first_page_image))
                            _max_w = A4[0] - doc.leftMargin - doc.rightMargin
                            _max_h = A4[1] - doc.topMargin - doc.bottomMargin
                            _scale = min(_max_w / float(_img.drawWidth or 1), _max_h / float(_img.drawHeight or 1), 1.0)
                            _img.drawWidth *= _scale
                            _img.drawHeight *= _scale
                            story.append(_img)
                            return True
                        except Exception:
                            return False

                    if _append_original_docx_cover_page():
                        story.append(PageBreak())
                    else:
                        def _docx_cover_has_mapped_image():
                            return bool(image_by_line.get(0))

                        for idx, ln in enumerate(cover_lines):
                            story.append(Spacer(1, 0.2 * inch if idx == 0 and _docx_cover_has_mapped_image() else 2.0 * inch))
                            _append_images_for_line(idx)
                            story.append(Paragraph(_safe(ln), cover_style))
                        story.append(PageBreak())

                    for idx, ln in enumerate(title_lines, start=1):
                        # Keep title-page images on the title page. Rendering them after a
                        # large spacer can overflow and create a blank page before the manual.
                        _append_images_for_line(idx)
                        story.append(Spacer(1, 1.15 * inch))
                        story.append(Paragraph(_safe(ln), title_style))
                    story.append(PageBreak())

                    for local_idx, ln in enumerate(manual_lines, start=2):
                        render_ln = _render_line_text(local_idx, ln)
                        style = heading_style if local_idx == 2 or (ln.isupper() and len(ln) < 90) or local_idx in bold_line_indices else body_style
                        story.append(Paragraph(_safe(render_ln), style))
                        _append_images_for_line(local_idx)
                    story.append(PageBreak())

                    if publication_lines and all(_re.search(r'\b(UPDATED|YAKAGADZIRIDZWA|OPGEDATEER|KUBUYEKEZWE|IMESASISHWA)\b', ln or '', _re.IGNORECASE) for ln in publication_lines):
                        _publication_line_indexes = set(range(len(exam_lines), len(exam_lines) + len(publication_lines)))
                        exam_lines = exam_lines + publication_lines
                        publication_lines = []
                    exam_render_lines = list(exam_lines)
                    for local_idx, ln in enumerate(exam_render_lines, start=exam_idx):
                        render_ln = _render_line_text(local_idx, ln)
                        if local_idx == exam_idx:
                            story.append(Paragraph(_safe(render_ln), heading_style))
                        elif ln.isupper() and len(ln) < 180:
                            story.append(Paragraph(_safe(render_ln), warn_style))
                        else:
                            story.append(Paragraph(_safe(render_ln), body_style))
                        _append_images_for_line(local_idx)
                    story.append(PageBreak())

                    if publication_lines:
                        _publication_start_idx = exam_idx + len(exam_render_lines)
                        for offset, ln in enumerate(publication_lines):
                            abs_idx = _publication_start_idx + offset
                            render_ln = (ln or '').strip()
                            _legalish = bool(_re.search(r'(copyright|all rights reserved|no part of this publication|rights reserved|prior written permission|publisher|publisher\.)', render_ln, _re.IGNORECASE))
                            if _legalish:
                                render_ln = legal_override_by_line.get(abs_idx, render_ln)
                            if offset == 0 or abs_idx in bold_line_indices:
                                story.append(Paragraph(_safe(render_ln), heading_style if len(render_ln) <= 90 else body_style))
                            else:
                                story.append(Paragraph(_safe(render_ln), body_style))
                            _append_images_for_line(abs_idx)
                        story.append(PageBreak())

                    def _cleanup_docx_toc_entries(_entries):
                        _cleaned = []
                        _seen = set()
                        _seen_major = False
                        for _entry in _entries or []:
                            _value = (_entry or '').strip()
                            if not _value:
                                continue
                            _is_intro = bool(_re.match(r'^(UTANGULIZI|NHANGANYAYA\s+YEKOSI|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION|COURSE\s+INTRODUCTION|KURSUS\s+INLEIDING)\b', _value, _re.IGNORECASE))
                            _is_major = bool(_is_chapter(_value) or _is_section_heading_line(_value) or _re.match(r'^(BIBLIOGRAPHY|BHAIBHERI|MAREJELEO|CONCLUSION|MHEDZISO|HITIMISHO|APPENDIX|AANHANGSEL|CHIMWE\s+CHINHU\s+CHEKUWEDZERA)\b', _value, _re.IGNORECASE))
                            if _seen_major and _is_intro:
                                continue
                            if not (_is_intro or _is_major):
                                continue
                            _key = _re.sub(r'\s+', ' ', _value).strip().upper()
                            if _key in _seen:
                                continue
                            _seen.add(_key)
                            _cleaned.append(_value)
                            if _is_major:
                                _seen_major = True
                        return _cleaned

                    toc_entries = _cleanup_docx_toc_entries(toc_entries) or toc_entries
                    def _toc_canon(_value):
                        return _re.sub(r'[^A-Z0-9]+', '', _re.sub(r"\s+", " ", (_value or '').strip()).upper())
                    toc_title_value = _re.sub(r"\s+", " ", (toc_title_text or raw_lines[toc_idx] if toc_idx < len(raw_lines) else "YALIYOMO").strip()).upper()
                    body_heading_value = _re.sub(r"\s+", " ", (body_heading_after_toc or "").strip()).upper()
                    intro_heading_value = _re.sub(r"\s+", " ", (intro_heading_after_toc or "").strip()).upper()
                    toc_entry_values = {_toc_canon(toc_title_value), _toc_canon(body_heading_value), _toc_canon(intro_heading_value)}
                    toc_entries = [
                        entry for entry in toc_entries
                        if _toc_canon(entry) not in toc_entry_values
                        and not _is_body_start_heading(entry)
                        and not _is_chapter(entry)
                    ]
                    _toc_title_line = _re.sub(r"\s+", " ", (toc_title_text or raw_lines[toc_idx] if toc_idx < len(raw_lines) else "YALIYOMO")).strip().upper()
                    toc_entries = [
                        entry for entry in toc_entries
                        if _re.sub(r"\s+", " ", (entry or "")).strip().upper() != _toc_title_line
                    ]
                    toc_body_texts = {
                        _toc_canon(entry)
                        for entry in toc_entries
                        if entry
                    }
                    if not workbook_like:
                        story.append(Paragraph(_safe(raw_lines[toc_idx] if toc_idx < len(raw_lines) else "YALIYOMO"), title_style))
                        _append_images_for_line(toc_idx)
                        story.append(Spacer(1, 0.22 * inch))
                        for entry in toc_entries:
                            story.append(Paragraph(_safe(entry), toc_style))
                        story.append(PageBreak())

                    forced_body_prefix_indices = set()

                    def _append_images_for_line(line_idx):
                        for _img_item in image_by_line.get(line_idx, []):
                            try:
                                _img_bytes = _img_item.get("blob") if isinstance(_img_item, dict) else _img_item
                                _display_size = _img_item.get("display_size") if isinstance(_img_item, dict) else None
                                _img_buf = _io.BytesIO(_img_bytes)
                                _img = RLImage(_img_buf)
                                if _display_size:
                                    _img.drawWidth, _img.drawHeight = _display_size
                                _max_w = min(A4[0] - doc.leftMargin - doc.rightMargin, 3.0 * inch)
                                _max_h = 2.0 * inch
                                _scale = min(_max_w / float(_img.drawWidth or 1), _max_h / float(_img.drawHeight or 1), 1.0)
                                _img.drawWidth *= _scale
                                _img.drawHeight *= _scale
                                story.append(Spacer(1, 0.08 * inch))
                                story.append(_img)
                                story.append(Spacer(1, 0.08 * inch))
                            except Exception:
                                continue

                    source_table_by_line = dict(table_by_line)

                    # Remap DOCX table anchors to translated body indexes. Front-matter slicing
                    # changes line offsets, so original DOCX line numbers cannot be used directly.
                    if table_by_line:
                        _table_items = sorted(table_by_line.items())
                        _table_signatures = []
                        for _table_start, _rows in _table_items:
                            _first_cell_text = ""
                            for _row in _rows:
                                for _cell in _row:
                                    if _cell:
                                        _first_cell_text = raw_lines[_cell[0]] if _cell[0] < len(raw_lines) else ""
                                        break
                                if _first_cell_text:
                                    break
                            _table_signatures.append((_table_start, _rows, _first_cell_text))
                        _remapped_tables = {}
                        _remapped_table_line_counts = {}
                        _remapped_skip_indices = set()
                        def _looks_like_translated_table_header(_idx):
                            _current = _re.sub(r'\s+', ' ', (raw_lines[_idx] if _idx < len(raw_lines) else '').strip()).lower()
                            _window = [
                                _re.sub(r'\s+', ' ', (raw_lines[_i] if _i < len(raw_lines) else '').strip()).lower()
                                for _i in range(_idx, min(_idx + 6, len(raw_lines)))
                            ]
                            _joined = ' | '.join(_window)
                            level_tokens = (
                                'vlak van operasie', 'level of operation', 'toɓɓere golle',
                                'ipele iṣẹ', 'ipele iṣẹ́', 'ipele isẹ', 'operasie'
                            )
                            counselor_tokens = (
                                'tipe berader', 'type of counselor', 'sifaa wasiyaajo',
                                'iru olùdámọ̀ràn', 'iru olumoran', 'iru olùmọ̀ràn'
                            )
                            function_tokens = ('funksie', 'function', 'kugal', 'iṣẹ', 'iṣẹ́', 'ise')
                            return bool(
                                any(token in _current for token in level_tokens)
                                and any(token in _joined for token in counselor_tokens)
                                and any(token in _joined for token in function_tokens)
                            )

                        def _translated_table_line_count(_start_idx, _rows):
                            _shape_count = sum(max(len(_cell), 1) for _row in _rows for _cell in _row)
                            _cursor = _start_idx
                            _limit = min(len(raw_lines), _start_idx + max(_shape_count + 8, 24))
                            _seen_nations = False
                            while _cursor < _limit:
                                _value = _re.sub(r'\s+', ' ', (raw_lines[_cursor] or '').strip()).lower()
                                if _cursor > _start_idx and (
                                    _value.startswith('ndee tawnoo') or _value.startswith('nde tawnoo')
                                    or _value.startswith('aangesien hierdie kursus')
                                    or _value.startswith('since this course')
                                    or _value.startswith('bí ẹ̀kọ́ yìí') or _value.startswith('bi ẹ̀kọ́ yìí')
                                    or _value.startswith('bi ẹkọ yii') or _value.startswith('bí ẹkọ yii')
                                    or _value.startswith('níwọ̀n bí')
                                    or _value.startswith('niwon')
                                ):
                                    break
                                if _re.match(r'^(5\.|5\s)', _value) or 'leƴƴi' in _value or 'nasies' in _value or 'nations' in _value:
                                    _seen_nations = True
                                _cursor += 1
                                if _seen_nations and _cursor < len(raw_lines):
                                    _next = _re.sub(r'\s+', ' ', (raw_lines[_cursor] or '').strip()).lower()
                                    if (
                                        _next.startswith('ndee tawnoo') or _next.startswith('nde tawnoo')
                                        or _next.startswith('aangesien hierdie kursus')
                                        or _next.startswith('since this course')
                                        or _next.startswith('bí ẹ̀kọ́ yìí') or _next.startswith('bi ẹ̀kọ́ yìí')
                                        or _next.startswith('bi ẹkọ yii') or _next.startswith('bí ẹkọ yii')
                                        or _next.startswith('níwọ̀n bí')
                                        or _next.startswith('niwon')
                                    ):
                                        break
                            return max(_cursor - _start_idx, 1)

                        for _old_start, _rows, _first_cell_text in _table_signatures:
                            _match_idx = None
                            # Tables must start at their header row. Fuzzy matching on the first
                            # source cell can catch preceding paragraphs and pull body text into
                            # the table, so require the translated header triplet.
                            for _idx, _line in body_pairs:
                                if _looks_like_translated_table_header(_idx):
                                    _match_idx = _idx
                                    break
                            if _match_idx is None:
                                for _idx in range(0, len(raw_lines)):
                                    if _looks_like_translated_table_header(_idx):
                                        _match_idx = _idx
                                        break
                            if _match_idx is None:
                                _match_idx = _old_start
                            _remapped_tables[_match_idx] = _rows
                            _table_line_count = _translated_table_line_count(_match_idx, _rows)
                            _remapped_table_line_counts[_match_idx] = _table_line_count
                            for _skip_idx in range(_match_idx, min(len(raw_lines), _match_idx + _table_line_count)):
                                _remapped_skip_indices.add(_skip_idx)
                        table_by_line = _remapped_tables
                        translated_table_line_counts = _remapped_table_line_counts
                        skip_table_line_indices = _remapped_skip_indices

                    if source_table_by_line and source_to_trans_idx:
                        _source_mapped_tables = {}
                        _source_mapped_counts = {}
                        _source_mapped_skip = set()
                        for _src_start, _rows in sorted(source_table_by_line.items()):
                            _mapped_start = source_to_trans_idx.get(_src_start)
                            if _mapped_start is None:
                                continue
                            _shape_count = sum(max(len(_cell), 1) for _row in _rows for _cell in _row)
                            _source_mapped_tables[_mapped_start] = _rows
                            _source_mapped_counts[_mapped_start] = _shape_count
                            for _skip_idx in range(_mapped_start, min(len(raw_lines), _mapped_start + _shape_count)):
                                _source_mapped_skip.add(_skip_idx)
                        if _source_mapped_tables:
                            table_by_line = _source_mapped_tables
                            translated_table_line_counts = _source_mapped_counts
                            skip_table_line_indices = _source_mapped_skip

                    previous_was_heading = False
                    previous_was_section_heading = False
                    body_started = False
                    _last_chapter_line_idx = None
                    _numbered_run_next = None

                    def _renumber_translated_list_item(value):
                        # Do not rewrite translated numbering. Random numbering regressions came
                        # from trying to infer sequence state from inherited DOCX list metadata.
                        return value

                    _skip_body_line_indices = set()

                    def _first_following_body_paragraph(_body_pos):
                        for _next_idx, _next_ln in body_pairs[_body_pos + 1:]:
                            if _next_idx in _skip_body_line_indices or _is_toc(_next_ln):
                                continue
                            if _next_idx in table_by_line or _next_idx in skip_table_line_indices:
                                return None
                            if _is_render_heading(_next_ln, _next_idx) or ((_next_ln or '').isupper() and len(_next_ln or '') <= 100):
                                return None
                            if _next_idx in bold_line_indices and len(_next_ln or '') <= 180:
                                return None
                            _next_render = _renumber_translated_list_item(_with_number_prefix(_next_idx, _next_ln))
                            return _next_idx, Paragraph(_safe(_next_render), body_style)
                        return None

                    for _body_pos, (line_idx, ln) in enumerate(body_pairs):
                        if line_idx in toc_body_line_indices:
                            continue
                        if line_idx in _skip_body_line_indices:
                            continue
                        if _is_toc(ln):
                            continue
                        if toc_body_texts and _re.sub(r'[^A-Z0-9]+', '', _re.sub(r'\s+', ' ', (ln or '').strip()).upper()) in toc_body_texts:
                            continue
                        if line_idx in table_by_line and not _is_synthesized_toc_heading(ln, line_idx):
                            _append_table_for_line(line_idx)
                            previous_was_heading = False
                            previous_was_section_heading = False
                            body_started = True
                            continue
                        if line_idx in skip_table_line_indices and not _is_synthesized_toc_heading(ln, line_idx):
                            continue
                        render_ln = _renumber_translated_list_item(_with_number_prefix(line_idx, ln))
                        if _is_section_heading_line(ln):
                            story.append(KeepTogether([Paragraph(_safe(render_ln), subhead_style), Spacer(1, 0.02 * inch)]))
                            _append_images_for_line(line_idx)
                            previous_was_heading = True
                            previous_was_section_heading = True
                            body_started = True
                            continue
                        if _is_render_heading(ln, line_idx) and (_is_chapter(ln) or _source_heading_level_for_line(line_idx) in (1, 2)):
                            _current_is_section_heading = bool(_source_heading_level_for_line(line_idx) == 1 or _is_section_heading_line(ln))
                            if body_started and _is_major_start_heading(ln, line_idx):
                                story.append(PageBreak())
                            _heading_style_for_line = subhead_style if (_is_bible_book_subhead(ln) or (_source_heading_level_for_line(line_idx) == 2 and not _is_chapter(ln) and not _is_section_heading_line(ln))) else heading_style
                            _heading_flowables = [Paragraph(_safe(render_ln), _heading_style_for_line), Spacer(1, 0.04 * inch)]
                            _following = _first_following_body_paragraph(_body_pos)
                            if _following is not None:
                                _following_idx, _following_para = _following
                                _skip_body_line_indices.add(_following_idx)
                                _heading_flowables.append(_following_para)
                            story.append(KeepTogether(_heading_flowables))
                            _append_images_for_line(line_idx)
                            if _following is not None:
                                _append_images_for_line(_following_idx)
                            previous_was_heading = True
                            previous_was_section_heading = _current_is_section_heading
                            _last_chapter_line_idx = line_idx
                            body_started = True
                        elif _is_render_heading(ln, line_idx) and _re.match(r'^(UTANGULIZI|NHANGANYAYA|ISINGENISO|DIBAJI|PREFACE|INTRODUCTION)\b', ln, _re.IGNORECASE):
                            _intro_follows_chapter_opening = _last_chapter_line_idx is not None and (line_idx - _last_chapter_line_idx) <= 4
                            if body_started and _is_major_start_heading(ln, line_idx) and not _intro_follows_chapter_opening:
                                story.append(PageBreak())
                            _heading_flowables = [Paragraph(_safe(render_ln), heading_style), Spacer(1, 0.04 * inch)]
                            _following = _first_following_body_paragraph(_body_pos)
                            if _following is not None:
                                _following_idx, _following_para = _following
                                _skip_body_line_indices.add(_following_idx)
                                _heading_flowables.append(_following_para)
                            story.append(KeepTogether(_heading_flowables))
                            _append_images_for_line(line_idx)
                            if _following is not None:
                                _append_images_for_line(_following_idx)
                            previous_was_heading = True
                            previous_was_section_heading = False
                            _last_chapter_line_idx = None
                            body_started = True
                        elif ln.isupper() and len(ln) <= 100:
                            story.append(KeepTogether([Paragraph(_safe(render_ln), subhead_style), Spacer(1, 0.02 * inch)]))
                            _append_images_for_line(line_idx)
                            previous_was_heading = True
                            previous_was_section_heading = False
                        elif line_idx in bold_line_indices and len(ln) <= 180:
                            story.append(KeepTogether([Paragraph(_safe(render_ln), subhead_style), Spacer(1, 0.02 * inch)]))
                            _append_images_for_line(line_idx)
                            previous_was_heading = True
                            previous_was_section_heading = False
                            body_started = True
                        else:
                            story.append(Paragraph(_safe(render_ln), body_style))
                            _append_images_for_line(line_idx)
                            previous_body_heading = False
                            previous_was_heading = False
                            previous_was_section_heading = False
                            body_started = True

                    if closing_pairs:
                        story.append(PageBreak())
                        for _closing_idx, (_line_idx, _closing_line) in enumerate(closing_pairs):
                            _closing_text = _safe(_with_number_prefix(_line_idx, _closing_line))
                            if not _closing_text:
                                continue
                            _style = heading_style if _closing_idx >= max(len(closing_pairs) - 3, 0) else body_style
                            story.append(Paragraph(_closing_text, _style))
                            _append_images_for_line(_line_idx)

                    def _number_pages(canvas, doc_obj):
                        # Do not synthesize page-number footers. In long generated TOCs
                        # they are extracted as content and merge into TOC entries.
                        return

                    doc.build(story, onFirstPage=_number_pages, onLaterPages=_number_pages)
                    content = buf.getvalue()

                    # Do not replace the rebuilt closing page with LibreOffice's final DOCX page.
                    # That page can include preceding body content, which reintroduces merged/duplicated text.

                    # PDF-to-DOCX conversion can drop image-based covers. For PDF-normalized
                    # books, keep the original first PDF page when it contains an image.
                    try:
                        if pdf_normalized_docx and (book.file_path or "").lower().endswith(".pdf"):
                            import fitz as _fitz
                            _src_cover_pdf = _fitz.open(f"/app/storage/{book.file_path}")
                            _rendered_pdf = _fitz.open(stream=content, filetype="pdf")
                            if len(_src_cover_pdf) and len(_rendered_pdf):
                                _cover_page = _src_cover_pdf[0]
                                _page_area = float(_cover_page.rect.width * _cover_page.rect.height) or 1.0
                                _has_cover_image = bool(_cover_page.get_images(full=True))
                                if not _has_cover_image:
                                    for _block in _cover_page.get_text("dict").get("blocks", []):
                                        if _block.get("type") != 1:
                                            continue
                                        _bbox = _block.get("bbox") or (0, 0, 0, 0)
                                        _img_area = max(0.0, (_bbox[2] - _bbox[0]) * (_bbox[3] - _bbox[1]))
                                        if _img_area >= (_page_area * 0.25):
                                            _has_cover_image = True
                                            break
                                if _has_cover_image:
                                    _merged_pdf = _fitz.open()
                                    _merged_pdf.insert_pdf(_src_cover_pdf, from_page=0, to_page=0)
                                    if len(_rendered_pdf) > 1:
                                        _merged_pdf.insert_pdf(_rendered_pdf, from_page=1, to_page=len(_rendered_pdf) - 1)
                                    _merged_buf = _io.BytesIO()
                                    _merged_pdf.save(_merged_buf, deflate=True, garbage=4)
                                    content = _merged_buf.getvalue()
                                    _merged_pdf.close()
                            _src_cover_pdf.close()
                            _rendered_pdf.close()
                    except Exception as _cover_preserve_exc:
                        import logging as _cover_logging
                        _cover_logging.getLogger(__name__).warning(f"PDF cover preservation failed: {_cover_preserve_exc}")

                    # Drop accidental blank pages caused by pagination overflow.
                    # Page numbers alone do not count as content.
                    try:
                        import fitz as _fitz
                        _src_pdf = _fitz.open(stream=content, filetype="pdf")
                        _clean_pdf = _fitz.open()
                        for _page_no in range(len(_src_pdf)):
                            _page = _src_pdf[_page_no]
                            _text = (_page.get_text("text") or "").strip()
                            _text_without_number = _re.sub(r'^\d+$', '', _text).strip()
                            _has_images = bool(_page.get_images(full=True))
                            _has_drawings = bool(_page.get_drawings())
                            if not _text_without_number and not _has_images and not _has_drawings:
                                continue
                            _clean_pdf.insert_pdf(_src_pdf, from_page=_page_no, to_page=_page_no)
                        if len(_clean_pdf) and len(_clean_pdf) != len(_src_pdf):
                            _clean_buf = _io.BytesIO()
                            _clean_pdf.save(_clean_buf)
                            content = _clean_buf.getvalue()
                        _src_pdf.close()
                        _clean_pdf.close()
                    except Exception:
                        pass

                    with open(cached_pdf_path, "wb") as f:
                        f.write(content)

                media_type = "application/pdf"
                filename = f"translation_{translation_id}.pdf"

            except Exception as e:
                import logging, traceback
                logging.getLogger(__name__).warning(f"Docx workbook PDF failed: {e}\n{traceback.format_exc()[-800:]}")
                content = None

    if translation.content_type == "exam" and format == "xlsx":
        from app.models import Exam

        exam = db.query(Exam).filter(Exam.id == str(translation.content_id)).first()
        if exam and exam.file_path:
            from app.services.doc_service import translate_excel_from_json

            content = translate_excel_from_json(
                exam.file_path, translation.translated_text
            )
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"translation_{translation_id}.xlsx"
    elif format == "xlsx":
        book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
        if book and book.file_path and book.file_path.endswith((".xlsx", ".xls")):
            from app.services.doc_service import translate_excel_from_json

            content = translate_excel_from_json(
                book.file_path, translation.translated_text
            )
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"translation_{translation_id}.xlsx"
    elif format == "docx":
        from app.services.doc_service import create_translated_docx

        book = None
        cover_text = None
        if translation.content_type == "book":
            book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
            cover_text = book.extracted_cover_text if book else None

        source_docx_path = (getattr(book, "normalized_docx_path", None) or book.file_path) if book else None
        if book and source_docx_path and source_docx_path.endswith(".docx"):
            import os
            from app.services.docx_translation_service import apply_translated_paragraphs_to_docx_bytes

            cached_docx_key = source_docx_path.replace(".docx", f"_translated_{translation.language_id}.docx")
            cached_docx_path = f"/app/storage/{cached_docx_key}"

            if os.path.exists(cached_docx_path):
                with open(cached_docx_path, "rb") as f:
                    content = f.read()
            else:
                with open(f"/app/storage/{source_docx_path}", "rb") as f:
                    original_docx = f.read()
                content = apply_translated_paragraphs_to_docx_bytes(original_docx, text or translation.translated_text or "")
                with open(cached_docx_path, "wb") as f:
                    f.write(content)
        else:
            content = create_translated_docx(text, cover_text)

        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"translation_{translation_id}.docx"
    elif content is None:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        lang = db.query(Language).filter(Language.id == translation.language_id).first()
        fallback_font_set = _resolve_font_set((lang.libretranslate_code or lang.code) if lang else None)
        fallback_regular_name = "FallbackFont"
        fallback_bold_name = "FallbackFont-Bold"
        fallback_regular_file = fallback_font_set["overlay_regular_file"]
        fallback_bold_file = fallback_font_set["overlay_bold_file"]
        pdfmetrics.registerFont(TTFont(fallback_regular_name, fallback_regular_file))
        pdfmetrics.registerFont(TTFont(fallback_bold_name, fallback_bold_file))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        title_style = ParagraphStyle(
            "CustomTitle",
            fontName=fallback_bold_name,
            fontSize=16,
            spaceAfter=12,
            textColor=colors.black,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            fontName=fallback_bold_name,
            fontSize=12,
            spaceAfter=6,
            textColor=colors.darkblue,
        )
        body_style = ParagraphStyle(
            "CustomBody", fontName=fallback_regular_name, fontSize=10, spaceAfter=6, leading=14
        )

        story = []
        story.append(Paragraph("Translation Document", title_style))
        story.append(Spacer(1, 0.3 * inch))

        for para in text.split("\n"):
            if para.strip():
                safe = (
                    para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                if len(para) < 50 or para.rstrip().endswith(":"):
                    story.append(Paragraph(safe, heading_style))
                else:
                    story.append(Paragraph(safe, body_style))
                story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        buffer.seek(0)
        content = buffer.getvalue()

    if content is None:
        raise HTTPException(status_code=500, detail="Failed to generate file")

    if media_type == "application/pdf" and filename.lower().endswith(".pdf"):
        try:
            from app.services.document_conversion_service import compress_pdf_bytes
            content = compress_pdf_bytes(content)
        except Exception:
            pass

    if translation.content_type == "book" and format == "pdf":
        book_for_assets = db.query(Book).filter(Book.id == str(translation.content_id)).first()
        book_images = list(getattr(book_for_assets, "images", []) or []) if book_for_assets else []
        if book_images:
            import io as _io, os as _os, zipfile as _zipfile, re as _re

            zip_buffer = _io.BytesIO()
            safe_title = _re.sub(r'[^A-Za-z0-9._-]+', '-', (book_for_assets.title if book_for_assets else filename)).strip('-') or 'book'
            pdf_name = filename if filename.lower().endswith('.pdf') else f"{safe_title}.pdf"
            with _zipfile.ZipFile(zip_buffer, 'w', _zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"translation/{pdf_name}", content)
                for img in book_images:
                    image_path = f"/app/storage/{img.file_path}"
                    if not _os.path.exists(image_path):
                        continue
                    image_name = _os.path.basename(img.original_filename or img.file_path)
                    with open(image_path, 'rb') as imgf:
                        zf.writestr(f"images/{image_name}", imgf.read())
            content = zip_buffer.getvalue()
            media_type = 'application/zip'
            filename = f"{safe_title}-translation-package.zip"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
