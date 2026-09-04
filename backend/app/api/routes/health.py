from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.api.dependencies import get_db
from backend.app.core.logging import logger

router = APIRouter()

@router.get("/")
def health_check():
    """
    Basic health check endpoint to verify the service is running.
    """
    return {
        "status": "healthy",
        "service": "campusai-backend"
    }

@router.get("/database")
def database_health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify database connectivity.
    """
    if db is None:
        logger.error("Database connection check failed: SessionLocal is None")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        # Execute a simple query to verify connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "campusai-database"
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
