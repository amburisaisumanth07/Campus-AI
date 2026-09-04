from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.db.models import User, Role
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.schemas.auth import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    """Look up a user by email address."""
    return db.query(User).filter(User.email == email).first()


def register_user(db: Session, payload: UserCreate) -> User:
    """Register a new user with the STUDENT role.

    Raises HTTPException 409 if the email is already taken.
    """
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=Role.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate credentials and return the user.

    Raises HTTPException 401 with a generic message to avoid account enumeration.
    """
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user


def create_user_token(user: User) -> dict:
    """Create a JWT access token for the given user."""
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
