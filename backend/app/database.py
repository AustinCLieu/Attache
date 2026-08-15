from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# pool of connections to Postgres (phone line)
engine = create_engine(settings.DATABASE_URL)

# factory that creates Session objects (phone calls to DB)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# shared parent for table models
class Base(DeclarativeBase):
    pass

# generator dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()