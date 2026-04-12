from fastapi import APIRouter

from app.routers.admin import (
    books,
    exams,
    answer_keys,
    languages,
    translations,
    content,
    users,
)

router = APIRouter(prefix="/admin")

router.include_router(books.router)
router.include_router(exams.router)
router.include_router(answer_keys.router)
router.include_router(languages.router)
router.include_router(translations.router)
router.include_router(content.router)
router.include_router(users.router)
