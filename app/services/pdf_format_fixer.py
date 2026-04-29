"""PDF Translation Format Fixer — fixes font and line wrapping in translated PDFs."""

import fitz
import os

PAGE_W = 595.3
MARGIN_L = 57.7
MARGIN_R = 540.9
CONTENT_W = MARGIN_R - MARGIN_L

SERIF_REGULAR = "Times-Roman"
SERIF_BOLD = "Times-Bold"
SERIF_ITALIC = "Times-Italic"
SERIF_BOLDITALIC = "Times-BoldItalic"


def _serif_font(original_fontname: str) -> str:
    fn = original_fontname.lower()
    if "bolditalic" in fn or ("bold" in fn and "italic" in fn):
        return SERIF_BOLDITALIC
    if "bold" in fn:
        return SERIF_BOLD
    if "italic" in fn or "oblique" in fn:
        return SERIF_ITALIC
    return SERIF_REGULAR


def _needs_fixing(page: fitz.Page) -> bool:
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if "helvetica" in span["font"].lower() or "helv" in span["font"].lower():
                    return True
    return False


def _wrap_text(text: str, fontname: str, fontsize: float, max_width: float):
    words = text.split()
    if not words:
        return []
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if fitz.get_text_length(test, fontname=fontname, fontsize=fontsize) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def fix_translated_pdf(translated_pdf_path: str, output_pdf_path: str) -> str:
    doc = fitz.open(translated_pdf_path)
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        if page_idx == 0:
            continue
        if not _needs_fixing(page):
            continue

        # Extract spans before redacting
        spans = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        spans.append(span)

        if not spans:
            continue

        # Redact all text
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            r = fitz.Rect(block["bbox"]) + (-2, -2, 2, 2)
            page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions()

        # Redraw with correct font + wrapping
        for span in spans:
            new_font = _serif_font(span["font"])
            size = span["size"]
            x, y = span["origin"]
            text = span["text"]

            actual_w = fitz.get_text_length(text, fontname=new_font, fontsize=size)

            if size < 10 or actual_w <= CONTENT_W:
                # Fits — draw at original position
                try:
                    page.insert_text(fitz.Point(x, y), text, fontname=new_font, fontsize=size, color=(0, 0, 0))
                except Exception:
                    pass
            else:
                # Needs wrapping
                wrapped = _wrap_text(text, new_font, size, CONTENT_W)
                for i, wline in enumerate(wrapped):
                    try:
                        page.insert_text(fitz.Point(MARGIN_L, y + i * size * 1.2), wline, fontname=new_font, fontsize=size, color=(0, 0, 0))
                    except Exception:
                        pass

    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()
    return output_pdf_path
