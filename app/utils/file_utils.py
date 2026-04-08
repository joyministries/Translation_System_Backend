import os
import uuid
import magic

from app.config import settings


ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}


def validate_mime_type(file_bytes: bytes) -> str | None:
    mime = magic.from_buffer(file_bytes[:2048], mime=True)
    return mime if mime in ALLOWED_MIME_TYPES else None


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
