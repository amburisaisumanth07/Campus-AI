import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from backend.app.core.config import settings
from backend.app.core.logging import logger

try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Enable connection health checks
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to initialize database engine: {e}")
    # We do not raise the exception here to allow the app to start
    # and properly return 503 from the health/database endpoint.
    engine = None
    SessionLocal = None
