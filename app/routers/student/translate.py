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
    cache_variant: str | None = Query(
        None,
        pattern=r"^[A-Za-z0-9_-]{1,40}$",
        description="Optional suffix for writing/reading a separate cached PDF variant.",
    ),
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

    if translation.status != "done":
        raise HTTPException(status_code=400, detail="Translation not complete yet")

    from fastapi.responses import Response

    text = translation.translated_text

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
        _route_log.getLogger(__name__).warning(f"pdf branch entered file_path={book.file_path if book else None}")
        if book and book.file_path and book.file_path.endswith(".pdf"):
            try:
                import os as _os, io as _io
                cache_suffix = f"_translated_{translation.language_id}"
                if cache_variant:
                    cache_suffix = f"{cache_suffix}_{cache_variant}"
                cached_pdf_path = f"/app/storage/{book.file_path.replace('.pdf', f'{cache_suffix}.pdf')}"

                if _os.path.exists(cached_pdf_path) and not refresh_cache:
                    with open(cached_pdf_path, "rb") as f:
                        content = f.read()
                elif translation.translated_text:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether, Image as RLImage
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
                        r'^(INTRODUCTION|NHANGANYAYA|ISINGENISO|ISANDULELO|INTRODUCCI[ÓO]N|UTANGULIZI|INTRODUÇÃO|EINFÜHRUNG)\b',
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

                    _stored_translated_lines = [ln.strip() for ln in translation.translated_text.split("\n") if ln.strip()]
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

                            text_blocks = [tb for tb in text_blocks if _is_toc_block(tb[1])]
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
                    heading_style = ParagraphStyle("H", fontName=reportlab_bold_name, fontSize=14, spaceBefore=14, spaceAfter=4, leading=18, alignment=1, keepWithNext=1, splitLongWords=0)
                    chapter_heading_style = ParagraphStyle("HC", fontName=reportlab_bold_name, fontSize=14, spaceBefore=14, spaceAfter=4, leading=18, alignment=1, keepWithNext=1, splitLongWords=0)
                    intro_title_style = ParagraphStyle("IT", fontName=reportlab_bold_name, fontSize=16, spaceBefore=6, spaceAfter=8, leading=20, alignment=1, keepWithNext=1, splitLongWords=0)
                    subhead_style = ParagraphStyle("SH", fontName=reportlab_bold_name, fontSize=11, spaceBefore=8, spaceAfter=2, leading=14, alignment=TA_LEFT, keepWithNext=1, splitLongWords=0)
                    toc_line_style = ParagraphStyle("TOC", fontName=reportlab_regular_name, fontSize=12, spaceBefore=0, spaceAfter=8, leading=18, alignment=TA_LEFT, splitLongWords=0)
                    body_style = ParagraphStyle("B", fontName=reportlab_regular_name, fontSize=11, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_LEFT, splitLongWords=0)
                    body_style_bold = ParagraphStyle("BB", fontName=reportlab_bold_name, fontSize=11, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_LEFT, splitLongWords=0)
                    reference_style = ParagraphStyle("REF", fontName=reportlab_regular_name, fontSize=8, spaceBefore=1, spaceAfter=1, leading=10, alignment=TA_LEFT, wordWrap="CJK")
                    table_cell_style = ParagraphStyle("TC", fontName=reportlab_regular_name, fontSize=9.5, spaceBefore=0, spaceAfter=0, leading=12, alignment=TA_LEFT, splitLongWords=0)
                    table_header_style = ParagraphStyle("TH", fontName=reportlab_bold_name, fontSize=9.5, spaceBefore=0, spaceAfter=0, leading=12, alignment=TA_LEFT, splitLongWords=0)
                    indent_style = ParagraphStyle("IND", fontName=reportlab_regular_name, fontSize=11,
                        leftIndent=20, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_LEFT, splitLongWords=0)

                    def _new_body_doc(buffer):
                        return SimpleDocTemplate(
                            buffer,
                            pagesize=A4,
                            leftMargin=0.75*inch,
                            rightMargin=0.75*inch,
                            topMargin=0.75*inch,
                            bottomMargin=0.75*inch,
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
                                    previous_sentence_break = bool(_re.search(r"[.!?](?:\"|”|\')?$", previous_text.strip())) if previous_text else False
                                    starts_paragraph = previous_y1 is None or gap > 8 or (gap > 4 and previous_sentence_break)
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
                        if not _re.search(r'[.!?]"?$|[.!?]”$|[.!?]\'$', prev):
                            return True
                        if curr[:1].islower():
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

                    all_translated_lines = translation.translated_text.split("\n")

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

                    def _is_workbook_toc_entry_line(value):
                        candidate = _clean_toc_entry_text(value)
                        if not candidate:
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
                            for idx, line in enumerate(exam_lines):
                                safe_line = _normalize_render_quotes(line).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                                if idx == 0:
                                    workbook_front_story.append(Paragraph(safe_line, heading_style))
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
                            if len(body_toc_entries) > len(toc_entries):
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
                            render_toc_entries = toc_entries
                            import logging as _log
                            _log.getLogger(__name__).warning(f'workbook front matter intro={intro_heading_after_toc!r} toc_count={len(toc_entries)} title={toc_title_text!r}')
                            title_safe = _normalize_render_quotes(toc_title_text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                            workbook_front_story.append(Paragraph(title_safe, heading_style))
                            workbook_front_story.append(Spacer(1, 0.12*inch))
                            toc_block_lines = []
                            workbook_front_story.append(Spacer(1, 0.25*inch))
                            for cleaned in render_toc_entries:
                                safe_line = _normalize_render_quotes(cleaned).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                toc_block_lines.append(safe_line)
                            toc_block = "<br/>".join(toc_block_lines)
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
                        if paragraph_buffer and _re.match(r'^\d+:\d+', p) and not _current_buffer_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")):
                            paragraph_buffer[-1] = paragraph_buffer[-1].rstrip() + " " + p
                        elif paragraph_buffer and _should_join_with_previous(paragraph_buffer[-1], p) and not _current_buffer_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")):
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
                        elif translated_records and p and _should_join_with_previous(translated_records[-1]["text"], p) and not _last_translated_record_looks_like_subheading() and not (current_source and current_source.get("starts_paragraph")) and not _looks_like_source_subheading(p, current_source) and not _looks_like_isolated_translated_heading(p, prev_line, next_line, current_source):
                            translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + p
                        else:
                            paragraph_buffer.append(line)

                    _flush_paragraph_buffer()

                    def _normalize_lettered_prompt_fragments(records):
                        normalized = []
                        idx = 0
                        while idx < len(records):
                            rec = records[idx]
                            text = (rec.get("text") or "").strip()
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
                        chapter_re = _re.compile(
                            r'^(CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s+(?:\d+|[^-–]{1,40})\s*[:\-–]\s+\D',
                            _re.IGNORECASE,
                        )
                        while idx < len(records):
                            rec = records[idx]
                            text = (rec.get("text") or "").strip()
                            if chapter_re.match(text):
                                parts = [text]
                                look = idx + 1
                                while look < len(records) and len(parts) < 4:
                                    next_text = (records[look].get("text") or "").strip()
                                    next_upper = next_text.upper()
                                    words = _re.findall(r"\b[\wÀ-ÿ-]+\b", next_text)
                                    short_heading_tail = (
                                        next_text
                                        and len(next_text) <= 36
                                        and len(words) <= 3
                                        and next_upper == next_text
                                        and not chapter_re.match(next_text)
                                        and not introduction_pattern.match(next_text)
                                        and not _starts_new_body_block(next_text)
                                    )
                                    if not short_heading_tail:
                                        break
                                    parts.append(next_text)
                                    look += 1
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
                            match = _re.match(r'^([A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{5,80})\s+(["“]?[A-ZÀ-Þ]?[a-zà-ÿ].{30,})$', text)
                            if match:
                                heading = _re.sub(r'\s+', ' ', match.group(1)).strip()
                                body = match.group(2).strip()
                                if _valid_inline_allcaps_heading(heading):
                                    split_records.append({**rec, "text": heading})
                                    split_records.append({**rec, "text": body})
                                    continue
                            inline_match = _re.search(
                                r'(?P<prefix>.*[.!?])\s+(?P<head>[A-ZÀ-Þ][A-ZÀ-Þ0-9\s\-–,()/:;&\'’]{2,50})\s+(?P<body>["“]?[A-ZÀ-Þ]?[a-zà-ÿ].{30,})$',
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

                    translated_records = _mark_table_records(_split_inline_lettered_dot_records(_split_inline_chapter_heading_records(_split_inline_allcaps_subheading_records(_split_inline_intro_heading_records(_normalize_lettered_prompt_fragments(_normalize_fragmented_chapter_titles(translated_records)))))))

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

                    def _append_paragraph(text, style, *, keep_together=False):
                        para = Paragraph(text, style)
                        if keep_together:
                            _append_flowable(KeepTogether([para]))
                        else:
                            _append_flowable(para)

                    def _append_heading_paragraph(text, style):
                        # Keep headings/subheads with at least a little following text.
                        # This prevents orphaned prompts at page bottoms while still
                        # allowing the next paragraph to flow naturally if it is long.
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
                        return len(words) <= 28

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

                    for record in translated_records:
                        if record.get("page_break"):
                            if body_sections[-1]:
                                _append_flowable(PageBreak())
                            previous_body_heading = "section"
                            continue
                        p = record["text"].strip()
                        source_record = record["source"]
                        _append_source_page_images((source_record or {}).get("page_number"))
                        force_chapter = bool(record.get("force_chapter"))
                        force_subheading = bool(record.get("force_subheading"))
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

        # .docx translation — translated text as formatted PDF
        elif book and book.file_path and book.file_path.endswith(".docx"):
            try:
                import io as _io, os
                from docx import Document
                from app.services.docx_translation_service import translate_docx_bytes
                from app.tasks.translation_tasks import _batch_translate
                from app.models import Language
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont

                lang = db.query(Language).filter(Language.id == translation.language_id).first()
                src_lang = db.query(Language).filter(Language.id == translation.source_language_id).first()
                target_code = lang.libretranslate_code or lang.code if lang else "sw"
                source_code = src_lang.libretranslate_code or src_lang.code if src_lang else "en"
                docx_font_set = _resolve_font_set(target_code)
                docx_regular_name = "DocxFont"
                docx_bold_name = "DocxFont-Bold"
                docx_regular_file = docx_font_set["overlay_regular_file"]
                docx_bold_file = docx_font_set["overlay_bold_file"]

                cached_pdf_key = book.file_path.replace(".docx", f"_translated_{translation.language_id}.pdf")
                cached_pdf_path = f"/app/storage/{cached_pdf_key}"

                if os.path.exists(cached_pdf_path):
                    with open(cached_pdf_path, "rb") as f:
                        content = f.read()
                else:
                    with open(f"/app/storage/{book.file_path}", "rb") as f:
                        original_docx = f.read()

                    translated_docx = translate_docx_bytes(
                        original_docx,
                        lambda texts: _batch_translate(texts, source_code, target_code)
                    )

                    pdfmetrics.registerFont(TTFont(docx_regular_name, docx_regular_file))
                    pdfmetrics.registerFont(TTFont(docx_bold_name, docx_bold_file))

                    heading_style = ParagraphStyle("h", fontName=docx_bold_name, fontSize=13, spaceAfter=6, leading=16)
                    body_style = ParagraphStyle("b", fontName=docx_regular_name, fontSize=10, spaceAfter=4, leading=14)

                    doc = Document(_io.BytesIO(translated_docx))
                    buf = _io.BytesIO()
                    pdf = SimpleDocTemplate(buf, pagesize=A4,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

                    story = []
                    for para in doc.paragraphs:
                        if not para.text.strip():
                            story.append(Spacer(1, 0.1*inch))
                            continue
                        is_heading = "heading" in (para.style.name.lower() if para.style else "")
                        safe = para.text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                        story.append(Paragraph(safe, heading_style if is_heading else body_style))

                    pdf.build(story)
                    content = buf.getvalue()

                    # Prepend cover page image if available
                    import fitz as _fitz
                    cover_path = f"/app/storage/{book.file_path.replace('.docx', '_cover.png')}"
                    if os.path.exists(cover_path):
                        body_doc = _fitz.open("pdf", content)
                        cover_pix = _fitz.Pixmap(cover_path)
                        cover_page = body_doc.new_page(0, width=cover_pix.width/2, height=cover_pix.height/2)
                        cover_page.insert_image(cover_page.rect, pixmap=cover_pix)
                        final_buf = _io.BytesIO()
                        body_doc.save(final_buf)
                        content = final_buf.getvalue()

                    with open(cached_pdf_path, "wb") as f:
                        f.write(content)

                media_type = "application/pdf"
                filename = f"translation_{translation_id}.pdf"

            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Docx translation failed: {e}")
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

        # Get book cover text if exists
        cover_text = None
        if translation.content_type == "book":
            book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
            cover_text = book.extracted_cover_text if book else None

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
