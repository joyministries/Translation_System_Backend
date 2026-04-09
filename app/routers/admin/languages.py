from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.language import LanguageCreate, LanguageUpdate, LanguageResponse
from app.services.language_service import LanguageService


router = APIRouter(prefix="/admin/languages", tags=["admin", "languages"])


@router.get("", response_model=list[LanguageResponse])
def list_languages(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return LanguageService.list_languages(db, skip, limit)


@router.post("", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED)
def create_language(
    language: LanguageCreate,
    db: Session = Depends(get_db),
):
    existing = LanguageService.get_language_by_code(db, language.code)
    if existing:
        raise HTTPException(
            status_code=400, detail="Language with this code already exists"
        )
    return LanguageService.create_language(db, language.model_dump())


@router.get("/{language_id}", response_model=LanguageResponse)
def get_language(language_id: int, db: Session = Depends(get_db)):
    language = LanguageService.get_language(db, language_id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    return language


@router.patch("/{language_id}", response_model=LanguageResponse)
def update_language(
    language_id: int,
    language: LanguageUpdate,
    db: Session = Depends(get_db),
):
    language_obj = LanguageService.get_language(db, language_id)
    if not language_obj:
        raise HTTPException(status_code=404, detail="Language not found")
    update_data = language.model_dump(exclude_unset=True)
    return LanguageService.update_language(db, language_id, update_data)


@router.post("/{language_id}/activate", response_model=LanguageResponse)
def activate_language(language_id: int, db: Session = Depends(get_db)):
    language = LanguageService.activate_language(db, language_id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    return language


@router.post("/{language_id}/deactivate", response_model=LanguageResponse)
def deactivate_language(language_id: int, db: Session = Depends(get_db)):
    language = LanguageService.deactivate_language(db, language_id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    return language
