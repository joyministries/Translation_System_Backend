"""
Structure-preserving translation for .docx files.
- Cover page (up to first page break) is kept exactly as-is
- Rest of document text is translated
- Returns translated .docx bytes
"""
import io
import re
import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PRESERVED_FRONT_TRANSLATED_LINES = 1


def _find_cover_end(body: etree._Element) -> int:
    """Return index of last paragraph on cover page, or -1 if none found."""
    return _find_preserved_front_end(body, pages=1)


def _find_preserved_front_end(body: etree._Element, pages: int = 2) -> int:
    """Return the last paragraph index in the preserved front matter pages.

    Only counts a page boundary as a cover-page break if the content seen so
    far is sparse (≤ 4 non-empty lines). Books whose page 1 is separated from
    page 2 by spacing/layout only (no explicit break) fall back to preserving
    everything before the second non-empty paragraph.
    """
    page_breaks_seen = 0
    last_break_idx = -1
    non_empty_since_last_break = 0
    paras = body.findall(f"{{{W}}}p")
    for idx, para in enumerate(paras):
        has_page_boundary = para.find(f".//{{{W}}}sectPr") is not None
        for br in para.findall(f".//{{{W}}}br"):
            if br.get(f"{{{W}}}type", "") == "page":
                has_page_boundary = True
                break
        if _paragraph_text(para).strip():
            non_empty_since_last_break += 1
        if has_page_boundary:
            if non_empty_since_last_break <= 4:
                # Sparse section — treat as a real cover-page boundary
                page_breaks_seen += 1
                last_break_idx = idx
                non_empty_since_last_break = 0
                if page_breaks_seen >= pages:
                    return idx
            else:
                # Dense section — not a cover page, stop
                break

    # No sparse page break found — preserve up to just before the second
    # non-empty paragraph (page 1 only).
    if last_break_idx == -1:
        non_empty = 0
        for idx, para in enumerate(paras):
            if _paragraph_text(para).strip():
                non_empty += 1
                if non_empty == 2:
                    return idx - 1

    return last_break_idx


def _find_front_matter_end(body: etree._Element) -> int:
    """Return the last paragraph index of all front matter (cover, title, extra
    pages, TOC) — everything before real chapter/section body content begins.

    Strategy: scan paragraphs tracking the last SECT/page-break paragraph seen.
    The front matter ends at the last such boundary before the first paragraph
    that has a Heading1 or Heading2 style AND whose text looks like a chapter or
    section heading (not a sub-heading inside the front matter).
    We stop at the SECT boundary *before* that first real body heading paragraph.
    """
    paras = body.findall(f"{{{W}}}p")
    last_sect_idx = -1

    for idx, para in enumerate(paras):
        has_page_boundary = para.find(f".//{{{W}}}sectPr") is not None
        if not has_page_boundary:
            for br in para.findall(f".//{{{W}}}br"):
                if br.get(f"{{{W}}}type", "") == "page":
                    has_page_boundary = True
                    break

        if has_page_boundary:
            last_sect_idx = idx
            continue

        # Check if this is the first real body heading
        style = ""
        ps = para.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        if ps is not None:
            style = (ps.get(f"{{{W}}}val") or "").lower()

        if style in ("heading1", "heading2"):
            text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
            # Real body headings are chapter/section markers or TOC title
            if _is_major_body_start_text(text):
                # The front matter ended at the last sect break before this
                return last_sect_idx if last_sect_idx >= 0 else idx - 1
            # Also stop if we see a TOC title heading (INDHOLDSFORTEGNELSE etc.)
            if _line_looks_like_toc_title(text):
                # Keep scanning — the TOC itself is still front matter
                continue

    # No clear body start found — fall back to counting 2 page breaks
    return _find_preserved_front_end(body, pages=2)


def _collect_runs(body: etree._Element, start_idx: int):
    """Collect (t_element, text) pairs from paragraphs after start_idx."""
    paras = body.findall(f"{{{W}}}p")
    runs = []
    for para in paras[start_idx:]:
        if para.find(f".//{{{W}}}drawing") is not None:
            continue
        for run in para.findall(f".//{{{W}}}r"):
            t_el = run.find(f"{{{W}}}t")
            if t_el is None or not (t_el.text or "").strip():
                continue
            text = t_el.text
            if re.match(r"(https?://|www\.|mailto:|\S+@\S+\.\S+)", text.strip()):
                continue
            runs.append((t_el, text))
    return runs


def _paragraph_text(para: etree._Element) -> str:
    return "".join(t.text or "" for t in para.findall(f".//{{{W}}}t"))


def _paragraph_text_no_superscript(para: etree._Element) -> str:
    """Return paragraph text excluding superscript runs."""
    parts = []
    for t_el in para.findall(f".//{{{W}}}t"):
        run = t_el.getparent()
        if run is not None and run.tag == f"{{{W}}}r":
            rPr = run.find(f"{{{W}}}rPr")
            if rPr is not None:
                vert = rPr.find(f"{{{W}}}vertAlign")
                if vert is not None and vert.get(f"{{{W}}}val") == "superscript":
                    continue
        parts.append(t_el.text or "")
    return "".join(parts)


def _run_for_text_node(t_el: etree._Element) -> etree._Element | None:
    current = t_el
    while current is not None and etree.QName(current).localname != "r":
        current = current.getparent()
    return current


def _run_is_bold(run: etree._Element | None) -> bool:
    if run is None:
        return False
    r_pr = run.find(f"{{{W}}}rPr")
    if r_pr is None:
        return False
    bold = r_pr.find(f"{{{W}}}b")
    if bold is None:
        return False
    return bold.get(f"{{{W}}}val", "true") not in {"false", "0", "off"}


def _paragraph_style_value(para: etree._Element) -> str:
    p_style = para.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    return (p_style.get(f"{{{W}}}val") if p_style is not None else "") or ""


def _has_ancestor_named(element: etree._Element, names: set[str]) -> bool:
    current = element.getparent()
    while current is not None:
        if etree.QName(current).localname in names:
            return True
        current = current.getparent()
    return False


def _is_toc_paragraph(para: etree._Element) -> bool:
    style = _paragraph_style_value(para).lower()
    return style.startswith("toc") or _has_ancestor_named(para, {"sdt", "sdtContent"})


def _looks_like_artifact_paragraph(para: etree._Element, text: str) -> bool:
    style = _paragraph_style_value(para).lower()
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if style or not clean:
        return False
    if len(clean) > 40 or len(clean.split()) > 5:
        return False
    if re.search(r"[.!?:;0-9]", clean):
        return False
    return clean[:1].islower()


