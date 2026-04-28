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
                import os as _os, io as _io, fitz as _fitz
                cached_pdf_path = f"/app/storage/{book.file_path.replace('.pdf', f'_translated_{translation.language_id}.pdf')}"

                if _os.path.exists(cached_pdf_path):
                    with open(cached_pdf_path, "rb") as f:
                        content = f.read()
                else:
                    from app.models import Language
                    lang = db.query(Language).filter(Language.id == translation.language_id).first()
                    src_lang = db.query(Language).filter(Language.id == translation.source_language_id).first()
                    target_code = lang.libretranslate_code or lang.code if lang else "sw"
                    source_code = src_lang.libretranslate_code or src_lang.code if src_lang else "en"

                    with open(f"/app/storage/{book.file_path}", "rb") as _f:
                        orig_bytes = _f.read()

                    # Use pre-translated lines from DB — no API calls
                    trans_lines = [l for l in translation.translated_text.split("\n") if l.strip()]
                    trans_iter = iter(trans_lines)

                    import pdfplumber
                    fitz_doc = _fitz.open("pdf", orig_bytes)
                    out = _fitz.open()

                    with pdfplumber.open(_io.BytesIO(orig_bytes)) as plumb_pdf:
                        for page_num, (fitz_page, plumb_page) in enumerate(zip(fitz_doc, plumb_pdf.pages)):
                            # Page 1: keep as-is
                            if page_num == 0:
                                out.insert_pdf(fitz_doc, from_page=0, to_page=0)
                                continue

                            pw = plumb_page.width
                            ph = plumb_page.height

                            # Render original page as background image (preserves images/layout)
                            pix = fitz_page.get_pixmap(matrix=_fitz.Matrix(1, 1))
                            new_page = out.new_page(width=fitz_page.rect.width, height=fitz_page.rect.height)
                            new_page.insert_image(new_page.rect, pixmap=pix)

                            # Extract lines with pdfplumber for accurate positions
                            words = plumb_page.extract_words(extra_attrs=["fontname", "size"])
                            if not words:
                                continue

                            # Group words into lines by top position
                            line_groups = {}
                            for w in words:
                                key = round(float(w.get("top", 0)), 1)
                                if key not in line_groups:
                                    line_groups[key] = []
                                line_groups[key].append(w)

                            # Collect all redactions first
                            redact_rects = []
                            line_inserts = []
                            for top, line_words in sorted(line_groups.items()):
                                line_text = " ".join(w["text"] for w in line_words)
                                if not line_text.strip():
                                    continue

                                trans = next(trans_iter, line_text)

                                x0 = min(float(w["x0"]) for w in line_words)
                                x1 = max(float(w["x1"]) for w in line_words)
                                y0 = float(min(w["top"] for w in line_words))
                                y1 = float(max(w["bottom"] for w in line_words))

                                fx0 = fitz_page.rect.width * (x0 / pw)
                                fx1 = fitz_page.rect.width * (x1 / pw)
                                fy0 = fitz_page.rect.height * (y0 / ph)
                                fy1 = fitz_page.rect.height * (y1 / ph)

                                fs = float(line_words[0].get("size", 10))
                                is_bold = "Bold" in str(line_words[0].get("fontname", ""))
                                if True:
                                    fontname = "hebo" if is_bold else "helv"
                                else:
                                    fontname = "hebo" if is_bold else "helv"

                                rect = _fitz.Rect(fx0, fy0, fx1, fy1)
                                redact_rects.append(rect)
                                line_inserts.append((rect, trans, fs, fontname))

                            # Apply all redactions at once
                            for rect in redact_rects:
                                new_page.add_redact_annot(rect, fill=(1,1,1))
                            new_page.apply_redactions()

                            # Insert translated text with proper line spacing and title padding
                            page_w = new_page.rect.width
                            page_h = new_page.rect.height
                            left_margin = 57
                            right_margin = 57
                            top_margin = 50
                            current_y = top_margin

                            # Detect average font size to identify titles
                            avg_fs = sum(fs for _,_,fs,_ in line_inserts) / max(len(line_inserts), 1)

                            for rect, trans, fs, fontname in line_inserts:
                                is_title = fs > avg_fs * 1.2  # larger than average = title/heading
                                line_height = fs * 1.5

                                if current_y + line_height > page_h - 40:
                                    break

                                # Add extra space before titles/headings
                                if is_title and current_y > top_margin:
                                    current_y += fs * 0.8

                                wrap_rect = _fitz.Rect(left_margin, current_y, page_w - right_margin, current_y + line_height * 2)
                                result = new_page.insert_textbox(wrap_rect, trans, fontsize=fs, fontname=fontname, color=(0,0,0), align=3)
                                if result < 0:
                                    new_page.insert_text((left_margin, current_y + fs), trans, fontsize=fs, fontname=fontname, color=(0,0,0))

                                current_y += line_height
                                # Add extra space after titles
                                if is_title:
                                    current_y += fs * 0.4

                        # OCR image blocks (flowcharts)
                        try:
                            import pytesseract
                            from PIL import Image as PILImage
                            from app.tasks.translation_tasks import _batch_translate
                            from app.models import Language
                            lang = db.query(Language).filter(Language.id == translation.language_id).first()
                            src_lang = db.query(Language).filter(Language.id == translation.source_language_id).first()
                            target_code = lang.libretranslate_code or lang.code if lang else "sw"
                            source_code = src_lang.libretranslate_code or src_lang.code if src_lang else "en"

                            for page_num, fitz_page in enumerate(fitz_doc):
                                if page_num == 0:
                                    continue
                                new_page = out[page_num]
                                for b in fitz_page.get_text("dict")["blocks"]:
                                    if b.get("type") != 1:
                                        continue
                                    img_bbox = _fitz.Rect(b["bbox"])
                                    clip_pix = fitz_page.get_pixmap(matrix=_fitz.Matrix(2,2), clip=img_bbox)
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
                                        new_page.add_redact_annot(_fitz.Rect(x0,y0,x1,y1), fill=(1,1,1))
                                        line_data.append((x0, y0, fs, trans))
                                    new_page.apply_redactions()
                                    for x0, y0, fs, trans in line_data:
                                        new_page.insert_text((x0, y0+fs), trans, fontsize=fs, fontname="helv", color=(0,0,0))
                        except Exception:
                            pass

                    buf = _io.BytesIO()
                    out.save(buf, deflate=True, garbage=4, incremental=False)
                    content = buf.getvalue()
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
