from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import (
    health, auth, documents, conversations, chat, feedback, sources,
    announcements, academic_calendar, examinations, departments, placements, college_info, search,
    coverage
)
from backend.app.core.config import settings
from backend.app.services import scheduler_service
from backend.app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start APScheduler and load active schedules
    scheduler_service.start_scheduler()
    if SessionLocal:
        db = SessionLocal()
        try:
            scheduler_service.init_active_source_schedules(db)
        except Exception:
            pass
        finally:
            db.close()
    yield
    # Shutdown: Stop scheduler
    scheduler_service.shutdown_scheduler()


app = FastAPI(
    title="CampusAI API",
    description="Backend API for CampusAI Student Support System",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(sources.router, prefix="/api/admin/sources", tags=["Website Sources"])
app.include_router(coverage.router, prefix="/api/admin/coverage", tags=["Admin Coverage"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])

# Official MITS Entity Routers
app.include_router(announcements.router, prefix="/api/announcements", tags=["Announcements"])
app.include_router(academic_calendar.router, prefix="/api/academic-calendar", tags=["Academic Calendar"])
app.include_router(examinations.router, prefix="/api/examinations", tags=["Examinations"])
app.include_router(departments.router, prefix="/api/departments", tags=["Departments"])
app.include_router(placements.router, prefix="/api/placements", tags=["Placements"])
app.include_router(college_info.router, prefix="/api/college", tags=["College Info"])
app.include_router(search.router, prefix="/api/search", tags=["Global Search"])


@app.get("/")
def root():
    return {"message": "Welcome to CampusAI API"}
