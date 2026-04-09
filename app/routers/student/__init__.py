from fastapi import APIRouter

from app.routers.student import translate

router = APIRouter(prefix="/student")

router.include_router(translate.router)
