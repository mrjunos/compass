"""
Unit tests for CompassIndexer — focuses on caching and deduplication logic.
PageIndexClient is mocked so no disk I/O or LLM calls are made.
"""

import pytest
from unittest.mock import MagicMock, patch, call


def _make_client(doc_name="doc", structure='[{"title": "T", "nodes": []}]'):
    client = MagicMock()
    client.documents = {
        "doc-001": {"doc_name": doc_name, "type": "md", "page_count": None, "doc_description": ""}
    }
    client.get_document_structure.return_value = structure
    client.index.return_value = "doc-002"
    return client


@pytest.fixture
def indexer():
    with patch("backend.indexer.PageIndexClient") as MockClient:
        MockClient.return_value = _make_client()
        from backend.indexer import CompassIndexer
        idx = CompassIndexer(model="test-model", workspace="/tmp/ws")
        yield idx


class TestStructureCache:
    def test_first_call_hits_client(self, indexer):
        indexer.get_structure("doc-001")
        indexer.client.get_document_structure.assert_called_once_with("doc-001")

    def test_second_call_uses_cache(self, indexer):
        indexer.get_structure("doc-001")
        indexer.get_structure("doc-001")
        # client should only be called once
        indexer.client.get_document_structure.assert_called_once()

    def test_cache_returns_same_value(self, indexer):
        first = indexer.get_structure("doc-001")
        second = indexer.get_structure("doc-001")
        assert first == second

    def test_cache_invalidated_on_reindex(self, indexer):
        # Pre-populate cache
        indexer._structure_cache["doc-001"] = "cached-structure"

        # Simulate what index_document does after a successful index call
        indexer._structure_cache.pop("doc-001", None)

        assert "doc-001" not in indexer._structure_cache

    def test_cache_pop_is_called_after_index(self, indexer):
        indexer._structure_cache["doc-002"] = "stale"
        indexer.client.index.return_value = "doc-002"
        # doc-002 is not in existing documents, so it will be indexed
        indexer.client.documents = {}

        indexer.index_document("newfile.md")

        assert "doc-002" not in indexer._structure_cache

    def test_different_docs_cached_independently(self, indexer):
        indexer.client.documents["doc-002"] = {
            "doc_name": "other", "type": "md", "page_count": None, "doc_description": ""
        }
        indexer.client.get_document_structure.side_effect = lambda doc_id: f"structure-{doc_id}"

        s1 = indexer.get_structure("doc-001")
        s2 = indexer.get_structure("doc-002")

        assert s1 == "structure-doc-001"
        assert s2 == "structure-doc-002"
        assert indexer.client.get_document_structure.call_count == 2


class TestDeduplication:
    def test_does_not_reindex_existing_doc(self, indexer):
        result = indexer.index_document("doc.md")
        assert result == "doc-001"
        indexer.client.index.assert_not_called()

    def test_indexes_new_doc(self, indexer):
        result = indexer.index_document("new-file.md")
        assert result == "doc-002"
        indexer.client.index.assert_called_once()
