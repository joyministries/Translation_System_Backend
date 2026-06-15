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
    """Return the last paragraph index in the preserved front matter pages."""
    page_breaks_seen = 0
    last_break_idx = -1
    for idx, para in enumerate(body.findall(f"{{{W}}}p")):
        has_page_boundary = para.find(f".//{{{W}}}sectPr") is not None
        for br in para.findall(f".//{{{W}}}br"):
            if br.get(f"{{{W}}}type", "") == "page":
                has_page_boundary = True
                break
        if has_page_boundary:
            page_breaks_seen += 1
            last_break_idx = idx
            if page_breaks_seen >= pages:
                return idx
    return last_break_idx


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


def _replace_paragraph_text(para: etree._Element, replacement: str) -> None:
    replacement = _protect_connector_line_breaks(replacement)
    text_nodes = para.findall(f".//{{{W}}}t")
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
        if _is_toc_paragraph(para):
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
        r"(?i)^(chapter|section|part|appendix|bibliography|preface|introduction|course introduction|"
        r"sura|sehemu|dibaji|utangulizi|bibliografia|"
        r"isahluko|isigaba|isingeniso|"
        r"chitsauko|nhanganyaya|"
        r"hoofstuk|afdeling|voorwoord|inleiding)\b",
        clean,
    ))


def _line_looks_like_toc_title(line: str) -> bool:
    return bool(re.search(r"(?i)(contents|yaliyomo|okuqukethwe|zviri\s+mukati|inhoud)", line or ""))


def _strip_toc_dot_leaders(text: str) -> str:
    """Keep TOC entry text/page numbers, but remove dotted leader fill."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    clean = re.sub(r"\.{3,}|…{2,}", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _apply_translated_toc_entries(body: etree._Element, translated_lines: list[str]) -> None:
    toc_paras = [
        para
        for para in body.findall(f".//{{{W}}}p")
        if _is_toc_paragraph(para) and _paragraph_text(para).strip()
    ]
    if not toc_paras:
        return

    start = 0
    for idx, line in enumerate(translated_lines):
        if _line_looks_like_toc_title(line):
            start = idx
            break

    candidates: list[str] = []
    seen: set[str] = set()
    for line in translated_lines[start + 1:]:
        clean = _strip_toc_dot_leaders(line)
        if _line_looks_like_toc_title(clean):
            continue
        if not _line_looks_like_toc_candidate(clean):
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(clean)
        if len(candidates) >= len(toc_paras):
            break

    for para, replacement in zip(toc_paras, candidates):
        _replace_paragraph_text(para, replacement)


def _remove_child(parent: etree._Element | None, child_name: str) -> None:
    if parent is None:
        return
    child = parent.find(f"{{{W}}}{child_name}")
    if child is not None:
        parent.remove(child)


def _relax_pagination_constraints(body: etree._Element, cover_end: int) -> None:
    """Let translated text split naturally instead of pushing whole blocks to the next page."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids:
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
        r"^(?:CHAPTER|SURA(?:\s+YA)?|CHITSAUKO|CHAPITRE|CAP[IÍ]TULO|ORI|ISAHLUKO|HOOFSTUK|ÌSỌRÍ|SECTION|SEHEMU|ISIGABA|UTANGULIZI|INTRODUCTION|COURSE\s+INTRODUCTION)\b",
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
    """Remove source page-boundary section breaks that orphan translated paragraphs."""
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
    """Remove style-level pagination locks inherited by translated paragraphs."""
    for style in root.findall(f".//{{{W}}}style"):
        p_pr = style.find(f"{{{W}}}pPr")
        if p_pr is None:
            continue
        _remove_child(p_pr, "keepNext")
        _remove_child(p_pr, "keepLines")
        _remove_child(p_pr, "widowControl")
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
        if has_text or has_drawing or has_section:
            keep_one_blank = False
            continue
        if keep_one_blank:
            parent = para.getparent()
            if parent is not None:
                parent.remove(para)
            continue
        keep_one_blank = True


def _normalize_body_spacing(body: etree._Element, cover_end: int) -> None:
    """Remove stale source pagination spacing while preserving real structure."""
    direct_paragraphs = body.findall(f"{{{W}}}p")
    cover_ids = {id(p) for p in direct_paragraphs[: cover_end + 1]} if cover_end >= 0 else set()

    for para in body.findall(f".//{{{W}}}p"):
        if id(para) in cover_ids or _is_toc_paragraph(para):
            continue
        text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
        if not text:
            continue

        p_pr = _ensure_p_pr(para)
        if not _is_major_body_start_text(text) and not _is_tail_promo_start_text(text):
            _remove_child(p_pr, "pageBreakBefore")

        if _is_major_body_start_text(text):
            _set_spacing_twips(para, before="120", after="60")
        elif _paragraph_is_major_heading(para) or (text.isupper() and len(text) <= 180):
            _set_spacing_twips(para, before="120", after="40")
        elif _paragraph_alignment(para) == "center":
            _set_spacing_twips(para, before="60", after="40")
        else:
            _set_spacing_twips(para, before="0", after="0")


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
    text = re.sub(r"\s+", " ", _paragraph_text(para).strip())
    style = _paragraph_style_value(para).lower()
    if not text:
        return False
    if style in {"heading1", "heading2", "title"}:
        return True
    return bool(re.match(
        r"(?i)^(chapter|section|part|sura|sehemu|utangulizi|isahluko|isigaba|isingeniso|chitsauko|hoofstuk|yaliyomo|okuqukethwe|contents)\b",
        text,
    ))


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


def _set_paragraph_line_spacing(para: etree._Element, line_twips: str = "252") -> None:
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
        _set_paragraph_line_spacing(para)


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
    if _line_looks_like_toc_title(clean):
        return True
    return bool(re.match(
        r"(?i)^(chapter|sura(?:\s+ya)?|isahluko|chitsauko|hoofstuk|section|sehemu|isigaba)\b",
        clean,
    ))


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
    # TOC entries can live in tables/content controls, so scan all paragraphs.
    for para in body.findall(f".//{{{W}}}p"):
        text = _paragraph_text(para).strip()
        if not text:
            continue
        has_dot_text = bool(re.search(r"\.{3,}|…{2,}", text))
        has_dot_tab = _paragraph_has_dot_leader_tab(para)
        if not has_dot_text and not has_dot_tab:
            continue
        clean = _strip_toc_dot_leaders(text)
        if not clean or len(clean) > 180:
            continue
        if _line_looks_like_toc_candidate(clean) or _line_looks_like_toc_title(clean):
            _replace_paragraph_text(para, clean)
            _remove_toc_tab_leaders(para)
            if _line_looks_like_toc_title(clean):
                _set_center_alignment(para)
            else:
                _set_left_alignment(para)


def _force_tail_promo_to_own_page(body: etree._Element, cover_end: int) -> None:
    direct_paragraphs = body.findall(f"{{{W}}}p")
    for idx, para in enumerate(direct_paragraphs):
        if idx <= cover_end:
            continue
        if not _is_tail_promo_start_text(_paragraph_text(para)):
            continue
        p_pr = _ensure_p_pr(para)
        if p_pr.find(f"{{{W}}}pageBreakBefore") is None:
            p_pr.insert(0, etree.Element(f"{{{W}}}pageBreakBefore"))
        end_idx = min(len(direct_paragraphs), idx + 6)
        for promo_idx, promo_para in enumerate(direct_paragraphs[idx:end_idx], start=idx):
            promo_p_pr = _ensure_p_pr(promo_para)
            if promo_idx < end_idx - 1 and promo_p_pr.find(f"{{{W}}}keepNext") is None:
                promo_p_pr.append(etree.Element(f"{{{W}}}keepNext"))
            _set_center_alignment(promo_para)
        return

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
    """Return visible DOCX text in the same paragraph order used by the DOCX renderer."""
    in_buf = io.BytesIO(docx_bytes)
    with zipfile.ZipFile(in_buf, "r") as zin:
        tree = etree.fromstring(zin.read("word/document.xml"))
    body = tree.find(f".//{{{W}}}body")
    if body is None:
        return ""

    lines: list[str] = []
    for para in body.findall(f".//{{{W}}}p"):
        if _is_toc_paragraph(para):
            continue
        if _has_ancestor_named(para, {"txbxContent", "drawing", "pict", "AlternateContent"}):
            continue
        current = _paragraph_text(para).strip()
        if not current:
            continue
        if _looks_like_artifact_paragraph(para, current):
            continue
        if re.match(r"(https?://|www\.|mailto:|\S+@\S+\.\S+)", current):
            continue
        lines.append(current)
    return "\n".join(lines)

def apply_translated_paragraphs_to_docx_bytes(docx_bytes: bytes, translated_text: str) -> bytes:
    """
    Apply cached translated text to the original DOCX in-place.

    This preserves the original DOCX layout, including tables/images/sections,
    and relies on LibreOffice for PDF layout. It intentionally does not rebuild
    the TOC because the original-tables renderer kept the Word structure intact.
    """
    translated_lines = [line.strip() for line in (translated_text or "").splitlines() if line.strip()]
    if translated_lines:
        deduped_lines = []
        prev_norm = None
        for line in translated_lines:
            norm = re.sub(r'\s+', ' ', line).upper()
            if norm and norm == prev_norm:
                continue
            deduped_lines.append(line)
            prev_norm = norm
        translated_lines = deduped_lines
    # The workbook structure preserves only the cover page unchanged. Cached
    # translated text still contains that cover line, so skip it before applying
    # translations to the title/manual/body pages.
    line_index = min(PRESERVED_FRONT_TRANSLATED_LINES, len(translated_lines))
    in_buf = io.BytesIO(docx_bytes)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename == "word/document.xml":
                tree = etree.fromstring(data)
                body = tree.find(f".//{{{W}}}body")
                if body is not None:
                    _apply_translated_toc_entries(body, translated_lines)
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
                    _body_paragraphs = body.findall(f".//{{{W}}}p")
                    for _idx in range(len(_body_paragraphs) - 1):
                        _current_text = re.sub(r"\s+", " ", _paragraph_text(_body_paragraphs[_idx]).strip())
                        _next_text = re.sub(r"\s+", " ", _paragraph_text(_body_paragraphs[_idx + 1]).strip())
                        if not _current_text or _current_text != _next_text:
                            continue
                        _current_para = _body_paragraphs[_idx]
                        if _has_ancestor_named(_current_para, {"txbxContent", "drawing", "pict", "AlternateContent"}):
                            continue
                        parent = _current_para.getparent()
                        if parent is not None:
                            parent.remove(_current_para)
                    cover_end = _find_preserved_front_end(body, pages=1)
                    format_start = _find_body_start_after_toc(body, cover_end)
                    front_matter_end = max(cover_end, format_start - 1)
                    _relax_pagination_constraints(body, front_matter_end)
                    _remove_body_empty_section_breaks(body, front_matter_end)
                    _tighten_page_margins(body, front_matter_end)
                    _remove_empty_body_paragraphs(body, front_matter_end)
                    for para in _iter_translatable_paragraphs(body, cover_end):
                        current_text = _paragraph_text(para).strip()
                        if _line_looks_like_toc_title(current_text):
                            toc_line_index = next(
                                (idx for idx in range(line_index, len(translated_lines)) if _line_looks_like_toc_title(translated_lines[idx])),
                                line_index,
                            )
                            if toc_line_index < len(translated_lines):
                                _replace_paragraph_text(para, translated_lines[toc_line_index])
                                line_index = toc_line_index + 1
                            continue

                        if line_index >= len(translated_lines):
                            break
                        if _is_legal_credit_text(current_text):
                            line_index += 1
                            continue
                        _replace_paragraph_text(para, translated_lines[line_index])
                        line_index += 1

                    # Keep front-matter page boundaries, but avoid distributed/justified text stretching there.
                    _left_align_body_paragraphs(body, cover_end)
                    _center_title_paragraphs(body, cover_end)
                    _strip_front_matter_toc_dot_leaders(body, front_matter_end)
                    _increase_body_font_size(body, cover_end)
                    _normalize_body_spacing(body, front_matter_end)
                    _normalize_flow_paragraphs(body, front_matter_end)
                    _merge_lowercase_continuations(body, front_matter_end)
                    _normalize_body_spacing(body, front_matter_end)
                    _inline_translated_bullets(body, front_matter_end)
                    _force_tail_promo_to_own_page(body, front_matter_end)

                data = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

            elif item.filename == "word/styles.xml":
                tree = etree.fromstring(data)
                _relax_style_pagination_constraints(tree)
                data = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

            zout.writestr(item, data)

    return out_buf.getvalue()
