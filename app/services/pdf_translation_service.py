import io
import logging
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def translate_pdf_preserving_layout(
    file_path: str,
    translate_fn,  # callable(text: str) -> str
) -> bytes:
    """
    Translate a PDF while preserving layout:
    - Page 1: keep exactly as-is, only translate footer text overlay
    - Page 2+: OCR text, translate, overlay on original page image
    """
    doc = fitz.open(file_path)
    out = fitz.open()

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Render page to image at 2x resolution for quality
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if page_num == 0:
            # Cover page — keep as-is, just add translated footer
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pix)

            # Add small translated footer at bottom
            try:
                cover_text = page.get_text().strip()
                if not cover_text:
                    # Try OCR on bottom 15% of cover for footer
                    h = img.height
                    footer_img = img.crop((0, int(h * 0.85), img.width, h))
                    cover_text = pytesseract.image_to_string(footer_img).strip()

                if cover_text:
                    translated_footer = translate_fn(cover_text[:200])
                    footer_rect = fitz.Rect(
                        20, page.rect.height - 30,
                        page.rect.width - 20, page.rect.height - 10
                    )
                    new_page.insert_textbox(
                        footer_rect,
                        translated_footer,
                        fontsize=7,
                        color=(0.3, 0.3, 0.3),
                        align=1,
                    )
            except Exception as e:
                logger.warning(f"Cover footer translation failed: {e}")

        else:
            # Body pages — OCR, translate, overlay on original
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pix)

            try:
                # Try native text first (faster)
                native_text = page.get_text("dict")
                has_native = any(
                    span["text"].strip()
                    for block in native_text.get("blocks", [])
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                )

                if has_native:
                    _overlay_native_text(page, new_page, translate_fn)
                else:
                    _overlay_ocr_text(img, pix, new_page, page, translate_fn)

            except Exception as e:
                logger.warning(f"Page {page_num} translation failed: {e}")

    buf = io.BytesIO()
    out.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _overlay_native_text(src_page, new_page, translate_fn):
    """For text-based PDFs: redact original text and insert translation."""
    text_dict = src_page.get_text("dict")
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            line_text = " ".join(s["text"] for s in line.get("spans", []) if s["text"].strip())
            if not line_text.strip():
                continue
            span = line["spans"][0]
            bbox = fitz.Rect(line["bbox"])
            fontsize = max(span.get("size", 10), 6)
            try:
                translated = translate_fn(line_text)
                new_page.add_redact_annot(bbox, fill=(1, 1, 1))
                new_page.apply_redactions()
                new_page.insert_textbox(bbox, translated, fontsize=fontsize, color=(0, 0, 0))
            except Exception:
                pass


def _overlay_ocr_text(img, pix, new_page, src_page, translate_fn):
    """For scanned PDFs: OCR then overlay translated text."""
    scale_x = src_page.rect.width / pix.width
    scale_y = src_page.rect.height / pix.height

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    n = len(data["text"])

    for i in range(n):
        text = data["text"][i]
        if not text.strip() or int(data.get("conf", [0] * n)[i]) < 40:
            continue

        x = data["left"][i] * scale_x
        y = data["top"][i] * scale_y
        w = data["width"][i] * scale_x
        h = data["height"][i] * scale_y
        bbox = fitz.Rect(x, y, x + w, y + h)
        fontsize = max(h * 0.7, 6)

        try:
            translated = translate_fn(text)
            new_page.add_redact_annot(bbox, fill=(1, 1, 1))
            new_page.apply_redactions()
            new_page.insert_textbox(bbox, translated, fontsize=fontsize, color=(0, 0, 0))
        except Exception:
            pass