def _paragraph_looks_like_heading(para: etree._Element, text: str) -> bool:
    style = _paragraph_style_value(para).lower()
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if "heading" in style or "title" in style:
        return True
    if clean and len(clean) <= 120 and clean.upper() == clean and re.search(r"[A-ZÀ-Þ]", clean):
        return True
    return False


def _clear_paragraph_text(para: etree._Element) -> None:
    for t_el in para.findall(f".//{{{W}}}t"):
        t_el.text = ""



def _protect_connector_line_breaks(text: str) -> str:
    """Keep short connector phrases together across line/page breaks."""
    value = text or ""
    # Keep phrases like "Kampuni ya Matunda" together, not just "ya Matunda".
    value = re.sub(
        r"\b([A-ZÀ-Þ][\wÀ-ÿ’'-]{2,})\s+(ya|wa|kwa|na|la|za|cha|vya|of|to|for|and)\s+(?=[A-ZÀ-Þ])",
        lambda match: match.group(1) + "\u00a0" + match.group(2) + "\u00a0",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\b(ya|wa|kwa|na|la|za|cha|vya|of|to|for|and)\s+(?=[A-ZÀ-Þ])",
        lambda match: match.group(1) + "\u00a0",
        value,
        flags=re.IGNORECASE,
    )



def _set_text_with_inline_heading_break(t_el: etree._Element, text: str) -> None:
    value = text or ""
    match = re.match(
        r"^(.+?\([^)]{2,90}\))\s+((?:UTANGULIZI|ISINGENISO|INTRODUCTION|INLEIDING|ISANDULELO|DIBAJI)\b.*)$",
        value,
        re.IGNORECASE,
    )
    if not match:
        t_el.text = value
        return

    first, heading = match.group(1).strip(), match.group(2).strip()
    t_el.text = first
    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    run = _run_for_text_node(t_el)
    if run is None:
        return
    parent = run.getparent()
    if parent is None:
        return
    new_run = etree.Element(f"{{{W}}}r")
    r_pr = run.find(f"{{{W}}}rPr")
    if r_pr is not None:
        new_run.append(etree.fromstring(etree.tostring(r_pr)))
    new_run.append(etree.Element(f"{{{W}}}br"))
    new_t = etree.Element(f"{{{W}}}t")
    new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    new_t.text = heading
    new_run.append(new_t)
    parent.insert(parent.index(run) + 1, new_run)


def _is_superscript_text(t_el: etree._Element) -> bool:
    run = t_el.getparent()
    if run is not None and run.tag == f"{{{W}}}r":
        rPr = run.find(f"{{{W}}}rPr")
        if rPr is not None:
            vert = rPr.find(f"{{{W}}}vertAlign")
            if vert is not None and vert.get(f"{{{W}}}val") == "superscript":
                return True
    return False


def _replace_paragraph_text(para: etree._Element, replacement: str) -> None:
    replacement = _protect_connector_line_breaks(replacement)
    text_nodes = [t for t in para.findall(f".//{{{W}}}t") if not _is_superscript_text(t)]
    if not text_nodes:
        return

    original_text = _paragraph_text(para)
    node_runs = [(t_el, _run_for_text_node(t_el)) for t_el in text_nodes]
    bold_nodes = [(t_el, run) for t_el, run in node_runs if _run_is_bold(run)]
    non_bold_nodes = [(t_el, run) for t_el, run in node_runs if not _run_is_bold(run)]

    # Preserve common inline-bold labels at the start of body paragraphs.
    # Example: bold "Yusufu:" + normal explanation should not become all normal.
    if bold_nodes and non_bold_nodes and not _paragraph_looks_like_heading(para, original_text):
        label_match = re.match(r"^([^:：]{1,80}[:：])\s*(.*)$", replacement or "")
        if label_match:
            bold_target = max(bold_nodes, key=lambda item: len(item[0].text or ""))[0]
            body_target = max(non_bold_nodes, key=lambda item: len(item[0].text or ""))[0]
            for t_el in text_nodes:
                if t_el is bold_target:
                    _set_text_with_inline_heading_break(t_el, label_match.group(1) + " ")
                    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                    bold_run = _run_for_text_node(t_el)
                    if bold_run is not None:
                        _set_run_bold(bold_run)
                        _set_run_font_face(bold_run)
                elif t_el is body_target:
                    _set_text_with_inline_heading_break(t_el, label_match.group(2))
                    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                else:
                    t_el.text = ""
            return

    # Body paragraphs often begin with a bold phrase/number, followed by normal
    # text. Put the full replacement into the dominant normal run so we do not
    # accidentally make the whole paragraph bold. True headings keep their bold
    # heading run.
    if non_bold_nodes and not _paragraph_looks_like_heading(para, original_text):
        target = max(non_bold_nodes, key=lambda item: len(item[0].text or ""))[0]
    else:
        target = max(text_nodes, key=lambda t: len(t.text or ""))

    for t_el in text_nodes:
        if t_el is target:
            _set_text_with_inline_heading_break(t_el, replacement)
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        else:
            t_el.text = ""


def _iter_translatable_paragraphs(body: etree._Element, cover_end: int):
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()
    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids:
            continue
        if _has_ancestor_named(para, {"txbxContent", "drawing", "pict", "AlternateContent"}):
            continue
        if para.find(f".//{{{W}}}drawing") is not None and not _paragraph_text(para).strip():
            continue
        current = _paragraph_text(para).strip()
        if not current:
            continue
        if _looks_like_artifact_paragraph(para, current):
            _clear_paragraph_text(para)
            continue
        if re.match(r"(https?://|www\.|mailto:|\S+@\S+\.\S+)", current):
            continue
        yield para


def _line_looks_like_toc_candidate(line: str) -> bool:
    clean = re.sub(r"\s+", " ", (line or "").strip())
    if not clean or len(clean) > 160:
        return False
    if re.search(r"[.。!?]$", clean):
        return False
    letters = re.findall(r"[^\W\d_]", clean, flags=re.UNICODE)
    uppers = [ch for ch in letters if ch.upper() == ch and ch.lower() != ch]
    if letters and len(uppers) / len(letters) >= 0.55:
        return True
    return bool(re.match(
        r"(?i)^(chapter|kapitel|abschnitt|teil|"
        r"cap[ií]tulo|capitolo|sezione|"
        r"section|secci[oó]n|part|parte|appendix|appendice|"
        r"bibliography|bibliograf[ií]a|preface|pr[oó]logo|introduction|introducci[oó]n|"
        r"conclusion|conclusi[oó]n|course introduction|"
        r"sura|sehemu|dibaji|utangulizi|bibliografia|"
        r"isahluko|isigaba|isingeniso|"
        r"chitsauko|nhanganyaya|"
        r"hoofstuk|afdeling|voorwoord|inleiding)\b",
        clean,
    ))


