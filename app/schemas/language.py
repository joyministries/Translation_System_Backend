from pydantic import BaseModel


class LanguageBase(BaseModel):
    name: str
    code: str
    native_name: str | None = None
    libretranslate_code: str | None = None


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    name: str | None = None
    native_name: str | None = None
    libretranslate_code: str | None = None
    is_active: bool | None = None


class LanguageResponse(LanguageBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
