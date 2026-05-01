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
                cached_pdf_path = f"/app/storage/{book.file_path.replace('.pdf', f'_translated_{translation.language_id}.pdf')}"

                if _os.path.exists(cached_pdf_path):
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

                    # --- Translate pages 1-6 in-place using overlay method ---
                    for page_num in range(min(6, last_page - 1)):
                        page = orig_doc[page_num]
                        if page_num == 0:
                            continue  # keep cover as-is
                        # Translate text blocks
                        text_blocks = []
                        for b in page.get_text("dict")["blocks"]:
                            if b.get("type") != 0: continue
                            text = "".join(s["text"] for l in b["lines"] for s in l["spans"]).strip()
                            if not text or text.startswith("©"): continue
                            if len(text) <= 150 and ("@" in text or "www." in text): continue
                            text_blocks.append((b["bbox"], text))
                        if text_blocks:
                            translated = _batch_translate([t for _, t in text_blocks], source_code, target_code)
                            for (bbox, _), trans in zip(text_blocks, translated):
                                rect = _fitz.Rect(bbox)
                                page.add_redact_annot(rect, fill=(1,1,1))
                            page.apply_redactions()
                            for (bbox, orig_text), trans in zip(text_blocks, translated):
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
                                    for fs in [10, 8, 7]:
                                        if page.insert_textbox(rect, trans, fontsize=fs, fontname="dejv", fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", color=(0,0,0)) >= 0:
                                            break
                        # Translate flowchart image (page 4 = index 3)
                        if page_num == 3:
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
                                    if not word or int(ocr_data["conf"][i]) < 50: continue
                                    key = (ocr_data["block_num"][i], ocr_data["par_num"][i], ocr_data["line_num"][i])
                                    if key not in ocr_lines:
                                        ocr_lines[key] = {"words": [], "x": ocr_data["left"][i], "y": ocr_data["top"][i], "h": ocr_data["height"][i]}
                                    ocr_lines[key]["words"].append(word)
                                if ocr_lines:
                                    line_keys = list(ocr_lines.keys())
                                    texts = [" ".join(ocr_lines[k]["words"]) for k in line_keys]
                                    translated_lines = _batch_translate(texts, source_code, target_code)
                                    line_data = [(img_bbox.x0 + ocr_lines[k]["x"]*scale_x, img_bbox.y0 + ocr_lines[k]["y"]*scale_y, max(ocr_lines[k]["h"]*scale_y*0.85, 8), t) for k, t in zip(line_keys, translated_lines)]
                                    # Draw white box behind each line then insert translated text on top
                                    for x0, y0, fs, t in line_data:
                                        page.draw_rect(_fitz.Rect(x0, y0, img_bbox.x1, y0 + fs*1.3), color=(1,1,1), fill=(1,1,1))
                                        page.insert_text(_fitz.Point(x0, y0+fs), t, fontsize=fs, fontname="dejv", fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", color=(0,0,0))

                    # --- Build body from stored translation (skip TOC lines) ---
                    heading_style = ParagraphStyle("H", fontName="DejaVu-Bold", fontSize=14, spaceBefore=14, spaceAfter=4, leading=18, alignment=TA_LEFT)
                    subhead_style = ParagraphStyle("SH", fontName="DejaVu-Bold", fontSize=11, spaceBefore=8, spaceAfter=2, leading=14, alignment=TA_LEFT)
                    body_style = ParagraphStyle("B", fontName="DejaVu", fontSize=11, spaceBefore=2, spaceAfter=2, leading=15, alignment=TA_JUSTIFY)

                    body_buf = _io.BytesIO()
                    body_doc_rl = SimpleDocTemplate(body_buf, pagesize=A4,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)
                    story = []
                    skip_toc = False
                    reached_chapter_1 = False
                    for para in translation.translated_text.split("\n"):
                        p = para.strip()
                        # Detect and skip the entire TOC section
                        if not reached_chapter_1 and ("TABLE OF CONTENTS" in p.upper() or "YALIYOMO" in p.upper() or "ZVIRI MUKATI" in p.upper() or "TABLE DES" in p.upper() or "ÍNDICE" in p.upper() or "JEDWALI" in p.upper()):
                            skip_toc = True
                            continue
                        if skip_toc:
                            # End of TOC: first chapter heading WITHOUT dot leaders
                            if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO|NHANGANYAYA|INTRODUCTION|UTANGULIZI)\b', p, _re.IGNORECASE) and "....." not in p:
                                skip_toc = False
                                # Don't include intro pages — only start from Chapter 1
                                if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO)\s+\d+', p, _re.IGNORECASE):
                                    reached_chapter_1 = True
                            continue
                        # Skip everything before Chapter 1
                        if not reached_chapter_1:
                            if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO)\s+\d+', p, _re.IGNORECASE) and "....." not in p:
                                reached_chapter_1 = True
                            else:
                                continue
                        if not p:
                            story.append(Spacer(1, 0.05*inch))
                            continue
                        safe = p.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                        if _re.match(r'^(CHAPTER|SURA|CHITSAUKO|CHAPITRE|CAPÍTULO)\s+\d+', p, _re.IGNORECASE):
                            story.append(Paragraph(safe, heading_style))
                        elif len(p) < 80 and (p.isupper() or p.rstrip().endswith(":")):
                            story.append(Paragraph(safe, subhead_style))
                        else:
                            story.append(Paragraph(safe, body_style))
                    body_doc_rl.build(story)
                    body_bytes = body_buf.getvalue()

                    # --- Assemble: first 4 pages (translated in-place) + body + last 2 pages ---
                    mod_buf = _io.BytesIO()
                    orig_doc.save(mod_buf)
                    mod_doc = _fitz.open("pdf", mod_buf.getvalue())

                    out = _fitz.open()
                    out.insert_pdf(mod_doc, from_page=0, to_page=min(5, last_page))
                    body_fitz = _fitz.open("pdf", body_bytes)
                    out.insert_pdf(body_fitz)
                    if last_page >= 6:
                        out.insert_pdf(orig_doc, from_page=max(last_page-1, 6), to_page=last_page)

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
