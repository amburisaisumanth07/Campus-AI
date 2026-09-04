import os
from backend.app.core.config import Settings

def test_settings_loading(monkeypatch):
    """Test that settings load correctly from environment variables."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/testdb")
    
    settings = Settings()
    
    assert settings.APP_ENV == "testing"
    assert settings.DATABASE_URL == "postgresql+psycopg://test:test@localhost:5432/testdb"
    assert "http://localhost:5173" in settings.cors_origins_list
