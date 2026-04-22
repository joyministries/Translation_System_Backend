import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Exam, User
from app.utils.security import require_role
from app.services.translation_service import TranslationService


router = APIRouter(prefix="/translate", tags=["Translations"])


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
                    from reportlab.lib.pagesizes import A4
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.units import inch
                    from reportlab.pdfbase import pdfmetrics
                    from reportlab.pdfbase.ttfonts import TTFont

                    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
                    body_style = ParagraphStyle("b", fontName="DejaVu", fontSize=10, spaceAfter=4, leading=14)

                    # Build translated text pages
                    buf = _io.BytesIO()
                    pdf = SimpleDocTemplate(buf, pagesize=A4,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)
                    story = []
                    for line in translation.translated_text.split("\n"):
                        if line.strip():
                            safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                            story.append(Paragraph(safe, body_style))
                        else:
                            story.append(Spacer(1, 0.08*inch))
                    pdf.build(story)

                    # Prepend first 4 pages from original PDF
                    orig_path = f"/app/storage/{book.file_path}"
                    text_doc = _fitz.open("pdf", buf.getvalue())
                    first_content = book.first_content_page or 5
                    pages_to_keep = first_content - 1

                    if _os.path.exists(orig_path) and pages_to_keep > 0:
                        orig_doc = _fitz.open(orig_path)
                        out = _fitz.open()
                        # Insert original first pages
                        out.insert_pdf(orig_doc, from_page=0, to_page=min(pages_to_keep-1, len(orig_doc)-1))
                        # Append translated text pages
                        out.insert_pdf(text_doc)
                        final_buf = _io.BytesIO()
                        out.save(final_buf)
                        content = final_buf.getvalue()
                    else:
                        content = buf.getvalue()

                    with open(cached_pdf_path, "wb") as f:
                        f.write(content)

                filename = f"translation_{translation_id}.pdf"
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Layout PDF failed, falling back: {e}")
                content = None  # fall through to plain PDF

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
