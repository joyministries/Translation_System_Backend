import os
import uuid
import magic

from app.config import settings


ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def validate_mime_type(file_bytes: bytes) -> str | None:
    mime = magic.from_buffer(file_bytes[:2048], mime=True)

    if mime in ALLOWED_MIME_TYPES:
        return mime

    # OLE compound document - check for Excel vs Word
    if file_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        # Check for Excel markers at specific offsets
        if file_bytes[0x18:0x1C] == b"\x00\x00\x00\x00":
            return "application/vnd.ms-excel"
        # Default to Excel for .xls extension files - will be corrected by filename
        return "application/vnd.ms-excel"

    return None


def save_upload_securely(file_bytes: bytes, mime_type: str) -> str:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Invalid file type: {mime_type}")

    extension = ALLOWED_MIME_TYPES[mime_type]
    filename = f"{uuid.uuid4()}{extension}"

    storage_path = os.path.join(settings.STORAGE_ROOT, filename)
    os.makedirs(settings.STORAGE_ROOT, exist_ok=True)

    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    return filename


def get_file_path(filename: str) -> str:
    return os.path.join(settings.STORAGE_ROOT, filename)


def delete_file(filename: str) -> bool:
    file_path = get_file_path(filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
