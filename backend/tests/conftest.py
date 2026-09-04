import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base
from backend.app.api.dependencies import get_db
from backend.app.main import app
from backend.app.db import session as db_session

_current_test_sessionmaker = None


class _TestSessionLocalProxy:
    def __call__(self, *args, **kwargs):
        if _current_test_sessionmaker is not None:
            return _current_test_sessionmaker(*args, **kwargs)
        raise RuntimeError("No test database session available")


# Install proxy on db_session so any module importing SessionLocal at load time receives the proxy
db_session.SessionLocal = _TestSessionLocalProxy()


@pytest.fixture(autouse=True)
def setup_test_db():
    """
    Create a temporary file-backed SQLite test database for each test,
    override the FastAPI get_db dependency, create all tables,
    and clean up after each test completes.
    """
    global _current_test_sessionmaker

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    _current_test_sessionmaker = TestingSessionLocal

    def override_get_db():
        db_s = TestingSessionLocal()
        try:
            yield db_s
        finally:
            db_s.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    _current_test_sessionmaker = None
    test_engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def db():
    """Provide a database session fixture for direct unit/integration test access if needed."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    test_engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass



