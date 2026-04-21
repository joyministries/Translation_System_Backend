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


def _find_cover_end(body: etree._Element) -> int:
    """Return index of last paragraph on cover page, or -1 if none found."""
    for idx, para in enumerate(body.findall(f"{{{W}}}p")):
        if para.find(f".//{{{W}}}sectPr") is not None:
            return idx
        for br in para.findall(f".//{{{W}}}br"):
            if br.get(f"{{{W}}}type", "") == "page":
                return idx
    return -1


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

                cover_end = _find_cover_end(body)
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