def _line_looks_like_toc_title(line: str) -> bool:
    clean = re.sub(r"\s+", " ", (line or "").strip())
    return bool(re.search(
        r"(?i)\b(table\s+of\s+contents|contents|tabla\s+de\s+contenido(?:s)?|"
        r"sommario|indice|"
        r"yaliyomo|okuqukethwe|zviri\s+mukati|inhoud)\b",
        clean,
    ))


def _strip_toc_dot_leaders(text: str) -> str:
    """Keep TOC entry text/page numbers, but remove dotted leader fill."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    clean = re.sub(r"\.{3,}|…{2,}", " ", clean)
    clean = re.sub(r"(?<=[^\W\d_])(?=\d{1,4}$)", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _line_is_toc_noise(text: str) -> bool:
    """Lines that must never be treated as TOC entries (language-agnostic)."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return True
    if re.search(r"(https?://|www\.|mailto:|\S+@\S+\.\S+)", clean, re.IGNORECASE):
        return True
    if re.match(r"^\d+\s*(https?://|www\.)", clean, re.IGNORECASE):
        return True
    if re.search(r"(?i)\b(pp?\.|publishers?|publications?|press)\b", clean) and re.search(r"\d{4}", clean):
        return True
    words = re.findall(r"[^\W\d_]+", clean, flags=re.UNICODE)
    if len(words) > 26 or len(clean) > 200:
        return True
    if len(words) > 14 and re.search(r"[.!?;:]$", clean):
        return True
    return False


def _score_toc_entry_line(text: str) -> int:
    """Higher score = more likely a real TOC entry (language-agnostic)."""
    clean = _strip_toc_dot_leaders(text)
    if not clean or _line_is_toc_noise(clean):
        return -100
    if _line_looks_like_toc_title(clean) or _is_copyright_line(clean):
        return -50

    score = 0
    if re.search(r"\b\d{1,4}$", clean):
        score += 4
    if _line_looks_like_toc_candidate(clean):
        score += 3
    words = re.findall(r"[^\W\d_]+", clean, flags=re.UNICODE)
    if ":" in clean and len(words) <= 18 and len(clean) <= 150:
        score += 2
    letters = re.findall(r"[^\W\d_]", clean, flags=re.UNICODE)
    if letters:
        uppers = [ch for ch in letters if ch.upper() == ch and ch.lower() != ch]
        if len(uppers) / len(letters) >= 0.55 and len(clean) <= 120:
            score += 1
    return score


def _find_toc_title_index(translated_lines: list[str]) -> int:
    """Return index of the last explicit TOC title in front matter."""
    last = -1
    for idx, line in enumerate(translated_lines[:450]):
        if _line_looks_like_toc_title(line):
            last = idx
    return last


def _collect_toc_candidates(translated_lines: list[str], start: int, needed: int) -> list[str]:
    """Pick the best contiguous TOC-like block after the TOC title."""
    if start < 0 or needed <= 0:
        return []

    normalized: list[tuple[str, int]] = []
    pending: str | None = None
    for line in translated_lines[start + 1 : start + 1 + 400]:
        clean = _strip_toc_dot_leaders(line)
        if not clean:
            continue
        if clean.isdigit() and pending is not None:
            normalized.append((f"{pending} {clean}".strip(), _score_toc_entry_line(f"{pending} {clean}")))
            pending = None
            continue
        if _line_looks_like_toc_title(clean) or _is_copyright_line(clean):
            continue
        score = _score_toc_entry_line(clean)
        if score >= 2:
            normalized.append((clean, score))
            pending = None
        elif score >= 1 and ":" in clean:
            pending = clean
        else:
            pending = None

    if not normalized:
        return []

    if len(normalized) <= needed:
        return [text for text, _ in normalized if _ >= 1]

    best_start = 0
    best_avg = -1.0
    for window_start in range(0, len(normalized) - needed + 1):
        window = normalized[window_start : window_start + needed]
        if any(score < 1 for _, score in window):
            continue
        avg = sum(score for _, score in window) / needed
        if avg > best_avg:
            best_avg = avg
            best_start = window_start

    if best_avg >= 1:
        return [text for text, _ in normalized[best_start : best_start + needed]]

    # Fallback: keep the strongest lines in order.
    strong = [(text, score) for text, score in normalized if score >= 2]
    if len(strong) >= needed:
        return [text for text, _ in strong[:needed]]
    return [text for text, score in normalized if score >= 1][:needed]


def _apply_translated_toc_entries(body: etree._Element, translated_lines: list[str]) -> None:
    toc_paras = [
        para
        for para in body.findall(f".//{{{W}}}p")
        if _is_toc_paragraph(para) and _paragraph_text(para).strip()
    ]
    if not toc_paras:
        return

    for para in toc_paras:
        _remove_toc_tab_leaders(para)


def _apply_toc_from_body_headings(body: etree._Element, cover_end: int) -> None:
    """Replace TOC1 paragraph text with translated Heading1 body headings.

    Runs after body translation so Heading1 paragraphs already contain
    translated text. This gives us the correct chapter/section-level entries
    for the TOC instead of guessing from arbitrary body text.
    """
    toc_paras = [
        para
        for para in body.findall(f".//{{{W}}}p")
        if _is_toc_paragraph(para) and _paragraph_text(para).strip()
    ]
    if not toc_paras:
        return

    direct_paras = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paras[: cover_end + 1]} if cover_end >= 0 else set()

    heading_texts: list[str] = []
    toc_title_text: str | None = None

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids:
            continue
        text = _paragraph_text(para).strip()
        if not text:
            continue
        style = _paragraph_style_value(para).lower()
        if style == "heading1":
            if _line_looks_like_toc_title(text):
                toc_title_text = text
            else:
                heading_texts.append(text)

    if not heading_texts:
        return

    if toc_title_text:
        _replace_paragraph_text(toc_paras[0], toc_title_text)

    for toc_para, heading_text in zip(toc_paras[1:], heading_texts):
        _replace_paragraph_text(toc_para, heading_text)

    for para in toc_paras[1 + len(heading_texts):]:
        _clear_paragraph_text(para)


