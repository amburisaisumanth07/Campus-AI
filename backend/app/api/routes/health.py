from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.api.dependencies import get_db
from backend.app.core.logging import logger

router = APIRouter()

@router.get("")
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


@router.get("/chroma")
def chroma_health_check(reload: bool = False):
    """
    Diagnostic endpoint to verify Chroma connectivity and settings without exposing secrets.
    """
    from backend.app.core.config import settings
    from backend.app.rag import vectorstore

    raw_key = (settings.CHROMA_API_KEY or "").strip().strip("'\"")
    has_api_key = bool(raw_key)
    tenant_val = (settings.CHROMA_TENANT or "default_tenant").strip().strip("'\"")
    db_val = (settings.CHROMA_DATABASE or "default_database").strip().strip("'\"")
    collection_name = (settings.CHROMA_COLLECTION or "campus_docs").strip().strip("'\"")

    diagnostic = {
        "has_chroma_api_key": has_api_key,
        "api_key_length": len(raw_key),
        "api_key_prefix": raw_key[:3] if raw_key else "",
        "chroma_tenant_configured": bool(settings.CHROMA_TENANT),
        "chroma_tenant": tenant_val,
        "chroma_database": db_val,
        "chroma_collection": collection_name,
        "mode": "CloudClient" if has_api_key else "HttpClient",
        "client_init": False,
        "collection_fetch": False,
        "vector_count": None,
        "similarity_search": False,
        "error": None,
    }

    try:
        client = vectorstore.get_chroma_client(force_reload=reload)
        diagnostic["client_init"] = True

        coll = vectorstore.get_collection(collection_name)
        diagnostic["collection_fetch"] = True

        cnt = coll.count()
        diagnostic["vector_count"] = cnt

        dummy_vector = [0.0] * 768
        hits = vectorstore.similarity_search(dummy_vector, top_k=1)
        diagnostic["similarity_search"] = True
        diagnostic["sample_hits_count"] = len(hits)
    except Exception as exc:
        cause = str(exc.__cause__) if getattr(exc, "__cause__", None) else str(exc)
        diagnostic["error"] = f"{type(exc).__name__}: {cause}"
        logger.error(f"[CHROMA_HEALTH_CHECK_FAILED] {diagnostic['error']}")

    return diagnostic

