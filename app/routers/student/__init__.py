from fastapi import APIRouter

from app.routers.student import translate
from app.routers.student import content

router = APIRouter(prefix="/student")

router.include_router(translate.router)
router.include_router(content.router)