def _remove_child(parent: etree._Element | None, child_name: str) -> None:
    if parent is None:
        return
    child = parent.find(f"{{{W}}}{child_name}")
    if child is not None:
        parent.remove(child)


def _relax_pagination_constraints(body: etree._Element, cover_end: int) -> None:
    """Let translated text split naturally instead of pushing whole blocks to the next page.
    Skip Heading1/Title paragraphs so their pagination properties remain intact."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids:
            continue
        if _paragraph_is_major_heading(para):
            continue
        p_pr = para.find(f"{{{W}}}pPr")
        if p_pr is None:
            continue
        _remove_child(p_pr, "keepNext")
        _remove_child(p_pr, "keepLines")
        _remove_child(p_pr, "widowControl")

    for row in body.findall(f".//{{{W}}}tr"):
        tr_pr = row.find(f"{{{W}}}trPr")
        _remove_child(tr_pr, "cantSplit")




def _is_major_body_start_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return False
    return bool(re.match(
        r"^(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ|SECTION|SEHEMU|ISIGABA|UTANGULIZI|INTRODUCTION|COURSE\s+INTRODUCTION"
        r"|AFSNIT|DEEL|PART|ABSCHNITT|SECCIÓN|SEZIONE|РАЗДЕЛ|IQXENYE|ICANDELO|BIBLIOGRAPHY|BIBLIOGRAPHIE|REFERENCIAS)\b",
        clean,
        re.IGNORECASE,
    ))


def _is_legal_credit_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return False
    return bool(re.search(
        r"(?i)(scripture quotations.*copyright|copyright|©|thomas nelson|"
        r"international bible society|tyndale house|used by permission|all rights reserved)",
        clean,
    ))


def _is_copyright_line(text: str) -> bool:
    """Lines we must keep in source language (copyright/attribution)."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return False
    return bool(re.search(r"(?i)(©|copyright)", clean))


def _is_tail_promo_start_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    return bool(re.match(
        r"(?i)^(iwe\s+unatafuta|uma\s+ufuna|kungakhathaliseki\s+ukuthi\s+ufuna|of\s+jy\s+nou\s+soek|if\s+you\s+are\s+looking\s+for)\b",
        clean,
    ))


def _next_nonempty_paragraph_text(direct_paragraphs: list[etree._Element], start_index: int) -> str:
    for para in direct_paragraphs[start_index + 1:]:
        text = _paragraph_text(para).strip()
        if text:
            return text
    return ""




def _find_body_start_after_toc(body: etree._Element, cover_end: int) -> int:
    """Return direct paragraph index where real body content starts after the TOC/front matter."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    toc_seen = False
    for idx, para in enumerate(direct_paragraphs):
        if idx <= cover_end:
            continue
        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text:
            continue
        if _line_looks_like_toc_title(text):
            toc_seen = True
            continue
        if toc_seen and _is_major_body_start_text(text):
            return idx
    # Fallback: keep the workbook front matter intact even if TOC detection fails.
    return cover_end + 1


def _remove_body_empty_section_breaks(body: etree._Element, cover_end: int) -> None:
    """Remove source page-boundary section breaks that orphan translated paragraphs.
    Only acts on the body after front matter — never touches section breaks within
    the front matter pages (cover, title, extra pages, TOC) so their page structure
    is preserved exactly as authored.
    """
    direct_paragraphs = body.findall(f"{{{W}}}p")
    for idx in range(len(direct_paragraphs) - 1, -1, -1):
        if idx <= cover_end:
            continue
        para = direct_paragraphs[idx]
        if _paragraph_text(para).strip():
            continue
        if para.find(f".//{{{W}}}drawing") is not None or para.find(f".//{{{W}}}pict") is not None:
            continue
        if para.find(f"{{{W}}}pPr/{{{W}}}sectPr") is None:
            continue
        next_text = _next_nonempty_paragraph_text(direct_paragraphs, idx)
        if _is_major_body_start_text(next_text):
            continue
        parent = para.getparent()
        if parent is not None:
            parent.remove(para)


def _relax_style_pagination_constraints(root: etree._Element) -> None:
    """Remove style-level pagination locks inherited by translated paragraphs.
    Ensure heading styles have pageBreakBefore so chapters start on new pages."""
    for style in root.findall(f".//{{{W}}}style"):
        style_id = (style.get(f"{{{W}}}styleId") or "").lower()
        p_pr = style.find(f"{{{W}}}pPr")
        if p_pr is None:
            continue
        _remove_child(p_pr, "keepNext")
        _remove_child(p_pr, "keepLines")
        _remove_child(p_pr, "widowControl")
        if style_id.startswith(("heading1", "title")):
            # Ensure heading styles force a page break and remove numPr
            # which can cause LibreOffice to ignore pageBreakBefore.
            _remove_child(p_pr, "numPr")
            if p_pr.find(f"{{{W}}}pageBreakBefore") is None:
                p_pr.insert(0, etree.Element(f"{{{W}}}pageBreakBefore"))
        else:
            _remove_child(p_pr, "pageBreakBefore")


def _ensure_p_pr(para: etree._Element) -> etree._Element:
    p_pr = para.find(f"{{{W}}}pPr")
    if p_pr is None:
        p_pr = etree.Element(f"{{{W}}}pPr")
        para.insert(0, p_pr)
    return p_pr


def _set_compact_spacing(para: etree._Element) -> None:
    p_pr = _ensure_p_pr(para)
    spacing = p_pr.find(f"{{{W}}}spacing")
    if spacing is None:
        spacing = etree.Element(f"{{{W}}}spacing")
        p_pr.append(spacing)
    spacing.set(f"{{{W}}}before", "0")
    spacing.set(f"{{{W}}}after", "0")


def _set_spacing_twips(para: etree._Element, before: str = "0", after: str = "0") -> None:
    p_pr = _ensure_p_pr(para)
    spacing = p_pr.find(f"{{{W}}}spacing")
    if spacing is None:
        spacing = etree.Element(f"{{{W}}}spacing")
        p_pr.append(spacing)
    spacing.set(f"{{{W}}}before", before)
    spacing.set(f"{{{W}}}after", after)
    spacing.set(f"{{{W}}}beforeAutospacing", "0")
    spacing.set(f"{{{W}}}afterAutospacing", "0")


def _paragraph_alignment(para: etree._Element) -> str:
    jc = para.find(f"{{{W}}}pPr/{{{W}}}jc")
    return (jc.get(f"{{{W}}}val") if jc is not None else "") or ""


def _remove_empty_body_paragraphs(body: etree._Element, cover_end: int) -> None:
    direct_paragraphs = body.findall(f"{{{W}}}p")
    keep_one_blank = False
    for idx in range(len(direct_paragraphs) - 1, -1, -1):
        if idx <= cover_end:
            continue
        para = direct_paragraphs[idx]
        has_text = bool(_paragraph_text(para).strip())
        has_drawing = para.find(f".//{{{W}}}drawing") is not None or para.find(f".//{{{W}}}pict") is not None
        has_section = para.find(f"{{{W}}}pPr/{{{W}}}sectPr") is not None
        has_pagebreak = any(br.get(f"{{{W}}}type", "") == "page" for br in para.findall(f".//{{{W}}}br"))
        if has_pagebreak and not has_text:
            # Remove mid-section page breaks (before numbered items like "8. ...")
            # but keep page breaks before chapter headings — those are handled by
            # pageBreakBefore on the heading itself via _normalize_body_spacing.
            next_text = ""
            for j in range(idx + 1, min(idx + 6, len(direct_paragraphs))):
                next_text = _paragraph_text(direct_paragraphs[j]).strip()
                if next_text:
                    break
            is_mid_section = bool(re.match(r"^\d+\.\s+\S", next_text))
            if is_mid_section:
                parent = para.getparent()
                if parent is not None:
                    parent.remove(para)
            keep_one_blank = False
            continue
        if has_text or has_drawing or has_section or has_pagebreak:
            keep_one_blank = False
            continue
        if keep_one_blank:
            parent = para.getparent()
            if parent is not None:
                parent.remove(para)
            continue
        keep_one_blank = True


def _normalize_body_spacing(body: etree._Element, cover_end: int) -> None:
    """Restore pageBreakBefore on chapter headings. Leave all other spacing
    exactly as authored in the source DOCX so paragraph gaps are preserved."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            continue
        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text:
            continue

        p_pr = _ensure_p_pr(para)
        is_chapter_start = _paragraph_is_major_heading(para)

        if is_chapter_start:
            # Move any preceding page break INTO the heading's first run.
            # This ensures the heading always starts the new page (not at
            # the bottom of the previous page due to shorter translated text).
            runs = para.findall(f"{{{W}}}r")
            has_own_br = any(
                br.get(f"{{{W}}}type", "") == "page"
                for r in runs for br in r.findall(f"{{{W}}}br")
            )
            if not has_own_br and runs:
                # Check if preceding para has the break — remove it from there
                para_idx = next((i for i, dp in enumerate(direct_paragraphs) if dp is para), -1)
                if para_idx > 0:
                    for j in range(para_idx - 1, max(0, para_idx - 4), -1):
                        prev_p = direct_paragraphs[j]
                        for br in prev_p.findall(f".//{{{W}}}br"):
                            if br.get(f"{{{W}}}type", "") == "page":
                                br.getparent().remove(br)
                                has_own_br = False  # we removed it, will add below
                        if _paragraph_text(prev_p).strip():
                            break
                # Add break to heading's first run
                br_el = etree.Element(f"{{{W}}}br")
                br_el.set(f"{{{W}}}type", "page")
                runs[0].insert(0, br_el)
        elif not _is_tail_promo_start_text(text):
            # Strip pageBreakBefore from non-heading body paragraphs only
            _remove_child(p_pr, "pageBreakBefore")


def _normalize_flow_paragraphs(body: etree._Element, cover_end: int) -> None:
    """Prevent long quote/body text from inheriting heading spacing/pagination behavior."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()
    previous_was_long_quote = False

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            previous_was_long_quote = False
            continue

        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text:
            previous_was_long_quote = False
            continue

        style = _paragraph_style_value(para).lower()
        quote_like = text.startswith(('“', '"', '‘', "'")) or previous_was_long_quote and text[:1].islower()
        long_heading_body = style in {"heading4", "heading5"} and (len(text) > 150 or quote_like)

        if long_heading_body:
            p_pr = _ensure_p_pr(para)
            p_style = p_pr.find(f"{{{W}}}pStyle")
            if p_style is not None:
                p_pr.remove(p_style)
            _set_compact_spacing(para)
            previous_was_long_quote = quote_like or len(text) > 150
        else:
            previous_was_long_quote = False


def _paragraph_is_major_heading(para: etree._Element) -> bool:
    style = _paragraph_style_value(para).lower()
    if not _paragraph_text(para).strip():
        return False
    return style in {"heading1", "title"}


def _paragraph_is_chapter_heading(para: etree._Element) -> bool:
    """Heading1/title = section start (own page). Heading2 = chapter under a section (shares page)."""
    return _paragraph_is_major_heading(para)


def _paragraph_starts_new_page_or_section(para: etree._Element) -> bool:
    p_pr = para.find(f"{{{W}}}pPr")
    if p_pr is None:
        return False
    return p_pr.find(f"{{{W}}}pageBreakBefore") is not None or p_pr.find(f"{{{W}}}sectPr") is not None


def _looks_like_body_continuation_para(para: etree._Element, text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return False
    if _paragraph_is_major_heading(para) or _paragraph_has_list_format(para):
        return False
    if _paragraph_starts_new_page_or_section(para):
        return False
    if clean.startswith(("•", "-", "–")):
        return False
    if re.match(r"^(?:\d+|[A-Za-z])(?:[.)]|:)\s+", clean):
        return False
    if clean.isupper() and len(clean) <= 160:
        return False
    if clean.endswith(":") and len(clean) <= 140:
        return False
    words = re.findall(r"[\wÀ-ÿ’'-]+", clean)
    if len(words) <= 3:
        return False
    style = _paragraph_style_value(para).lower()
    if style in {"heading1", "heading2", "heading3", "title", "subtitle"}:
        return False
    return True


def _merge_lowercase_continuations(body: etree._Element, cover_end: int) -> None:
    """Join body paragraphs that are actually line continuations split by extraction/layout."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()
    paras = [p for p in body.findall(f".//{{{W}}}p") if id(p) not in cover_ids and not _is_toc_paragraph(p)]

    previous: etree._Element | None = None
    for para in paras:
        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text:
            continue

        if previous is not None:
            prev_text = re.sub(r"\s+", " ", _paragraph_text(previous).strip())
            starts_lowercase = bool(re.match(r"^[a-zà-öø-ÿ]", text, re.UNICODE))
            normal_body_continuation = (
                len(prev_text) >= 40
                and _looks_like_body_continuation_para(previous, prev_text)
                and _looks_like_body_continuation_para(para, text)
            )
            if starts_lowercase or normal_body_continuation:
                if prev_text.endswith(".") and starts_lowercase:
                    # Split-line translations can add a sentence period before a lowercase
                    # continuation fragment, e.g. "kutoa njia. kwa mwingine".
                    prev_text = prev_text[:-1]
                _replace_paragraph_text(previous, f"{prev_text} {text}")
                _clear_paragraph_text(para)
                continue

        previous = para


def _ensure_r_pr(run: etree._Element) -> etree._Element:
    r_pr = run.find(f"{{{W}}}rPr")
    if r_pr is None:
        r_pr = etree.Element(f"{{{W}}}rPr")
        run.insert(0, r_pr)
    return r_pr



def _set_run_bold(run: etree._Element) -> None:
    r_pr = _ensure_r_pr(run)
    for name in ("b", "bCs"):
        node = r_pr.find(f"{{{W}}}{name}")
        if node is None:
            node = etree.Element(f"{{{W}}}{name}")
            r_pr.append(node)
        node.set(f"{{{W}}}val", "1")


def _set_run_font_face(run: etree._Element, font_name: str = "Liberation Serif") -> None:
    r_pr = _ensure_r_pr(run)
    fonts = r_pr.find(f"{{{W}}}rFonts")
    if fonts is None:
        fonts = etree.Element(f"{{{W}}}rFonts")
        r_pr.insert(0, fonts)
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(f"{{{W}}}{attr}", font_name)

def _set_run_font_size(run: etree._Element, half_points: str) -> None:
    r_pr = _ensure_r_pr(run)
    for name in ("sz", "szCs"):
        node = r_pr.find(f"{{{W}}}{name}")
        if node is None:
            node = etree.Element(f"{{{W}}}{name}")
            r_pr.append(node)
        node.set(f"{{{W}}}val", half_points)


def _set_paragraph_line_spacing(para: etree._Element, line_twips: str = "240") -> None:
    p_pr = _ensure_p_pr(para)
    spacing = p_pr.find(f"{{{W}}}spacing")
    if spacing is None:
        spacing = etree.Element(f"{{{W}}}spacing")
        p_pr.append(spacing)
    spacing.set(f"{{{W}}}line", line_twips)
    spacing.set(f"{{{W}}}lineRule", "auto")


def _increase_body_font_size(body: etree._Element, cover_end: int, half_points: str = "24") -> None:
    """Increase translated body text to 12pt without shrinking headings."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            continue
        text = _paragraph_text(para).strip()
        if not text or _paragraph_is_major_heading(para):
            continue
        style = _paragraph_style_value(para).lower()
        if style.startswith("heading") and len(text) <= 140:
            continue
        for run in para.findall(f".//{{{W}}}r"):
            if run.find(f"{{{W}}}t") is not None:
                _set_run_font_size(run, half_points)


def _tighten_page_margins(body: etree._Element, cover_end: int) -> None:
    """Give translated text more horizontal room without changing the cover page."""
    for idx, sect_pr in enumerate(body.findall(f".//{{{W}}}sectPr")):
        # Leave the first section alone because it belongs to the preserved cover/front page.
        if idx == 0:
            continue
        pg_mar = sect_pr.find(f"{{{W}}}pgMar")
        if pg_mar is None:
            pg_mar = etree.Element(f"{{{W}}}pgMar")
            sect_pr.append(pg_mar)
        pg_mar.set(f"{{{W}}}left", "720")
        pg_mar.set(f"{{{W}}}right", "720")
        pg_mar.set(f"{{{W}}}top", "720")
        pg_mar.set(f"{{{W}}}bottom", "720")


def _paragraph_has_list_format(para: etree._Element) -> bool:
    style = _paragraph_style_value(para).lower()
    return style.startswith("list") or para.find(f"{{{W}}}pPr/{{{W}}}numPr") is not None


def _remove_list_formatting(para: etree._Element) -> None:
    p_pr = _ensure_p_pr(para)
    _remove_child(p_pr, "numPr")
    p_style = p_pr.find(f"{{{W}}}pStyle")
    if p_style is not None and (p_style.get(f"{{{W}}}val") or "").lower().startswith("list"):
        p_pr.remove(p_style)


def _inline_translated_bullets(body: etree._Element, cover_end: int) -> None:
    """Avoid Word-generated bullets splitting away from translated list text."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            continue
        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text or not _paragraph_has_list_format(para):
            continue
        if _paragraph_is_major_heading(para):
            continue
        if not text.startswith(("•", "", "-")):
            _replace_paragraph_text(para, f"• {text}")
        _remove_list_formatting(para)
        _set_compact_spacing(para)


def _set_left_alignment(para: etree._Element) -> None:
    p_pr = _ensure_p_pr(para)
    jc = p_pr.find(f"{{{W}}}jc")
    if jc is None:
        jc = etree.Element(f"{{{W}}}jc")
        p_pr.append(jc)
    jc.set(f"{{{W}}}val", "left")
    _remove_child(p_pr, "textAlignment")
    _remove_child(p_pr, "adjustRightInd")
    _remove_child(p_pr, "snapToGrid")


def _set_center_alignment(para: etree._Element) -> None:
    p_pr = _ensure_p_pr(para)
    jc = p_pr.find(f"{{{W}}}jc")
    if jc is None:
        jc = etree.Element(f"{{{W}}}jc")
        p_pr.append(jc)
    jc.set(f"{{{W}}}val", "center")
    _remove_child(p_pr, "textAlignment")
    _remove_child(p_pr, "adjustRightInd")
    _remove_child(p_pr, "snapToGrid")


def _left_align_body_paragraphs(body: etree._Element, cover_end: int) -> None:
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()
    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            continue
        text = _paragraph_text(para).strip()
        if not text or _paragraph_is_major_heading(para):
            continue
        _set_left_alignment(para)


def _should_center_heading_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return False
    return bool(re.match(
        r"(?i)^(chapter|sura(?:\s+ya)?|isahluko|chitsauko|hoofstuk|section|sehemu|isigaba)\b",
        clean,
    ))


def _left_align_table_of_contents(body: etree._Element, front_matter_end: int) -> None:
    """Force left alignment for TOC paragraphs and all front-matter content after cover."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_end = _find_preserved_front_end(body, pages=1)
    front_ids = {id(p) for p in direct_paragraphs[cover_end + 1: front_matter_end + 1]} if front_matter_end >= 0 else set()
    for para in body.findall(f".//{{{W}}}p"):
        text = _paragraph_text(para).strip()
        if not text:
            continue
        if _is_toc_paragraph(para) or id(para) in front_ids:
            _set_left_alignment(para)


def _center_title_paragraphs(body: etree._Element, cover_end: int) -> None:
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()
    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids:
            continue
        text = _paragraph_text(para).strip()
        if _should_center_heading_text(text):
            _set_center_alignment(para)


def _paragraph_has_dot_leader_tab(para: etree._Element) -> bool:
    for tab in para.findall(f".//{{{W}}}tab"):
        if tab.get(f"{{{W}}}leader") == "dot":
            return True
    return False


def _remove_toc_tab_leaders(para: etree._Element) -> None:
    p_pr = para.find(f"{{{W}}}pPr")
    if p_pr is not None:
        tabs = p_pr.find(f"{{{W}}}tabs")
        if tabs is not None:
            p_pr.remove(tabs)
    for run_tab in list(para.findall(f".//{{{W}}}r/{{{W}}}tab")):
        parent = run_tab.getparent()
        if parent is not None:
            parent.remove(run_tab)


def _strip_front_matter_toc_dot_leaders(body: etree._Element, front_matter_end: int) -> None:
    # TOC entries can live in tables/content controls. Restrict cleanup to front
    # matter so body content with ellipses/page-like numbers is not rewritten.
    direct_paragraphs = body.findall(f"{{{W}}}p")
    front_ids = {id(p) for p in direct_paragraphs[: front_matter_end + 1]} if front_matter_end >= 0 else set()
    for para in body.findall(f".//{{{W}}}p"):
        # Some TOC rows are nested in content controls/tables and are not direct
        # body paragraphs. Process those TOC paragraphs even if outside front_ids.
        if id(para) not in front_ids and not _is_toc_paragraph(para):
            continue
        text = _paragraph_text(para).strip()
        has_dot_tab = _paragraph_has_dot_leader_tab(para)
        if not text:
            if has_dot_tab:
                _remove_toc_tab_leaders(para)
            continue
        has_dot_text = bool(re.search(r"\.{3,}|…{2,}", text))
        if not has_dot_text and not has_dot_tab:
            continue
        clean = _strip_toc_dot_leaders(text)
        if not clean:
            # Dot-leader-only TOC rows can become visually empty but still carry tab
            # leader nodes; clear both text and leader tabs so no dotted line renders.
            _clear_paragraph_text(para)
            _remove_toc_tab_leaders(para)
            continue
        if len(clean) > 180:
            continue
        if (
            _line_looks_like_toc_candidate(clean)
            or _line_looks_like_toc_title(clean)
            or re.search(r"\d{1,4}$", clean)
        ):
            _replace_paragraph_text(para, clean)
            _remove_toc_tab_leaders(para)
            _set_left_alignment(para)


def _force_tail_promo_to_own_page(body: etree._Element, cover_end: int) -> None:
    direct_paragraphs = body.findall(f"{{{W}}}p")

    def _text_at(idx: int) -> str:
        return re.sub(r"\s+", " ", _paragraph_text(direct_paragraphs[idx]).strip())

    def _is_external_url_list_line(value: str) -> bool:
        clean = (value or "").strip().lower()
        return bool(re.match(r"^(?:\d+\s*)?(?:https?://|www\.)", clean)) and "tiuniversity.com" not in clean

    start_idx = None
    for idx, para in enumerate(direct_paragraphs):
        if idx <= cover_end:
            continue
        if _is_tail_promo_start_text(_paragraph_text(para)):
            start_idx = idx
            break

    if start_idx is None:
        anchor_idx = None
        for idx in range(len(direct_paragraphs) - 1, cover_end, -1):
            text = _text_at(idx).lower()
            if "tiuniversity.com" in text or "team impact christian university" in text:
                anchor_idx = idx
                break
        if anchor_idx is not None:
            # The closing promo is the block after the bibliography/Other URL list.
            search_start = max(cover_end + 1, anchor_idx - 12)
            last_external_url_idx = None
            for idx in range(search_start, anchor_idx):
                if _is_external_url_list_line(_text_at(idx)):
                    last_external_url_idx = idx
            if last_external_url_idx is not None:
                for idx in range(last_external_url_idx + 1, min(anchor_idx + 1, len(direct_paragraphs))):
                    if _text_at(idx):
                        start_idx = idx
                        break
            else:
                for idx in range(anchor_idx, search_start - 1, -1):
                    text = _text_at(idx)
                    if not text:
                        continue
                    prev_text = _text_at(idx - 1) if idx > cover_end + 1 else ""
                    if not prev_text or _is_external_url_list_line(prev_text):
                        start_idx = idx
                        break
                if start_idx is None:
                    start_idx = anchor_idx

    if start_idx is None:
        return

    p_pr = _ensure_p_pr(direct_paragraphs[start_idx])
    if p_pr.find(f"{{{W}}}pageBreakBefore") is None:
        p_pr.insert(0, etree.Element(f"{{{W}}}pageBreakBefore"))

    end_idx = min(len(direct_paragraphs), start_idx + 8)
    for promo_idx, promo_para in enumerate(direct_paragraphs[start_idx:end_idx], start=start_idx):
        promo_p_pr = _ensure_p_pr(promo_para)
        if promo_idx < end_idx - 1 and promo_p_pr.find(f"{{{W}}}keepNext") is None:
            promo_p_pr.append(etree.Element(f"{{{W}}}keepNext"))
        _set_center_alignment(promo_para)

def translate_docx_bytes(docx_bytes: bytes, translate_fn) -> bytes:
    """
    Translate a .docx file preserving cover page and all formatting.
    translate_fn: callable(list[str]) -> list[str]  (batch translate)
    """
    in_buf = io.BytesIO(docx_bytes)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zin, \
         zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:

        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename == "word/document.xml":
                tree = etree.fromstring(data)
                body = tree.find(f".//{{{W}}}body")

                cover_end = _find_preserved_front_end(body, pages=1)
                start_from = cover_end + 1 if cover_end >= 0 else 0

                run_pairs = _collect_runs(body, start_from)

                if run_pairs:
                    texts = [t for (_, t) in run_pairs]
                    translated = translate_fn(texts)
                    for (t_el, _), trans in zip(run_pairs, translated):
                        if trans != trans.strip():
                            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        t_el.text = trans

                data = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

            zout.writestr(item, data)

    return out_buf.getvalue()



def extract_docx_translation_text(docx_bytes: bytes) -> str:
    """Return visible DOCX text in the same paragraph order used by the DOCX renderer.
    Table cell text is appended after a @@TABLE_CELLS@@ separator so it gets
    translated but doesn't affect the main paragraph alignment."""
    in_buf = io.BytesIO(docx_bytes)
    with zipfile.ZipFile(in_buf, "r") as zin:
        tree = etree.fromstring(zin.read("word/document.xml"))
    body = tree.find(f".//{{{W}}}body")
    if body is None:
        return ""

    lines: list[str] = []
    for para in body.findall(f".//{{{W}}}p"):
        if _has_ancestor_named(para, {"txbxContent", "drawing", "pict", "AlternateContent"}):
            continue
        current = _paragraph_text(para).strip()
        if not current:
            continue
        if _looks_like_artifact_paragraph(para, current):
            continue
        if re.match(r"(https?://|www\.|mailto:|\S+@\S+\.\S+)", current):
            continue
        # Use text without superscript for translation
        translatable = _paragraph_text_no_superscript(para).strip() or current
        lines.append(translatable)

    return "\n".join(lines)

