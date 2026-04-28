from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.database import engine, Base

from app.routers import admin, student, auth
from fastapi import APIRouter

Base.metadata.create_all(bind=engine)

# Run seed on startup (safe — skips if data already exists)
try:
    from seed import seed
    seed()
except Exception:
    pass

app = FastAPI(
    title="Curriculum Translation API",
    description="Translate educational content between languages. Paste your Bearer token in the Authorize button above.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(student.router)

# Shared translations router (no student/admin prefix)
from app.routers.student.translate import list_book_translations, list_exam_translations
from app.database import get_db
from app.models.user import User
from app.utils.security import require_role
from fastapi import Depends

shared_router = APIRouter(prefix="/translations", tags=["Translations"])

@shared_router.get("/book/{book_id}")
def shared_list_book_translations(book_id: str, current_user: User = Depends(require_role("admin","student","teacher","translator")), db=Depends(get_db)):
    return list_book_translations(book_id, current_user, db)

@shared_router.get("/exam/{exam_id}")
def shared_list_exam_translations(exam_id: str, current_user: User = Depends(require_role("admin","student","teacher","translator")), db=Depends(get_db)):
    return list_exam_translations(exam_id, current_user, db)

@shared_router.get("/{translation_id}/download")
def shared_download(translation_id: str, format: str = "pdf", current_user: User = Depends(require_role("admin","student","teacher","translator")), db=Depends(get_db)):
    from app.routers.student.translate import download_translation
    return download_translation(translation_id, format, current_user, db)

app.include_router(shared_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in schema.get("paths", {}).values():
        for op in path.values():
            op["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Curriculum Translation System API"}
