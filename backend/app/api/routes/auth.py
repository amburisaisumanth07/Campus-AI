from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.api.deps import get_current_user
from backend.app.db.models import User
from backend.app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from backend.app.services.auth_service import register_user, authenticate_user, create_user_token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new student account."""
    user = register_user(db, payload)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and return a JWT access token."""
    user = authenticate_user(db, payload.email, payload.password)
    return create_user_token(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user
