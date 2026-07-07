from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    LIBRETRANSLATE_URL: str = "https://libretranslate.com"
    STORAGE_ROOT: str = "/app/storage"
    DB_PASSWORD: str
    REDIS_PASSWORD: str
    GOOGLE_CLOUD_API_KEY: str | None = None
    CONVERTAPI_TOKEN: str | None = None
    CONVERTAPI_REGION: str = "v2"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_IDLE_TIMEOUT_MINUTES: int = 1440

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@curriculum.edu"
    FRONTEND_URL: str = "http://localhost:3000"

    ALLOWED_MIME_TYPES: str = "application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    MAX_UPLOAD_SIZE_MB: int = 50

    API_V1_PREFIX: str = "/api/v1"


settings = Settings()
