import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from backend.app.core.config import settings
from backend.app.core.logging import logger

try:
    engine_kwargs = {"pool_pre_ping": True}
    if not settings.DATABASE_URL.startswith("sqlite"):
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

    engine = create_engine(
        settings.DATABASE_URL,
        **engine_kwargs,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to initialize database engine: {e}")
    # We do not raise the exception here to allow the app to start
    # and properly return 503 from the health/database endpoint.
    engine = None
    SessionLocal = None
