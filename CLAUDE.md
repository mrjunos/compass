# CLAUDE.md — Compass

Guidance for AI assistants working on this codebase.

---

## What this project is

Compass is a local-first operational knowledge base for small businesses. It indexes company documents (PDF, Markdown, TXT) using [PageIndex](https://github.com/VectifyAI/PageIndex) — a hierarchical tree indexer, not a vector database — and answers questions in natural language with source citations. A local Ollama LLM handles all inference; no data leaves the machine.

**Key insight:** PageIndex builds a structured tree with summaries per section. The chat pipeline extracts all summaries and passes them as context to the LLM in a single call. No embedding, no similarity search.

---

## Commands

```bash
# Run the server
uvicorn backend.main:app --port 8000

# Run tests (all)
pytest tests/ -v

# Run a specific test file
pytest tests/test_api.py -v

# Install dependencies
pip install -r requirements.txt

# Clone with submodules (required — PageIndex is a git submodule)
git clone --recurse-submodules https://github.com/mrjunos/compass.git
```

---

## Architecture

```
HTTP (FastAPI)
    └─ main.py          routes, auth, rate limiting, CORS, lifespan
         ├─ chat.py     Q&A pipeline: context build → LLM → parse → save
         ├─ indexer.py  PageIndex wrapper, dedup, structure cache
         ├─ database.py SQLite: conversation history
         └─ watcher.py  watchdog: auto-index files dropped in data/docs/
```

### Request flow — POST /chat

1. Save user message to SQLite
2. For each indexed doc: `indexer.get_structure(doc_id)` → cached JSON tree
3. Recursively extract summaries from the tree → build context string
4. Fetch last 6 messages from this session
5. Single `litellm.acompletion()` call with system prompt + context + history + question
6. Parse response: split on `💡 SUGERENCIA:` marker → `answer` + optional `suggestion`
7. Save assistant answer to SQLite
8. Return `{answer, sources, suggestion, session_id}`

### PageIndex integration

PageIndex is a **git submodule** at `pageindex/`. It is NOT installed as a pip package. `indexer.py` adds it to `sys.path` at import time:

```python
sys.path.insert(0, str(Path(__file__).parent.parent / "pageindex"))
from pageindex.client import PageIndexClient
```

PageIndex stores `doc_name` **without the file extension** (e.g. `"servicios"` not `"servicios.md"`). The dedup check in `indexer.py` uses `path.stem` (not `path.name`) for this reason.

Structure cache: `CompassIndexer._structure_cache` stores the result of `get_document_structure()` per doc_id. Cache is invalidated when a document is re-indexed.

---

## Environment variables

All config lives in `.env` (see `.env.example`). No defaults should be changed without updating `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_API_BASE` | `http://localhost:11434` | Ollama server URL |
| `COMPASS_MODEL` | `ollama/gemma4:e4b` | LiteLLM model string |
| `COMPASS_DOCS_PATH` | `./data/docs` | Folder watched for documents |
| `COMPASS_WORKSPACE` | `./data/index` | PageIndex persistence directory |
| `COMPASS_API_KEY` | _(unset)_ | If set, all requests require `X-API-Key` header. Leave unset for local dev. |
| `COMPASS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` | CORS allowlist |
| `COMPASS_RATE_LIMIT` | `60/minute` | Rate limit per IP, all endpoints |

---

## Testing

**58 tests across 3 files.** No Ollama, no disk I/O, no real SQLite required — all external dependencies are mocked.

| File | What it tests |
|---|---|
| `tests/test_api.py` | All HTTP endpoints: health, chat, upload, documents. Also: auth, rate limiting, `_extract_summaries` unit tests |
| `tests/test_database.py` | SQLite schema (table + index), save/get messages, session isolation, ordering, limits |
| `tests/test_indexer.py` | Structure cache (hit, miss, invalidation), deduplication |

### Mocking strategy (conftest.py)

- `backend.main.CompassIndexer` — replaced with a `MagicMock` so PageIndexClient never runs
- `backend.main.start_watcher` — replaced to prevent background threads
- `backend.main.init_db` — replaced to prevent SQLite file creation
- `backend.chat.litellm.acompletion` — `AsyncMock` returning a controlled response
- `backend.chat.save_message` — replaced to prevent DB writes
- `backend.chat.get_session_messages` — returns `[]`

**Rule:** always mock at the site where the symbol is *used*, not where it's *defined*. This is the `unittest.mock` golden rule. E.g. mock `backend.main.CompassIndexer`, not `backend.indexer.CompassIndexer`.

### Two fixtures

- `client_empty` — no indexed documents
- `client_with_docs` — one pre-loaded doc (`doc-001`) with a mocked LLM response that includes a `💡 SUGERENCIA:` marker

---

## Key conventions

### Adding a new file format

`SUPPORTED_EXTENSIONS` is defined once in `backend/indexer.py` and imported everywhere else. Only change it there.

### Adding a new endpoint

1. Add the route in `main.py`
2. Decorate with `@limiter.limit(RATE_LIMIT)` — all endpoints are rate-limited
3. Use `get_indexer(request)` to access the indexer, never import it directly
4. Add tests in `test_api.py` (happy path + error cases)

### Changing the database schema

`init_db()` runs on startup via `CREATE TABLE IF NOT EXISTS`. For schema changes in an existing deployment, add a migration step — don't rely on `IF NOT EXISTS` to handle column additions.

### LLM calls

All LLM calls go through `litellm.acompletion()` in `chat.py`. Always include `timeout=60`. The model is always passed as a parameter — never hardcoded.

The system prompt is in Spanish (target market: LATAM SMBs). The `💡 SUGERENCIA:` marker at the end of the prompt triggers the proactive suggestion. If the LLM includes it, `_parse_response()` splits on it; if not, `suggestion` is `None`.

### Branch and PR workflow

- Never push directly to `main`
- Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`
- Every PR must have tests covering the change
- PRs targeting `main` trigger CI (pytest 58 tests)
- Draft PRs are excluded from CI

---

## What NOT to do

- **Do not** call `PageIndexClient` directly from anywhere except `indexer.py`
- **Do not** define `SUPPORTED_EXTENSIONS` in a new file — import from `indexer.py`
- **Do not** use `except Exception` without logging the error
- **Do not** add a new env variable without updating `.env.example` with a comment
- **Do not** mock at the definition site (`backend.indexer.CompassIndexer`) — mock at the usage site (`backend.main.CompassIndexer`)
- **Do not** write blocking I/O in async route handlers without acknowledging the tradeoff (known issue, tracked in audit)

---

## Known issues / technical debt

See `audits/001_2026-04-06_audit_report.md` for the full audit. Active items:

- `mark_indexed()` in `database.py` is dead code — never called
- `upload()` and `indexer.index_document()` are blocking in async context
- No `pytest-cov` — coverage is not measured
- No `ruff`/`mypy` — linting and type checking are not enforced in CI
- `messages` table grows unboundedly — no retention policy
- Watcher thread has no supervision — silent death undetected

---

## Demo dataset

`demo/techflow/` contains 5 Markdown files for a fictional 5-person digital agency (TechFlow Agency). Copy them to `data/docs/` to test end-to-end:

```bash
cp demo/techflow/*.md data/docs/
uvicorn backend.main:app --port 8000
```

Sample queries:
- *"What is the process for onboarding a new client?"*
- *"What did we decide about retainer pricing?"*
- *"Who handles design work and what tools do they use?"*
