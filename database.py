# # app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import get_settings
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from typing import Generator


# Load settings
settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=50,
    max_overflow=20,
    pool_timeout=20,
    pool_recycle=300,
    echo=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Provides a SQLAlchemy database session to be used in FastAPI routes.

    This function creates a new database session for each request and ensures
    proper cleanup after the request is completed, even if exceptions occur.

    Yields:
        Session: A SQLAlchemy database session

    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Note:
        The session is automatically closed after the request is completed,
        ensuring proper resource cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
