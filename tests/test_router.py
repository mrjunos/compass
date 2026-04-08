"""
Tests for the document routing layer in chat.py.
Covers: _extract_first_summary, _route_documents, and process_chat routing integration.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_structure(summary: str, children: list | None = None) -> str:
    node = {"title": "Root", "summary": summary, "nodes": children or []}
    return json.dumps([node])


def _make_indexer(docs: dict[str, str]) -> MagicMock:
    """Create a mock indexer with docs: {doc_id: doc_name}."""
    mock = MagicMock()
    mock.documents = {
        did: {"doc_name": name} for did, name in docs.items()
    }
    mock.get_structure.return_value = _make_structure("Default summary for testing.")
    return mock


def _make_llm_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# _extract_first_summary
# ---------------------------------------------------------------------------

class TestExtractFirstSummary:
    def test_returns_top_level_summary(self):
        from backend.chat import _extract_first_summary
        structure = _make_structure("This is the main summary.")
        assert _extract_first_summary(structure) == "This is the main summary."

    def test_truncates_long_summary(self):
        from backend.chat import _extract_first_summary
        long_text = "A" * 200
        structure = _make_structure(long_text)
        result = _extract_first_summary(structure)
        assert len(result) == 153  # 150 + "..."
        assert result.endswith("...")

    def test_returns_short_summary_without_truncation(self):
        from backend.chat import _extract_first_summary
        structure = _make_structure("Short.")
        assert _extract_first_summary(structure) == "Short."

    def test_returns_fallback_on_invalid_json(self):
        from backend.chat import _extract_first_summary
        assert _extract_first_summary("not json{{{") == "(no summary)"

    def test_returns_fallback_on_missing_summary(self):
        from backend.chat import _extract_first_summary
        structure = json.dumps([{"title": "Root", "nodes": []}])
        assert _extract_first_summary(structure) == "(no summary)"

    def test_handles_single_object_not_array(self):
        from backend.chat import _extract_first_summary
        structure = json.dumps({"title": "Root", "summary": "Single object.", "nodes": []})
        assert _extract_first_summary(structure) == "Single object."

    def test_returns_fallback_on_empty_array(self):
        from backend.chat import _extract_first_summary
        assert _extract_first_summary("[]") == "(no summary)"


# ---------------------------------------------------------------------------
# _route_documents
# ---------------------------------------------------------------------------

class TestRouteDocuments:
    @pytest.mark.asyncio
    async def test_selects_exact_doc_name(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios", "d2": "proveedores", "d3": "decisiones"})
        llm_response = _make_llm_response("servicios\nproveedores")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)):
            result = await _route_documents("What services do we offer?", indexer, "test-model", [])

        assert result == ["d1", "d2"]

    @pytest.mark.asyncio
    async def test_selects_doc_with_bullet_prefix(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios", "d2": "proveedores"})
        llm_response = _make_llm_response("- servicios")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)):
            result = await _route_documents("pricing?", indexer, "test-model", [])

        assert result == ["d1"]

    @pytest.mark.asyncio
    async def test_fuzzy_match_when_name_in_line(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "onboarding-clientes", "d2": "servicios"})
        llm_response = _make_llm_response("The document onboarding-clientes is relevant.")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)):
            result = await _route_documents("How do we onboard?", indexer, "test-model", [])

        assert "d1" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_all_docs_on_llm_failure(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios", "d2": "proveedores"})

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(side_effect=Exception("timeout"))):
            result = await _route_documents("anything", indexer, "test-model", [])

        assert set(result) == {"d1", "d2"}

    @pytest.mark.asyncio
    async def test_falls_back_when_no_names_matched(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios"})
        llm_response = _make_llm_response("I don't know which document is relevant.")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)):
            result = await _route_documents("random question", indexer, "test-model", [])

        assert result == ["d1"]  # fallback to all

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_documents(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({})

        result = await _route_documents("anything", indexer, "test-model", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_includes_conversation_history_in_routing(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios", "d2": "proveedores"})
        llm_response = _make_llm_response("servicios")
        history = [
            {"role": "user", "content": "Tell me about services"},
            {"role": "assistant", "content": "We offer web development."},
        ]

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)) as mock_llm:
            await _route_documents("tell me more", indexer, "test-model", history)

        # Verify the routing prompt includes conversation context
        call_args = mock_llm.call_args
        prompt_content = call_args.kwargs["messages"][0]["content"]
        assert "Tell me about services" in prompt_content
        assert "Recent conversation" in prompt_content

    @pytest.mark.asyncio
    async def test_no_duplicate_doc_ids(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios"})
        # LLM returns the same doc name multiple times
        llm_response = _make_llm_response("servicios\nservicios\n- servicios is relevant")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)):
            result = await _route_documents("pricing?", indexer, "test-model", [])

        assert result == ["d1"]

    @pytest.mark.asyncio
    async def test_routing_uses_short_timeout(self):
        from backend.chat import _route_documents

        indexer = _make_indexer({"d1": "servicios"})
        llm_response = _make_llm_response("servicios")

        with patch("backend.chat.litellm.acompletion", new=AsyncMock(return_value=llm_response)) as mock_llm:
            await _route_documents("test", indexer, "test-model", [])

        assert mock_llm.call_args.kwargs["timeout"] == 15


# ---------------------------------------------------------------------------
# process_chat — routing integration
# ---------------------------------------------------------------------------

class TestProcessChatRouting:
    @pytest.mark.asyncio
    async def test_only_selected_docs_in_context(self):
        from backend.chat import process_chat

        indexer = _make_indexer({"d1": "servicios", "d2": "proveedores", "d3": "decisiones"})
        indexer.get_structure.return_value = _make_structure("Some summary content.")

        # Router selects only "servicios"
        router_response = _make_llm_response("servicios")
        # Chat response
        chat_response = _make_llm_response("Services info here.")

        with patch("backend.chat.save_message"), \
             patch("backend.chat.get_session_messages", return_value=[
                 {"role": "user", "content": "What services?"}
             ]), \
             patch("backend.chat.litellm.acompletion", new=AsyncMock(
                 side_effect=[router_response, chat_response]
             )):
            result = await process_chat("What services?", "sess-1", indexer, "test-model")

        # Only servicios should be in sources, not all 3
        source_names = [s["doc_name"] for s in result["sources"]]
        assert "servicios" in source_names
        assert "proveedores" not in source_names
        assert "decisiones" not in source_names

    @pytest.mark.asyncio
    async def test_history_passed_to_llm(self):
        from backend.chat import process_chat

        indexer = _make_indexer({"d1": "servicios"})
        indexer.get_structure.return_value = _make_structure("Summary.")

        router_response = _make_llm_response("servicios")
        chat_response = _make_llm_response("Follow-up answer.")

        history = [
            {"role": "user", "content": "What services do you offer?"},
            {"role": "assistant", "content": "We offer web development."},
            {"role": "user", "content": "Tell me more"},
        ]

        with patch("backend.chat.save_message"), \
             patch("backend.chat.get_session_messages", return_value=history), \
             patch("backend.chat.litellm.acompletion", new=AsyncMock(
                 side_effect=[router_response, chat_response]
             )) as mock_llm:
            await process_chat("Tell me more", "sess-1", indexer, "test-model")

        # The second call (chat) should include history messages
        chat_call = mock_llm.call_args_list[1]
        messages = chat_call.kwargs["messages"]
        roles = [m["role"] for m in messages]
        # system + user + assistant + user (current)
        assert roles == ["system", "user", "assistant", "user"]

    @pytest.mark.asyncio
    async def test_session_history_limit_is_10(self):
        from backend.chat import process_chat

        indexer = _make_indexer({"d1": "servicios"})
        indexer.get_structure.return_value = _make_structure("Summary.")

        router_response = _make_llm_response("servicios")
        chat_response = _make_llm_response("Answer.")

        with patch("backend.chat.save_message"), \
             patch("backend.chat.get_session_messages", return_value=[
                 {"role": "user", "content": "q"}
             ]) as mock_get_messages, \
             patch("backend.chat.litellm.acompletion", new=AsyncMock(
                 side_effect=[router_response, chat_response]
             )):
            await process_chat("q", "sess-1", indexer, "test-model")

        mock_get_messages.assert_called_once_with("sess-1", limit=10)
