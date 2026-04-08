import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.utils.security import hash_password


def create_admin(email: str, password: str, institution_id: str = None):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists")
            return

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            institution_id=institution_id,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin created: {email}")

    except Exception as e:
        db.rollback()
        print(f"Error creating admin: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python scripts/create_admin.py <email> <password> [institution_id]"
        )
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    institution_id = sys.argv[3] if len(sys.argv) > 3 else None

    create_admin(email, password, institution_id)
