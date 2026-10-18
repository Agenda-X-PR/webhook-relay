"""Database engine, session, and base model."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

# Create the engine — this is the connection to the SQLite file
engine = create_engine(
    settings.database_url,
    # SQLite needs this for multithreaded FastAPI usage
    connect_args={"check_same_thread": False},
)

# Session factory — each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db():
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()