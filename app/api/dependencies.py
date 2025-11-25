"""FastAPI dependencies."""

from typing import Generator
from sqlalchemy.orm import Session
from app.models.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
