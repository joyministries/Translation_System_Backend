"""Translation Text Format Fixer — cleans up translated text formatting issues."""

import re


def fix_translation_format(text: str, source_text: str | None = None) -> str:
    """Fix all common formatting issues in translated text.
    
    Handles:
    - Extra blank lines (collapse to max 1 blank line)
    - Page headers/footers (e.g., "CC101 Misingi ya Kikristo 7")
    - Inconsistent paragraph spacing
    - Broken hyphenation/word splits
    - Leading/trailing whitespace on lines
    """
    if not text or not text.strip():
        return text

    lines = text.split("\n")
    fixed_lines = []
    
    # Pattern to match page headers like "CC101 Misingi ya Kikristo 5" or "CHRISTIAN FOUNDATIONS 6"
    # These typically appear as: [CourseCode] [Title] [PageNumber] or just [Title] [PageNumber]
    page_header_pattern = re.compile(
        r'^(?:CC\d+|CHAPTER|SURA)\s+.*\s+\d+$',
        re.IGNORECASE
    )
    
    # Pattern for lines that are just page numbers
    page_number_pattern = re.compile(r'^\d+$')
    
    # Pattern for TOC entries with dot leaders (preserve these)
    toc_pattern = re.compile(r'\.{3,}\s*\d+\s*$')
    
    # Pattern for hyphenated word breaks at end of line
    hyphen_break_pattern = re.compile(r'(\w+)-\s*$')
    
    # First pass: clean up individual lines
    cleaned_lines = []
    for line in lines:
        # Strip trailing whitespace but preserve leading whitespace for indentation
        line = line.rstrip()
        
        # Skip empty page headers
        if page_header_pattern.match(line):
            continue
        
        # Skip standalone page numbers (but not in TOC)
        if page_number_pattern.match(line):
            # Check if previous or next line suggests this is a page number
            if cleaned_lines and not cleaned_lines[-1].strip():
                continue
        
        cleaned_lines.append(line)
    
    # Second pass: fix hyphenation and join broken lines
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]
        
        # Check if line ends with hyphenated word
        if hyphen_break_pattern.match(line) and i + 1 < len(cleaned_lines):
            next_line = cleaned_lines[i + 1].lstrip()
            # If next line starts with lowercase, likely a continuation
            if next_line and next_line[0].islower():
                # Remove hyphen and join
                fixed_line = hyphen_break_pattern.sub(r'\1', line) + next_line
                cleaned_lines[i] = fixed_line
                cleaned_lines.pop(i + 1)
                continue
        
        # Check if line is incomplete sentence (no ending punctuation) and next line continues
        if (line.strip() and 
            not line.strip().endswith(('.', '!', '?', ':', ';', '—')) and
            i + 1 < len(cleaned_lines) and
            cleaned_lines[i + 1].strip() and
            cleaned_lines[i + 1].strip()[0].islower()):
            # Join lines
            fixed_line = line.rstrip() + ' ' + cleaned_lines[i + 1].lstrip()
            cleaned_lines[i] = fixed_line
            cleaned_lines.pop(i + 1)
            continue
        
        i += 1
    
    # Third pass: collapse multiple blank lines into single blank lines
    result_lines = []
    prev_blank = False
    for line in cleaned_lines:
        is_blank = not line.strip()
        if is_blank:
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(line)
            prev_blank = False
    
    # Remove leading/trailing blank lines
    while result_lines and not result_lines[0].strip():
        result_lines.pop(0)
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()
    
    return "\n".join(result_lines)


def fix_translation_in_db(db_session, translation_id: str) -> dict:
    """Fix formatting for a specific translation in the database.
    
    Returns dict with status and stats.
    """
    from app.models import Translation
    import uuid
    
    try:
        trans_uuid = uuid.UUID(translation_id)
    except ValueError:
        return {"status": "error", "message": "Invalid translation ID"}
    
    translation = db_session.query(Translation).filter(Translation.id == trans_uuid).first()
    if not translation:
        return {"status": "error", "message": "Translation not found"}
    
    if translation.status != "done" or not translation.translated_text:
        return {"status": "error", "message": "Translation not complete or empty"}
    
    original_length = len(translation.translated_text)
    original_lines = translation.translated_text.count("\n")
    
    fixed_text = fix_translation_format(translation.translated_text)
    
    fixed_length = len(fixed_text)
    fixed_lines = fixed_text.count("\n")
    
    translation.translated_text = fixed_text
    db_session.commit()
    
    return {
        "status": "success",
        "translation_id": translation_id,
        "original_length": original_length,
        "fixed_length": fixed_length,
        "original_lines": original_lines,
        "fixed_lines": fixed_lines,
        "reduction_percent": round((1 - fixed_length / original_length) * 100, 1) if original_length > 0 else 0,
    }


def fix_all_translations_for_language(db_session, language_id: int) -> dict:
    """Fix formatting for all completed translations of a specific language.
    
    Returns dict with status and stats.
    """
    from app.models import Translation
    
    translations = (
        db_session.query(Translation)
        .filter(
            Translation.language_id == language_id,
            Translation.status == "done",
            Translation.translated_text.isnot(None),
        )
        .all()
    )
    
    results = {
        "total": len(translations),
        "fixed": 0,
        "errors": 0,
        "details": [],
    }
    
    for translation in translations:
        try:
            result = fix_translation_in_db(db_session, str(translation.id))
            if result["status"] == "success":
                results["fixed"] += 1
                results["details"].append({
                    "translation_id": str(translation.id),
                    "content_type": translation.content_type,
                    "reduction_percent": result["reduction_percent"],
                })
            else:
                results["errors"] += 1
        except Exception as e:
            results["errors"] += 1
            results["details"].append({
                "translation_id": str(translation.id),
                "error": str(e),
            })
    
    return results
