import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from app.database import SessionLocal, engine
from app.models import Language, Institution
from app.utils.security import get_password_hash


LANGUAGES = [
    {
        "name": "Kiswahili",
        "code": "sw",
        "native_name": "Kiswahili",
        "libretranslate_code": "sw",
    },
    {
        "name": "Hausa",
        "code": "ha",
        "native_name": "Hausa",
        "libretranslate_code": "ha",
    },
    {
        "name": "Yoruba",
        "code": "yo",
        "native_name": "Èdè Yorùbá",
        "libretranslate_code": "yo",
    },
    {
        "name": "Igbo",
        "code": "ig",
        "native_name": "Asụsụ Igbo",
        "libretranslate_code": "ig",
    },
    {
        "name": "Amharic",
        "code": "am",
        "native_name": "አማርኛ",
        "libretranslate_code": "am",
    },
    {
        "name": "Zulu",
        "code": "zu",
        "native_name": "isiZulu",
        "libretranslate_code": "zu",
    },
    {
        "name": "Somali",
        "code": "so",
        "native_name": "Soomaali",
        "libretranslate_code": "so",
    },
    {
        "name": "Kinyarwanda",
        "code": "rw",
        "native_name": "Ikinyarwanda",
        "libretranslate_code": "rw",
    },
    {
        "name": "Afrikaans",
        "code": "af",
        "native_name": "Afrikaans",
        "libretranslate_code": "af",
    },
    {
        "name": "Xhosa",
        "code": "xh",
        "native_name": "isiXhosa",
        "libretranslate_code": None,
    },
    {
        "name": "Shona",
        "code": "sn",
        "native_name": "chiShona",
        "libretranslate_code": None,
    },
    {
        "name": "Oromo",
        "code": "om",
        "native_name": "Afaan Oromoo",
        "libretranslate_code": None,
    },
    {
        "name": "Wolof",
        "code": "wo",
        "native_name": "Wolof",
        "libretranslate_code": None,
    },
    {
        "name": "Lingala",
        "code": "ln",
        "native_name": "Lingala",
        "libretranslate_code": None,
    },
    {
        "name": "Luganda",
        "code": "lg",
        "native_name": "Luganda",
        "libretranslate_code": None,
    },
    {
        "name": "Chichewa",
        "code": "ny",
        "native_name": "Chichewa",
        "libretranslate_code": None,
    },
    {
        "name": "Tigrinya",
        "code": "ti",
        "native_name": "ትግርኛ",
        "libretranslate_code": None,
    },
    {
        "name": "Dholuo",
        "code": "luo",
        "native_name": "Dholuo",
        "libretranslate_code": None,
    },
    {
        "name": "Fula",
        "code": "ff",
        "native_name": "Fulfulde",
        "libretranslate_code": None,
    },
    {"name": "Twi", "code": "tw", "native_name": "Twi", "libretranslate_code": None},
]

INSTITUTIONS = [
    {"name": "University of Nairobi", "code": "UON"},
    {"name": "University of Ghana", "code": "UG"},
    {"name": "University of Lagos", "code": "UL"},
]

USERS = [
    {
        "email": "admin@curriculum.edu",
        "password": "admin123",
        "role": "admin",
        "institution_code": None,
    },
    {
        "email": "teacher@curriculum.edu",
        "password": "teacher123",
        "role": "teacher",
        "institution_code": "UON",
    },
    {
        "email": "student@curriculum.edu",
        "password": "student123",
        "role": "student",
        "institution_code": "UON",
    },
    {
        "email": "translator@curriculum.edu",
        "password": "translator123",
        "role": "translator",
        "institution_code": "UON",
    },
]


def seed():
    from app.models.base import Base
    from app.models.user import User

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for lang_data in LANGUAGES:
            existing = (
                db.query(Language).filter(Language.code == lang_data["code"]).first()
            )
            if not existing:
                language = Language(**lang_data)
                db.add(language)

        for inst_data in INSTITUTIONS:
            existing = (
                db.query(Institution)
                .filter(Institution.code == inst_data["code"])
                .first()
            )
            if not existing:
                institution = Institution(**inst_data)
                db.add(institution)

        db.commit()

        for user_data in USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                institution_id = None
                if user_data["institution_code"]:
                    inst = (
                        db.query(Institution)
                        .filter(Institution.code == user_data["institution_code"])
                        .first()
                    )
                    if inst:
                        institution_id = inst.id

                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    institution_id=institution_id,
                )
                db.add(user)

        db.commit()
        print(
            f"Seeded {len(LANGUAGES)} languages, {len(INSTITUTIONS)} institutions, {len(USERS)} users"
        )

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
