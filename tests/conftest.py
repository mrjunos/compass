"""
Shared fixtures for the Compass test suite.

Mocking strategy:
  - CompassIndexer is mocked so PageIndexClient never touches disk or network.
  - start_watcher is mocked so no background threads are launched.
  - init_db is mocked so no SQLite file is created.
  - litellm.acompletion is mocked in client_with_docs so /chat never calls Ollama.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_indexer(has_docs: bool = False) -> MagicMock:
    mock = MagicMock()
    if has_docs:
        mock.documents = {
            "doc-001": {
                "doc_name": "servicios",
                "doc_description": "Service catalog",
                "type": "md",
                "page_count": None,
            }
        }
        mock.list_documents.return_value = [
            {
                "doc_id": "doc-001",
                "doc_name": "servicios",
                "doc_description": "Service catalog",
                "type": "md",
                "page_count": None,
            }
        ]
        mock.get_structure.return_value = (
            '[{"title": "Services", "nodes": ['
            '{"title": "Web Dev", "summary": "Web development services starting at USD 1500."}'
            ']}]'
        )
    else:
        mock.documents = {}
        mock.list_documents.return_value = []

    mock.index_document.return_value = "doc-001"
    return mock


def _make_llm_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_empty():
    """TestClient with no indexed documents."""
    mock_indexer = _make_mock_indexer(has_docs=False)

    with patch("backend.main.CompassIndexer", return_value=mock_indexer), \
         patch("backend.main.start_watcher", return_value=MagicMock()), \
         patch("backend.main.init_db"):

        from backend.main import app
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client


@pytest.fixture
def client_with_docs():
    """TestClient with one pre-indexed document and mocked LLM responses."""
    mock_indexer = _make_mock_indexer(has_docs=True)

    with patch("backend.main.CompassIndexer", return_value=mock_indexer), \
         patch("backend.main.start_watcher", return_value=MagicMock()), \
         patch("backend.main.init_db"), \
         patch(
             "backend.chat.litellm.acompletion",
             new=AsyncMock(return_value=_make_llm_response(
                 "Web development services start at USD 1,500.\n"
                 "💡 SUGERENCIA: Consider documenting the revision process for delivered projects."
             ))
         ), \
         patch("backend.chat.save_message"), \
         patch("backend.chat.get_session_messages", return_value=[]):

        from backend.main import app
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
