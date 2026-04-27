from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exam
from app.utils.file_utils import validate_mime_type, save_upload_securely
from app.services.excel_service import parse_excel


router = APIRouter(prefix="/exams", tags=["Exams Management"])


@router.post("/import")
async def import_exam(
    file: UploadFile = File(...),
    title: str = "",
    book_id: str | None = None,
    answer_key_id: str | None = None,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    mime_type = validate_mime_type(file_bytes, file.filename or "")
    if not mime_type:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only Excel allowed."
        )

    filename = save_upload_securely(file_bytes, mime_type)

    raw_data = parse_excel(filename)

    exam = Exam(
        title=title or file.filename,
        file_path=filename,
        raw_data=raw_data,
        book_id=book_id,
        uploaded_by=None,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    if answer_key_id:
        from app.models import AnswerKey

        answer_key = db.query(AnswerKey).filter(AnswerKey.id == answer_key_id).first()
        if answer_key:
            answer_key.exam_id = exam.id
            db.commit()

    return {
        "id": str(exam.id),
        "title": exam.title,
        "sheet_names": raw_data["sheet_names"],
        "total_sheets": raw_data["total_sheets"],
    }


@router.get("/")
def list_exams(
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = Query(
        None, description="Filter by content_type: book, exam, or answer_key"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Exam)

    total = query.count()
    exams = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "exams": [
            {
                "id": str(e.id),
                "title": e.title,
                "content_type": "exam",
                "sheet_names": e.raw_data.get("sheet_names", []) if e.raw_data else [],
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exams
        ],
    }