def apply_translated_paragraphs_to_docx_bytes(docx_bytes: bytes, translated_text: str) -> bytes:
    """
    Apply cached translated text to the original DOCX in-place.

    This preserves the original DOCX layout, including tables/images/sections,
    and relies on LibreOffice for PDF layout. It intentionally does not rebuild
    the TOC because the original-tables renderer kept the Word structure intact.
    """
    translated_lines = [line.strip() for line in (translated_text or "").splitlines() if line.strip()]
    # Count non-empty lines in the preserved cover so we skip exactly that many
    # translated lines before starting paragraph replacements.
    _tmp_body = etree.fromstring(
        zipfile.ZipFile(io.BytesIO(docx_bytes)).read("word/document.xml")
    ).find(f".//{{{W}}}body")
    _cover_end = _find_preserved_front_end(_tmp_body, pages=1) if _tmp_body is not None else -1
    _cover_line_count = sum(
        1 for p in (_tmp_body.findall(f"{{{W}}}p") if _tmp_body is not None else [])[:_cover_end + 1]
        if _paragraph_text(p).strip()
    ) if _cover_end >= 0 else PRESERVED_FRONT_TRANSLATED_LINES
    line_index = min(_cover_line_count, len(translated_lines))
    in_buf = io.BytesIO(docx_bytes)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename == "word/document.xml":
                tree = etree.fromstring(data)
                body = tree.find(f".//{{{W}}}body")
                if body is not None:
                    _body_paragraphs = body.findall(f".//{{{W}}}p")
                    _toc_title_seen = False
                    for _idx, _para in enumerate(_body_paragraphs[:120]):
                        _text = re.sub(r"\s+", " ", _paragraph_text(_para).strip())
                        if not _text or not _line_looks_like_toc_title(_text):
                            continue
                        if not _toc_title_seen:
                            _toc_title_seen = True
                            continue
                        if _has_ancestor_named(_para, {"txbxContent", "drawing", "pict", "AlternateContent"}):
                            continue
                        _parent = _para.getparent()
                        while _parent is not None and etree.QName(_parent).localname != "body":
                            _parent = _parent.getparent()
                        if _parent is not None:
                            try:
                                _parent.remove(_para)
                            except Exception:
                                _direct_parent = _para.getparent()
                                if _direct_parent is not None:
                                    _direct_parent.remove(_para)
                    cover_end = _find_preserved_front_end(body, pages=1)
                    front_matter_end = _find_front_matter_end(body)
                    _remove_body_empty_section_breaks(body, front_matter_end)
                    _tighten_page_margins(body, front_matter_end)
                    _remove_empty_body_paragraphs(body, front_matter_end)
                    for para in _iter_translatable_paragraphs(body, cover_end):
                        current_text = _paragraph_text(para).strip()
                        if line_index >= len(translated_lines):
                            break
                        # Keep copyright/attribution lines untouched, but allow
                        # "All rights reserved..." paragraphs to translate.
                        if _is_copyright_line(current_text):
                            line_index += 1
                            continue
                        replacement = translated_lines[line_index]
                        if _is_toc_paragraph(para):
                            # Strip trailing page number from translated text
                            toc_match = re.match(r"^(.+?)(\d{1,4})\s*$", replacement)
                            if toc_match:
                                replacement = toc_match.group(1).strip()
                            # Only replace text nodes BEFORE the tab — leave tab + page number intact
                            all_t = para.findall(f".//{{{W}}}t")
                            # Find which t nodes are before vs after the tab
                            tab_found = False
                            before_tab = []
                            for _r in para.findall(f".//{{{W}}}r"):
                                if _r.find(f"{{{W}}}tab") is not None:
                                    tab_found = True
                                    continue
                                for _t in _r.findall(f"{{{W}}}t"):
                                    if not tab_found:
                                        before_tab.append(_t)
                            # Also check inside hyperlinks
                            for _hl in para.findall(f".//{{{W}}}hyperlink"):
                                for _r in _hl.findall(f"{{{W}}}r"):
                                    if _r.find(f"{{{W}}}tab") is not None:
                                        tab_found = True
                                        continue
                                    for _t in _r.findall(f"{{{W}}}t"):
                                        if not tab_found:
                                            before_tab.append(_t)
                            if before_tab:
                                before_tab[0].text = replacement
                                for _t in before_tab[1:]:
                                    _t.text = ""
                                line_index += 1
                                continue
                        _replace_paragraph_text(para, replacement)
                        line_index += 1

                    # Keep the original document structure as intact as possible.
                    # Avoid post-processing that can alter page flow for workbook PDFs.
                    _left_align_body_paragraphs(body, cover_end)
                    _center_title_paragraphs(body, cover_end)
                    _force_tail_promo_to_own_page(body, cover_end)
                    _left_align_table_of_contents(body, front_matter_end)

                data = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

            elif item.filename == "word/styles.xml":
                pass  # Keep styles.xml unchanged

            zout.writestr(item, data)

    return out_buf.getvalue()
