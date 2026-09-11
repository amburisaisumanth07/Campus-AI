import pytest
from unittest.mock import MagicMock, patch
from backend.scripts import reindex_chromadb


class TestReindexScript:

    @patch("backend.scripts.reindex_chromadb.index_document")
    @patch("backend.scripts.reindex_chromadb.get_collection")
    @patch("backend.scripts.reindex_chromadb.SessionLocal")
    def test_local_mode_default(self, mock_session, mock_get_coll, mock_index_doc):
        """Default local execution clears collection and indexes ready documents."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.title = "Test Doc"
        mock_doc.department = "CS"
        mock_doc.academic_year = "2025"
        mock_doc.source_type = "official"
        mock_doc.source_url = "http://test.com"
        mock_doc.pages = [{"page_number": 1, "text_content": "Page text", "char_count": 9}]
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_doc]

        mock_coll = MagicMock()
        mock_coll.get.return_value = {"ids": ["vec1", "vec2"]}
        mock_get_coll.return_value = mock_coll
        mock_index_doc.return_value = 2

        reindex_chromadb.reindex_all_documents(production=False, confirm_production=False)

        mock_coll.delete.assert_called_once_with(ids=["vec1", "vec2"])
        mock_index_doc.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("backend.scripts.reindex_chromadb.settings")
    def test_production_mode_missing_env_vars(self, mock_settings):
        """Production mode aborts when required env vars are missing."""
        mock_settings.DATABASE_URL = ""
        mock_settings.CHROMA_API_KEY = ""
        mock_settings.CHROMA_TENANT = ""
        mock_settings.CHROMA_DATABASE = ""
        mock_settings.CHROMA_COLLECTION = ""
        mock_settings.GEMINI_API_KEY = ""

        with pytest.raises(SystemExit) as exc_info:
            reindex_chromadb.reindex_all_documents(production=True, confirm_production=False)
        assert exc_info.value.code == 1

    @patch("backend.scripts.reindex_chromadb.settings")
    def test_production_mode_rejects_localhost_db(self, mock_settings):
        """Production mode aborts if DATABASE_URL host is 127.0.0.1 or localhost."""
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@127.0.0.1:5432/db"
        mock_settings.CHROMA_API_KEY = "key"
        mock_settings.CHROMA_TENANT = "tenant"
        mock_settings.CHROMA_DATABASE = "db"
        mock_settings.CHROMA_COLLECTION = "coll"
        mock_settings.GEMINI_API_KEY = "gemini"

        with pytest.raises(SystemExit) as exc_info:
            reindex_chromadb.reindex_all_documents(production=True, confirm_production=False)
        assert exc_info.value.code == 1

    @patch("backend.scripts.reindex_chromadb.get_collection")
    @patch("backend.scripts.reindex_chromadb.SessionLocal")
    @patch("backend.scripts.reindex_chromadb.settings")
    def test_production_mode_preflight_only_without_confirmation(
        self, mock_settings, mock_session, mock_get_coll
    ):
        """Production mode without --confirm-production performs preflight check and does NOT clear/index Chroma."""
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@ep-test.neon.tech/db"
        mock_settings.CHROMA_API_KEY = "key"
        mock_settings.CHROMA_TENANT = "tenant"
        mock_settings.CHROMA_DATABASE = "db"
        mock_settings.CHROMA_COLLECTION = "coll"
        mock_settings.GEMINI_API_KEY = "gemini"

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []

        reindex_chromadb.reindex_all_documents(production=True, confirm_production=False)

        mock_get_coll.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("backend.scripts.reindex_chromadb.index_document")
    @patch("backend.scripts.reindex_chromadb.get_collection")
    @patch("backend.scripts.reindex_chromadb.SessionLocal")
    @patch("backend.scripts.reindex_chromadb.settings")
    def test_production_mode_executes_with_confirmation(
        self, mock_settings, mock_session, mock_get_coll, mock_index_doc
    ):
        """Production mode with --confirm-production clears collection and re-indexes documents."""
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@ep-test.neon.tech/db"
        mock_settings.CHROMA_API_KEY = "key"
        mock_settings.CHROMA_TENANT = "tenant"
        mock_settings.CHROMA_DATABASE = "db"
        mock_settings.CHROMA_COLLECTION = "coll"
        mock_settings.GEMINI_API_KEY = "gemini"

        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []

        mock_coll = MagicMock()
        mock_coll.get.return_value = {"ids": []}
        mock_get_coll.return_value = mock_coll

        reindex_chromadb.reindex_all_documents(production=True, confirm_production=True)

        mock_get_coll.assert_called_once()
        mock_db.close.assert_called_once()
