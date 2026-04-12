from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnswerKey
from app.utils.file_utils import validate_mime_type, save_upload_securely
from app.services.excel_service import parse_excel


router = APIRouter(prefix="/answer-keys", tags=["Answer Keys Management"])


@router.post("/import")
async def import_answer_key(
    file: UploadFile = File(...),
    title: str = "",
    institution_id: str | None = None,
    book_id: str | None = None,
    exam_id: str | None = None,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    mime_type = validate_mime_type(file_bytes)
    if not mime_type:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only Excel allowed."
        )

    filename = save_upload_securely(file_bytes, mime_type)

    raw_data = parse_excel(filename)

    answer_key = AnswerKey(
        title=title or file.filename,
        file_path=filename,
        raw_data=raw_data,
        institution_id=institution_id,
        book_id=book_id,
        exam_id=exam_id,
        uploaded_by=None,
    )
    db.add(answer_key)
    db.commit()
    db.refresh(answer_key)

    return {
        "id": str(answer_key.id),
        "title": answer_key.title,
        "sheet_names": raw_data["sheet_names"],
        "total_sheets": raw_data["total_sheets"],
    }


@router.get("/")
def list_answer_keys(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book, exam, or answer_key"
    ),
    exam_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(AnswerKey)
    if exam_id:
        query = query.filter(AnswerKey.exam_id == exam_id)

    total = query.count()
    answer_keys = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "answer_keys": [
            {
                "id": str(a.id),
                "title": a.title,
                "content_type": "answer_key",
                "exam_id": str(a.exam_id) if a.exam_id else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in answer_keys
        ],
    }
