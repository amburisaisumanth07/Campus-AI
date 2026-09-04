from typing import Generator
from backend.app.db.session import SessionLocal

def get_db() -> Generator:
    """
    Dependency for getting database sessions.
    Provides a SQLAlchemy session for the duration of the request.
    """
    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
