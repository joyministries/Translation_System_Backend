from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exam
from app.utils.file_utils import validate_mime_type, save_upload_securely
from app.services.excel_service import parse_excel


router = APIRouter(prefix="/admin/exams", tags=["admin", "exams"])


@router.post("/import")
async def import_exam(
    file: UploadFile = File(...),
    title: str = "",
    institution_id: str | None = None,
    book_id: str | None = None,
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

    exam = Exam(
        title=title or file.filename,
        file_path=filename,
        raw_data=raw_data,
        institution_id=institution_id,
        book_id=book_id,
        uploaded_by="00000000-0000-0000-0000-000000000000",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

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
    institution_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Exam)
    if institution_id:
        query = query.filter(Exam.institution_id == institution_id)

    total = query.count()
    exams = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "exams": [
            {
                "id": str(e.id),
                "title": e.title,
                "sheet_names": e.raw_data.get("sheet_names", []) if e.raw_data else [],
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exams
        ],
    }
