# # app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from typing import Generator


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


# from sqlalchemy.ext.asyncio import (create_async_engine, AsyncSession, async_sessionmaker)
# from sqlalchemy.ext.declarative import declarative_base

# # Create async engine
# engine = create_async_engine(
#     ASYNC_DATABASE_URL,
#     echo=False,
#     future=True,
#     pool_size=50,
#     max_overflow=20,
#     pool_timeout=20,
#     pool_recycle=300,
#     pool_pre_ping=True,
# )

# # Create async session factory
# AsyncSessionLocal = async_sessionmaker(
#     engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
# )

# Base = declarative_base()

# # Async context manager for database sessions
# async def get_db():
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session  # Provide session to the endpoint
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()  # Explicitly close session
