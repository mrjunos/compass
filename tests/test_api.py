"""
Integration tests for the Compass API.
No Ollama, no disk I/O, no SQLite required — all external calls are mocked.
"""


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client_empty):
        assert client_empty.get("/health").status_code == 200

    def test_response_has_required_fields(self, client_empty):
        data = client_empty.get("/health").json()
        assert {"status", "model", "docs_indexed"} <= data.keys()

    def test_status_is_ok(self, client_empty):
        assert client_empty.get("/health").json()["status"] == "ok"

    def test_docs_indexed_zero_when_empty(self, client_empty):
        assert client_empty.get("/health").json()["docs_indexed"] == 0

    def test_docs_indexed_reflects_loaded_documents(self, client_with_docs):
        assert client_with_docs.get("/health").json()["docs_indexed"] == 1


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

class TestChat:
    def test_400_when_no_documents_indexed(self, client_empty):
        r = client_empty.post("/chat", json={"question": "What are your services?"})
        assert r.status_code == 400

    def test_error_detail_mentions_documents(self, client_empty):
        detail = client_empty.post(
            "/chat", json={"question": "Hello"}
        ).json()["detail"].lower()
        assert "documentos" in detail

    def test_returns_200_with_docs(self, client_with_docs):
        r = client_with_docs.post("/chat", json={"question": "What are your services?"})
        assert r.status_code == 200

    def test_response_contains_answer(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "What are your services?"}
        ).json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_response_contains_sources(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "What are your services?"}
        ).json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_response_contains_session_id(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "Hello", "session_id": "test-abc"}
        ).json()
        assert data["session_id"] == "test-abc"

    def test_default_session_id(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "Hello"}
        ).json()
        assert data["session_id"] == "default"

    def test_422_when_question_field_missing(self, client_with_docs):
        r = client_with_docs.post("/chat", json={"session_id": "s1"})
        assert r.status_code == 422

    def test_suggestion_returned_when_present(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "What are your services?"}
        ).json()
        assert data["suggestion"] is not None
        assert len(data["suggestion"]) > 0

    def test_answer_does_not_contain_suggestion_marker(self, client_with_docs):
        data = client_with_docs.post(
            "/chat", json={"question": "What are your services?"}
        ).json()
        assert "💡 SUGERENCIA:" not in data["answer"]


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_400_on_unsupported_extension(self, client_empty):
        r = client_empty.post(
            "/upload",
            files={"file": ("script.exe", b"MZ", "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_400_on_zip_file(self, client_empty):
        r = client_empty.post(
            "/upload",
            files={"file": ("data.zip", b"PK\x03\x04", "application/zip")},
        )
        assert r.status_code == 400

    def test_error_detail_mentions_supported_formats(self, client_empty):
        detail = client_empty.post(
            "/upload",
            files={"file": ("bad.xlsx", b"data", "application/vnd.ms-excel")},
        ).json()["detail"].lower()
        assert "soportados" in detail

    def test_201_on_markdown_upload(self, client_empty, tmp_path):
        r = client_empty.post(
            "/upload",
            files={"file": ("manual.md", b"# Manual\nContent here.", "text/markdown")},
        )
        assert r.status_code == 201

    def test_upload_returns_doc_id_and_filename(self, client_empty, tmp_path):
        r = client_empty.post(
            "/upload",
            files={"file": ("sop.md", b"# SOP\nStep 1.", "text/markdown")},
        )
        data = r.json()
        assert "doc_id" in data
        assert data["filename"] == "sop.md"

    def test_201_on_txt_upload(self, client_empty):
        r = client_empty.post(
            "/upload",
            files={"file": ("notes.txt", b"Plain text content.", "text/plain")},
        )
        assert r.status_code == 201

    def test_path_traversal_filename_is_sanitized(self, client_empty):
        r = client_empty.post(
            "/upload",
            files={"file": ("../../etc/passwd.md", b"# hacked", "text/markdown")},
        )
        assert r.status_code == 201
        assert r.json()["filename"] == "passwd.md"

    def test_413_when_file_too_large(self, client_empty):
        big = b"x" * (50 * 1024 * 1024 + 1)
        r = client_empty.post(
            "/upload",
            files={"file": ("big.md", big, "text/markdown")},
        )
        assert r.status_code == 413

    def test_file_at_size_limit_is_accepted(self, client_empty):
        at_limit = b"x" * (50 * 1024 * 1024)
        r = client_empty.post(
            "/upload",
            files={"file": ("limit.md", at_limit, "text/markdown")},
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------

class TestDocuments:
    def test_returns_200(self, client_empty):
        assert client_empty.get("/documents").status_code == 200

    def test_empty_list_when_no_docs(self, client_empty):
        data = client_empty.get("/documents").json()
        assert data["documents"] == []
        assert data["total"] == 0

    def test_returns_indexed_documents(self, client_with_docs):
        data = client_with_docs.get("/documents").json()
        assert data["total"] == 1
        assert len(data["documents"]) == 1

    def test_document_has_required_fields(self, client_with_docs):
        doc = client_with_docs.get("/documents").json()["documents"][0]
        assert {"doc_id", "doc_name", "doc_description", "type", "page_count"} <= doc.keys()

    def test_document_id_matches_expected(self, client_with_docs):
        doc = client_with_docs.get("/documents").json()["documents"][0]
        assert doc["doc_id"] == "doc-001"
