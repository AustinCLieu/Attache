import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

# fetch one user by primary ket
def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)

# fetch one user by email
def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return db.execute(stmt).scalar_one_or_none()

# insert a new user and return it
def create(
    db: Session,
    email: str,
    password_hash: str,
    display_name: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=password_hash,
        display_name=display_name,
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user