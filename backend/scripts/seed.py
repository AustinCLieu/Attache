"""Seed the development database.

Stub for M1 — it creates two users so the two-user rule (design §12) can be
exercised by hand without signing up through the UI every time. M3 replaces
this with the real seed: ~30 fake emails plus policies (design §9).

Run from the backend directory:

    .venv/Scripts/python.exe -m scripts.seed
"""

from app.database import SessionLocal
from app.repositories import user_repo
from app.security import hash_password

SEED_PASSWORD = "password123"

SEED_USERS = [
    ("alice@example.com", "Alice Nguyen"),
    ("bob@example.com", "Bob Ramirez"),
]


def main() -> None:
    db = SessionLocal()
    try:
        for email, display_name in SEED_USERS:
            # Idempotent: re-running must not fail on the unique email index.
            if user_repo.get_by_email(db, email) is not None:
                print(f"exists  {email}")
                continue

            user_repo.create(
                db,
                email=email,
                password_hash=hash_password(SEED_PASSWORD),
                display_name=display_name,
            )
            print(f"created {email}")
    finally:
        db.close()

    print(f"\nSeed users share the password: {SEED_PASSWORD}")


if __name__ == "__main__":
    main()
