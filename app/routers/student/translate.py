import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Exam, User
from app.utils.security import require_role
from app.services.translation_service import TranslationService


router = APIRouter(prefix="/translate", tags=["Translations"])


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
        book = db.query(Book).filter(Book.id == str(translation.content_id)).first()
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
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.units import inch
                    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
                    from reportlab.pdfbase import pdfmetrics
                    from reportlab.pdfbase.ttfonts import TTFont
                    import re as _re
                    import fitz as _fitz
                    import pytesseract
                    from PIL import Image as _PILImage
                    from app.models import Language
                    from app.tasks.translation_tasks import _batch_translate

                    lang = db.query(Language).filter(Language.id == translation.language_id).first()
                    src_lang = db.query(Language).filter(Language.id == translation.source_language_id).first()
                    target_code = lang.libretranslate_code or lang.code if lang else "sw"
                    source_code = src_lang.libretranslate_code or src_lang.code if src_lang else "en"

                    try:
                        pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
                        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
                    except Exception:
                        pass

                    orig_doc = _fitz.open(f"/app/storage/{book.file_path}")
                    last_page = len(orig_doc) - 1

                    chapter_1_pattern = _re.compile(
                        r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*1\b',
                        _re.IGNORECASE,
                    )

                    def _find_chapter_1_page_index():
                        start_idx = max((book.first_content_page or 5) - 1, 0)
                        for idx in range(start_idx, len(orig_doc)):
                            page_text = orig_doc[idx].get_text("text", sort=True)
                            for raw_line in page_text.splitlines():
                                line = raw_line.strip()
                                if not line:
                                    continue
                                if chapter_1_pattern.match(line) and "....." not in line:
                                    return idx
                        return min(6, last_page - 1) + 1

                    def _is_flowchart_page(page):
                        page_text = page.get_text("text", sort=True)
                        upper = page_text.upper()
                        return (
                            "FLOW CHART" in upper
                            or "CHATI INOTEVERA" in upper
                            or "CREDIT HOURS" in upper
                            or "CERTIFICATE IN MINISTRY" in upper
                        )

                    body_start_page_idx = _find_chapter_1_page_index()
                    front_matter_end_idx = max(0, min(body_start_page_idx - 1, last_page - 1))

                    def _extract_text_blocks(page, split_paragraphs: bool = False):
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
                                new_paragraph = gap > 10
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
                                merge_adjacent = (
                                    same_column
                                    and vertical_gap <= 18
                                    and (
                                        (prev_bold or is_bold)
                                        or (prev_incomplete and next_continuation)
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

                    # --- Translate front matter in-place using overlay method ---
                    for page_num in range(front_matter_end_idx + 1):
                        page = orig_doc[page_num]
                        if page_num == 0:
                            continue  # keep cover as-is only

                        # Page 2 (index 1): translate span-by-span preserving exact position/size/color
                        if page_num == 1:
                            spans_to_translate = []
                            for b in page.get_text("dict")["blocks"]:
                                if b.get("type") != 0: continue
                                for line in b["lines"]:
                                    for span in line["spans"]:
                                        t = span["text"].strip()
                                        if not t or t.startswith("©"): continue
                                        spans_to_translate.append(span)
                            if spans_to_translate:
                                texts = [s["text"].strip() for s in spans_to_translate]
                                translated = _batch_translate(texts, source_code, target_code)
                                for span, trans in zip(spans_to_translate, translated):
                                    rect = _fitz.Rect(span["bbox"])
                                    page.add_redact_annot(rect, fill=(1,1,1))
                                page.apply_redactions()
                                for span, trans in zip(spans_to_translate, translated):
                                    # Convert color int to RGB tuple
                                    c = span["color"]
                                    color = ((c >> 16 & 255)/255, (c >> 8 & 255)/255, (c & 255)/255)
                                    fs = span["size"]
                                    fontname = "dejvb" if "Bold" in span.get("font","") else "dejv"
                                    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if "Bold" in span.get("font","") else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                                    # Center the translated text at the same x position
                                    tw = _fitz.get_text_length(trans, fontname="helv", fontsize=fs)
                                    page_cx = page.rect.width / 2
                                    x = page_cx - tw / 2
                                    y = span["origin"][1]
                                    page.insert_text(_fitz.Point(x, y), trans, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
                            continue
                        # Translate text blocks
                        split_front_matter_paragraphs = page_num in {2, 4}
                        text_blocks = _extract_text_blocks(page, split_paragraphs=split_front_matter_paragraphs)
                        if text_blocks:
                            # For TOC page: use stored translation lines by position
                            stored_lookup = {}
                            if page_num == 5 and translation.translated_text:
                                trans_toc_lines = [l.strip() for l in translation.translated_text.split("\n")
                                                   if l.strip() and ("....." in l or "….." in l)]
                                orig_toc_blocks = [(i, orig) for i, (_, orig, _b) in enumerate(text_blocks) if "....." in orig or "….." in orig]
                                for pos, (blk_idx, orig) in enumerate(orig_toc_blocks):
                                    if pos < len(trans_toc_lines):
                                        stored_lookup[blk_idx] = trans_toc_lines[pos]

                            translated = _batch_translate([t for _, t, _ in text_blocks], source_code, target_code)
                            # Override TOC lines with stored translation
                            translated = [stored_lookup.get(i, trans) for i, trans in enumerate(translated)]
                            if page_num == 3 or _is_flowchart_page(page):
                                # Flowchart/examination page: collect ALL redactions (text + OCR image) then apply once
                                all_inserts = []  # (type, args)

                                # Text blocks
                                for (bbox, orig_text, _b), trans in zip(text_blocks, translated):
                                    page.add_redact_annot(_fitz.Rect(bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2), fill=(1,1,1))
                                    rect = _fitz.Rect(bbox)
                                    all_inserts.append(("text", rect, trans, orig_text))

                                # OCR image blocks
                                for b in page.get_text("dict")["blocks"]:
                                    if b.get("type") != 1: continue
                                    img_bbox = _fitz.Rect(b["bbox"])
                                    pix = page.get_pixmap(matrix=_fitz.Matrix(2,2), clip=img_bbox)
                                    img = _PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                                    n = len(ocr_data["text"])
                                    scale_x = img_bbox.width / pix.width
                                    scale_y = img_bbox.height / pix.height
                                    ocr_lines = {}
                                    for i in range(n):
                                        word = ocr_data["text"][i].strip()
                                        try:
                                            conf = float(ocr_data["conf"][i])
                                        except (TypeError, ValueError):
                                            conf = -1
                                        if not word or conf < 20:
                                            continue
                                        key = (ocr_data["block_num"][i], ocr_data["par_num"][i], ocr_data["line_num"][i])
                                        if key not in ocr_lines:
                                            ocr_lines[key] = {"words": [], "x": ocr_data["left"][i], "y": ocr_data["top"][i], "h": ocr_data["height"][i]}
                                        ocr_lines[key]["words"].append(word)
                                    if ocr_lines:
                                        line_keys = list(ocr_lines.keys())
                                        ocr_texts = [" ".join(ocr_lines[k]["words"]) for k in line_keys]
                                        ocr_translated = _batch_translate(ocr_texts, source_code, target_code)
                                        for k, t in zip(line_keys, ocr_translated):
                                            x0 = img_bbox.x0 + ocr_lines[k]["x"]*scale_x
                                            y0 = img_bbox.y0 + ocr_lines[k]["y"]*scale_y
                                            fs = max(ocr_lines[k]["h"]*scale_y*0.85, 8)
                                            page.add_redact_annot(_fitz.Rect(x0, y0, img_bbox.x1, y0 + fs*1.3), fill=(1,1,1))
                                            all_inserts.append(("ocr", x0, y0, fs, t))

                                # Single apply_redactions call
                                page.apply_redactions()

                                # Now insert all translated text
                                def _is_flowchart_label(orig_text, rect):
                                    text = (orig_text or "").strip()
                                    upper = text.upper()
                                    if not text:
                                        return False
                                    if rect.y0 < page.rect.height * 0.42:
                                        return False
                                    if len(text) <= 40:
                                        return True
                                    chart_markers = [
                                        "CERTIFICATE",
                                        "DIPLOMA",
                                        "BACHELOR",
                                        "MASTERS",
                                        "DOCTOR",
                                        "MINISTRY",
                                        "PHILOSOPHY",
                                        "CREDIT HOURS",
                                        "CREDITS",
                                        "CREDIT",
                                        "HOURS",
                                    ]
                                    if any(marker in upper for marker in chart_markers):
                                        return True
                                    if _re3.search(r"\b\d+\s+(CREDIT|CREDITS|HOURS)\b", upper):
                                        return True
                                    if _re3.fullmatch(r"[=0-9A-Z\s]+", upper) and len(text) <= 60:
                                        return True
                                    return False

                                def _insert_chart_label(rect, trans):
                                    trans_clean = (trans or "").strip()
                                    is_credit_value = bool(
                                        _re3.match(
                                            r"^(?:=\s*)?\d+\s+.+",
                                            trans_clean,
                                            _re3.IGNORECASE,
                                        )
                                    )
                                    is_short_value = len(trans_clean) <= 28
                                    if is_credit_value or is_short_value:
                                        rect = _fitz.Rect(rect.x0, rect.y0 - 1, rect.x1, rect.y1 + 4)
                                        align = 1
                                    else:
                                        rect = _fitz.Rect(rect.x0 - 2, rect.y0 - 1, rect.x1 + 8, rect.y1 + 6)
                                        align = 0
                                    for fs in [10, 9, 8, 7]:
                                        result = page.insert_textbox(
                                            rect,
                                            trans_clean,
                                            fontsize=fs,
                                            fontname="dejv",
                                            fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                            color=(0, 0, 0),
                                            align=align,
                                        )
                                        if result >= -2:
                                            return True
                                    return False

                                all_inserts.sort(
                                    key=lambda item: item[1].y0 if item[0] == "text" else item[2]
                                )
                                p3_y_cursor = None
                                chart_value_rects = []
                                chart_title_rects = []
                                for item in all_inserts:
                                    if item[0] == "text":
                                        _, rect, trans, orig_text = item
                                        if not trans.strip(): continue
                                        import re as _re3
                                        if rect.y0 > 230 and rect.x0 > 220 and rect.x1 < 360:
                                            txt = trans.strip()
                                            if _re3.match(r"^\d+\s+\S+", txt):
                                                chart_value_rects.append((rect, txt))
                                            elif len(txt) <= 40 and not _re3.match(r"^[=0-9]", txt):
                                                chart_title_rects.append((rect, txt))
                                        if _is_flowchart_label(orig_text, rect):
                                            _insert_chart_label(rect, trans)
                                            continue
                                        y_start = p3_y_cursor if p3_y_cursor is not None else rect.y0
                                        y_start = max(y_start, rect.y0)
                                        # Keep the page-4 warning sentence as one caps line.
                                        source_has_warning = "PLEASE ENSURE" in orig_text.upper()
                                        caps_match = _re3.search(r'\b[A-Z]{3,}(?:\s+[A-Z]{2,})+\.', trans)
                                        if source_has_warning:
                                            sentence_parts = [p.strip() for p in _re3.split(r'(?<=[.!?])\s+', trans.strip()) if p.strip()]
                                            if len(sentence_parts) >= 2:
                                                before = " ".join(sentence_parts[:-1]).strip()
                                                warning = sentence_parts[-1].strip()
                                                parts = [p for p in [before, warning] if p]
                                            elif caps_match:
                                                before = trans[:caps_match.start()].strip()
                                                warning = caps_match.group(0).strip()
                                                parts = [p for p in [before, warning] if p]
                                            else:
                                                parts = [trans]
                                        elif caps_match:
                                            before = trans[:caps_match.start()].strip()
                                            warning = caps_match.group(0).strip()
                                            parts = [p for p in [before, warning] if p]
                                        else:
                                            parts = [trans]
                                        for part in parts:
                                            part = part.strip()
                                            if not part: continue
                                            is_caps_line = (part == part.upper() and len(part) > 10) or (source_has_warning and part == parts[-1])
                                            fn = "dejvb" if is_caps_line else "dejv"
                                            ff = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if is_caps_line else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                                            expanded = _fitz.Rect(rect.x0, y_start, page.rect.x1 - 57, page.rect.y1 - 20)
                                            if y_start >= page.rect.y1 - 25 or not expanded.is_valid: break
                                            for fs in [10, 9, 8, 7]:
                                                result = page.insert_textbox(expanded, part, fontsize=fs, fontname=fn, fontfile=ff, color=(0,0,0))
                                                if result >= 0:
                                                    tw = _fitz.get_text_length(part, fontname="helv", fontsize=fs)
                                                    n_lines = max(1, -(-int(tw) // max(int(expanded.width), 1)))
                                                    y_start += n_lines * fs * 1.3 + fs * 0.5
                                                    break
                                            else:
                                                y_start += 15
                                        p3_y_cursor = y_start
                                    else:
                                        _, x0, y0, fs, t = item
                                        page.insert_text(_fitz.Point(x0, y0+fs), t, fontsize=fs, fontname="dejv", fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", color=(0,0,0))

                                chart_value_rects.sort(key=lambda item: item[0].y0)
                                chart_title_rects.sort(key=lambda item: item[0].y0)
                                if len(chart_value_rects) >= 7 and len(chart_title_rects) >= 7:
                                    cumulative_labels = [
                                        "30 Credit Hours",
                                        "= 60 Credit Hours",
                                        "120 Credit Hours",
                                        "136 Credit Hours",
                                        "= 156 Credit Hours",
                                        "= 192 Credit Hours",
                                        "= 228 Credit Hours",
                                    ]
                                    translated_labels = _batch_translate(cumulative_labels, source_code, target_code)
                                    connector_positions = []
                                    for idx, (value_rect, _txt) in enumerate(chart_value_rects[:7]):
                                        if idx + 1 < len(chart_title_rects):
                                            next_title_rect = chart_title_rects[idx + 1][0]
                                            y_mid = (value_rect.y1 + next_title_rect.y0) / 2
                                        else:
                                            y_mid = value_rect.y1 + 18
                                        connector_positions.append(y_mid)

                                    for idx, (y_mid, label) in enumerate(zip(connector_positions, translated_labels)):
                                        if idx == 0:
                                            # The first right-side connector survives as a baked graphic strip.
                                            # Wipe a wider fixed band and redraw the translated label explicitly.
                                            clear_rect = _fitz.Rect(392, 270, 520, 291)
                                            text_point = _fitz.Point(398, 284)
                                        else:
                                            clear_rect = _fitz.Rect(320, y_mid - 13, 505, y_mid + 13)
                                            text_point = _fitz.Point(338, y_mid + 3)
                                        page.draw_rect(
                                            clear_rect,
                                            color=(1, 1, 1),
                                            fill=(1, 1, 1),
                                            overlay=True,
                                        )
                                        page.insert_text(
                                            text_point,
                                            label,
                                            fontsize=9,
                                            fontname="dejv",
                                            fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                            color=(0, 0, 0),
                                            overlay=True,
                                        )

                                # Force-replace the first right-side connector label even if
                                # chart row detection misses it. This is the stubborn strip that
                                # survives as a graphic on page 4 in some cached builds.
                                first_connector_label = _batch_translate(
                                    ["30 Credit Hours"], source_code, target_code
                                )[0]
                                first_connector_rect = _fitz.Rect(392, 270, 520, 291)
                                page.draw_rect(
                                    first_connector_rect,
                                    color=(1, 1, 1),
                                    fill=(1, 1, 1),
                                    overlay=True,
                                )
                                page.insert_text(
                                    _fitz.Point(384, 284),
                                    first_connector_label,
                                    fontsize=9,
                                    fontname="dejv",
                                    fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                    color=(0, 0, 0),
                                    overlay=True,
                                )
                            else:
                                for (bbox, _, _b), trans in zip(text_blocks, translated):
                                    page.add_redact_annot(_fitz.Rect(bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2), fill=(1,1,1))
                                page.apply_redactions()
                                # Track y position per bbox to stack sub-blocks vertically
                                y_cursor = {}
                                for (bbox, orig_text, is_bold), trans in zip(text_blocks, translated):
                                    rect = _fitz.Rect(bbox)
                                    # TOC page (index 5): expand dotted lines to full page width
                                    if page_num == 5 and ("....." in orig_text or "….." in orig_text):
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
                                        page.insert_text(_fitz.Point(left_x, y), title, fontsize=fs, fontname="dejv", fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", color=(0,0,0))
                                        page.insert_text(_fitz.Point(left_x + title_w, y), dots, fontsize=fs, fontname="helv", color=(0,0,0))
                                        if pagenum:
                                            page.insert_text(_fitz.Point(right_x - num_w, y), pagenum, fontsize=fs, fontname="helv", color=(0,0,0))
                                    else:
                                        front_matter_body = split_front_matter_paragraphs and len(orig_text) > 40
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
                                        use_bold = is_bold and not force_plain
                                        fontfile_use = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if use_bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                                        fontname_use = "dejvb" if use_bold else "dejv"
                                        fs_use = 13 if use_bold else 10
                                        bbox_key = (round(bbox[0]), round(bbox[1]))
                                        y_start = y_cursor.get(bbox_key, rect.y0)
                                        front_matter_heading = split_front_matter_paragraphs and use_bold and len(orig_text) <= 80
                                        render_x1 = page.rect.x1 - 57 if (front_matter_body or front_matter_heading) else rect.x1
                                        render_rect = _fitz.Rect(rect.x0, y_start, render_x1, page.rect.y1 - 20)
                                        for fs in [fs_use, fs_use-2, 7]:
                                            result = page.insert_textbox(render_rect, trans, fontsize=fs, fontname=fontname_use, fontfile=fontfile_use, color=(0,0,0))
                                            if result >= 0:
                                                # Estimate height used and advance cursor
                                                tw = _fitz.get_text_length(trans, fontname="helv", fontsize=fs)
                                                n_lines = max(1, -(-int(tw) // max(int(render_rect.width), 1)))
                                                gap_after = fs * 1.5 if use_bold else fs * 0.6
                                                y_cursor[bbox_key] = y_start + n_lines * fs * 1.3 + gap_after
                                                break
                    # --- Build body from stored translation using original PDF line styles ---
                    heading_style = ParagraphStyle("H", fontName="DejaVu-Bold", fontSize=14, spaceBefore=14, spaceAfter=4, leading=18, alignment=TA_LEFT)
                    subhead_style = ParagraphStyle("SH", fontName="DejaVu-Bold", fontSize=11, spaceBefore=8, spaceAfter=2, leading=14, alignment=TA_LEFT)
                    body_style = ParagraphStyle("B", fontName="DejaVu", fontSize=11, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_JUSTIFY)
                    body_style_bold = ParagraphStyle("BB", fontName="DejaVu-Bold", fontSize=11, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_JUSTIFY)
                    indent_style = ParagraphStyle("IND", fontName="DejaVu", fontSize=11,
                        leftIndent=20, spaceBefore=2, spaceAfter=2, leading=15)

                    body_buf = _io.BytesIO()
                    body_doc_rl = SimpleDocTemplate(body_buf, pagesize=A4,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

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

                    def _source_line_records():
                        records = []
                        start_page = min(max(body_start_page_idx, 0), len(orig_doc))

                        def _normalize_line(value):
                            return _re.sub(r"\s+", " ", value or "").strip()

                        for source_page_num in range(start_page, len(orig_doc)):
                            page = orig_doc[source_page_num]
                            page_dict = page.get_text("dict", sort=True)
                            styled_lines = []
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
                                    styled_lines.append({
                                        "text": styled_text,
                                        "normalized": _normalize_line(styled_text),
                                        "bold": _line_is_bold(spans),
                                        "size": max(float(s.get("size", 11)) for s in spans),
                                    })

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
                                    matched_style = {"bold": False, "size": 11}
                                records.append({
                                    "page_number": source_page_num + 1,
                                    "text": original_text,
                                    "bold": matched_style["bold"],
                                    "size": matched_style["size"],
                                })
                        return records

                    def _skip_body_record(record):
                        original = record["text"].strip()
                        if original.startswith("CC101 Christian Foundations"):
                            return True
                        if _re.fullmatch(r"\d+", original):
                            return True
                        return False

                    # Pre-process: join continuation lines (scripture refs split across lines)
                    raw_lines = translation.translated_text.split("\n")
                    source_records = _source_line_records()
                    source_iter = iter(source_records)
                    translated_records = []
                    for line in raw_lines:
                        p = line.strip()
                        source_record = next(source_iter, None) if p else None
                        if p and not source_record:
                            source_record = {
                                "page_number": 0,
                                "text": "",
                                "bold": False,
                                "size": 11,
                            }
                        # Continuation: starts with verse ref like "44:8" or "10:14" or "13:20"
                        if translated_records and p and _re.match(r'^\d+:\d+', p):
                            translated_records[-1]["text"] = translated_records[-1]["text"].rstrip() + " " + p
                        else:
                            translated_records.append({
                                "text": line,
                                "source": source_record,
                            })

                    story = []
                    skip_toc = False
                    reached_chapter_1 = False
                    for record in translated_records:
                        p = record["text"].strip()
                        source_record = record["source"]
                        # Skip TOC section
                        if not reached_chapter_1 and p and ("TABLE OF CONTENTS" in p.upper() or "YALIYOMO" in p.upper() or "ZVIRI MUKATI" in p.upper() or "TABLE DES" in p.upper() or "ÍNDICE" in p.upper() or "JEDWALI" in p.upper() or "ATỌKA" in p.upper()):
                            skip_toc = True
                            continue
                        if skip_toc:
                            if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*\d+', p, _re.IGNORECASE) and "....." not in p:
                                skip_toc = False
                                reached_chapter_1 = True
                            else:
                                continue
                        if not reached_chapter_1:
                            if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*\d+', p, _re.IGNORECASE) and "....." not in p:
                                reached_chapter_1 = True
                            else:
                                continue
                        if source_record and _skip_body_record(source_record):
                            continue
                        if not p:
                            story.append(Spacer(1, 0.05*inch))
                            continue
                        safe = p.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                        is_source_bold = bool(source_record and source_record["bold"])
                        source_size = float(source_record["size"] if source_record else 11)
                        # Pattern-based overrides (reliable regardless of source pairing)
                        is_chapter = bool(_re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ)\s*\d+', p, _re.IGNORECASE))
                        is_allcaps = len(p) < 80 and p.isupper() and len(p) > 3
                        is_lettered = bool(_re.match(r'^[a-zA-Z]\) .{2,}', p) and len(p) < 120)
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
                        if is_chapter:
                            story.append(Spacer(1, 0.15*inch))
                            story.append(Paragraph(safe, heading_style))
                            story.append(Spacer(1, 0.08*inch))
                        elif is_allcaps or is_lettered or safe_source_bold:
                            story.append(Spacer(1, 0.05*inch))
                            story.append(Paragraph(safe, subhead_style))
                        elif _re.match(r'^\d+\. ', p):
                            content = _re.sub(r'^\d+\.\s*', '', p)
                            has_caps = bool(_re.search(r'[A-Z]{3,}', content))
                            is_title = len(content) <= 50 and not _re.search(r'\b(is|are|was|has|have)\b', content, _re.IGNORECASE)
                            story.append(Paragraph(safe, subhead_style if (is_title or has_caps) else body_style))
                        elif _re.match(r'^\([ivxabc]+\)', p):
                            story.append(Paragraph(safe, indent_style))
                        else:
                            story.append(Paragraph(safe, body_style))
                    try:
                        body_doc_rl.build(story)
                        body_bytes = body_buf.getvalue()
                        # Repair PDF via fitz to avoid malformed page tree on merge
                        _repair = _fitz.open("pdf", body_bytes)
                        _rbuf = _io.BytesIO()
                        _repair.save(_rbuf, garbage=4, deflate=True)
                        body_bytes = _rbuf.getvalue()
                    except Exception as _e:
                        import logging as _log
                        _log.getLogger(__name__).warning(f"ReportLab build failed: {_e}")
                        body_bytes = b""

                    # --- Translate page 100 (index 99) in-place using overlay ---
                    if last_page >= 99:
                        p100 = orig_doc[last_page - 1]
                        p100_blocks = []
                        for b in p100.get_text("dict")["blocks"]:
                            if b.get("type") != 0: continue
                            text = "".join(s["text"] for l in b["lines"] for s in l["spans"]).strip()
                            if not text or text.startswith("©"): continue
                            if len(text) <= 150 and ("@" in text or "www." in text): continue
                            p100_blocks.append((b["bbox"], text))
                        if p100_blocks:
                            translated_p100 = _batch_translate([t for _, t in p100_blocks], source_code, target_code)
                            for (bbox, _), trans in zip(p100_blocks, translated_p100):
                                p100.add_redact_annot(_fitz.Rect(bbox), fill=(1,1,1))
                            p100.apply_redactions()
                            for (bbox, _), trans in zip(p100_blocks, translated_p100):
                                rect = _fitz.Rect(bbox)
                                for fs in [10, 8, 7]:
                                    if p100.insert_textbox(rect, trans, fontsize=fs, fontname="dejv", fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", color=(0,0,0)) >= 0:
                                        break

                    # --- Assemble: translated front matter + body + last 2 pages ---
                    mod_buf = _io.BytesIO()
                    orig_doc.save(mod_buf)
                    mod_doc = _fitz.open("pdf", mod_buf.getvalue())

                    out = _fitz.open()
                    out.insert_pdf(mod_doc, from_page=0, to_page=front_matter_end_idx)
                    if body_bytes:
                        body_fitz = _fitz.open("pdf", body_bytes)
                        out.insert_pdf(body_fitz)
                    if last_page >= body_start_page_idx:
                        out.insert_pdf(orig_doc, from_page=max(last_page - 1, body_start_page_idx), to_page=last_page)

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

                        _font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                        _font_bold    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

                        for (bbox, orig_text, fontsize, is_bold), trans in zip(text_blocks, translated):
                            rect = _fitz.Rect(bbox)
                            fontfile = _font_bold if is_bold else _font_regular
                            fontname = "dejvb" if is_bold else "dejv"
                            fs = fontsize if fontsize > 13 else 11.7

                            # TOC lines: title left, dot leaders, page number flush right
                            if "....." in orig_text or "….." in orig_text:
                                import re as _re
                                toc_fs = 9.0
                                left_x, right_x = 57.7, 537.35
                                available_w = right_x - left_x

                                # Extract page number from original text
                                m = _re.search(r'(\d+)\s*$', orig_text.rstrip('.').strip())
                                pagenum = m.group(1) if m else ""

                                # Strip dots and page number from translated text to get clean title
                                title = _re.sub(r'\.{2,}.*', '', trans).strip()
                                title = _re.sub(r'\s*\d+\s*$', '', title).strip()

                                # Measure title and page number widths
                                title_w = _fitz.get_text_length(title, fontname="helv", fontsize=toc_fs)
                                num_w = _fitz.get_text_length(pagenum, fontname="helv", fontsize=toc_fs) if pagenum else 0
                                dot_w = _fitz.get_text_length(".", fontname="helv", fontsize=toc_fs)

                                # Fill middle with dots
                                gap = available_w - title_w - num_w
                                dot_count = max(int(gap / dot_w) - 1, 3)
                                dots = "." * dot_count

                                y = rect.y1 - 1
                                page.insert_text(_fitz.Point(left_x, y), title, fontsize=toc_fs, fontname=fontname, fontfile=fontfile, color=(0,0,0))
                                page.insert_text(_fitz.Point(left_x + title_w, y), dots, fontsize=toc_fs, fontname="helv", color=(0,0,0))
                                if pagenum:
                                    page.insert_text(_fitz.Point(right_x - num_w, y), pagenum, fontsize=toc_fs, fontname="helv", color=(0,0,0))
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

                        # OCR flowchart images
                        try:
                            import pytesseract
                            from PIL import Image as PILImage
                            from app.tasks.translation_tasks import _batch_translate
                            for b in blocks:
                                if b.get("type") != 1:
                                    continue
                                img_bbox = _fitz.Rect(b["bbox"])
                                clip_pix = page.get_pixmap(matrix=_fitz.Matrix(2,2), clip=img_bbox)
                                img = PILImage.frombytes("RGB", [clip_pix.width, clip_pix.height], clip_pix.samples)
                                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                                n = len(ocr_data["text"])
                                scale_x = img_bbox.width / clip_pix.width
                                scale_y = img_bbox.height / clip_pix.height
                                ocr_lines = {}
                                for i in range(n):
                                    word = ocr_data["text"][i].strip()
                                    if not word or int(ocr_data["conf"][i]) < 50:
                                        continue
                                    key = (ocr_data["block_num"][i], ocr_data["par_num"][i], ocr_data["line_num"][i])
                                    if key not in ocr_lines:
                                        ocr_lines[key] = {"words":[], "x":ocr_data["left"][i], "y":ocr_data["top"][i], "w":0, "h":ocr_data["height"][i]}
                                    ocr_lines[key]["words"].append(word)
                                    ocr_lines[key]["w"] = max(ocr_lines[key]["w"], ocr_data["left"][i]+ocr_data["width"][i]-ocr_lines[key]["x"])
                                if not ocr_lines:
                                    continue
                                line_keys = list(ocr_lines.keys())
                                texts = [" ".join(ocr_lines[k]["words"]) for k in line_keys]
                                translated_lines = _batch_translate(texts, source_code, target_code)
                                line_data = []
                                for key, trans in zip(line_keys, translated_lines):
                                    line = ocr_lines[key]
                                    x0 = img_bbox.x0 + line["x"]*scale_x
                                    y0 = img_bbox.y0 + line["y"]*scale_y
                                    x1 = img_bbox.x0 + (line["x"]+line["w"])*scale_x
                                    y1 = img_bbox.y0 + (line["y"]+line["h"])*scale_y
                                    fs = max((y1-y0)*0.85, 8)
                                    line_data.append((x0, y0, fs, trans))
                                # Keep image, white-out each text line area and overlay translation
                                for x0, y0, fs, trans in line_data:
                                    page.add_redact_annot(_fitz.Rect(x0, y0, img_bbox.x1, y0 + fs * 1.3), fill=(1,1,1))
                                page.apply_redactions()
                                for x0, y0, fs, trans in line_data:
                                    page.insert_text(
                                        _fitz.Point(x0, y0 + fs), trans,
                                        fontsize=fs, fontname="dejv",
                                        fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                        color=(0,0,0)
                                    )
                        except Exception:
                            pass

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

                    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
                    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

                    heading_style = ParagraphStyle("h", fontName="DejaVu-Bold", fontSize=13, spaceAfter=6, leading=16)
                    body_style = ParagraphStyle("b", fontName="DejaVu", fontSize=10, spaceAfter=4, leading=14)

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

        pdfmetrics.registerFont(
            TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            )
        )

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
            fontName="DejaVu-Bold",
            fontSize=16,
            spaceAfter=12,
            textColor=colors.black,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            fontName="DejaVu-Bold",
            fontSize=12,
            spaceAfter=6,
            textColor=colors.darkblue,
        )
        body_style = ParagraphStyle(
            "CustomBody", fontName="DejaVu", fontSize=10, spaceAfter=6, leading=14
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

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
