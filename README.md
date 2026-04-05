# Compass

> The operational brain of your company — a local AI assistant that knows everything your business has documented.

Compass is a fully local RAG system built for small businesses (1–10 people). It indexes your company's documents, answers questions in natural language with source citations, and remembers past decisions across sessions.

No external APIs. No vector database. No data leaves your machine.

---

## How it works

Instead of traditional vector similarity search, Compass uses [PageIndex](https://github.com/VectifyAI/PageIndex) to build a hierarchical tree index of each document — like a smart table of contents with summaries. An LLM reasons over that structure to find relevant sections and answer questions. This approach is more accurate than chunking + embeddings for structured documents like SOPs, manuals, and decision logs.

```
Documents (PDF / Markdown / TXT)
        ↓
PageIndex builds hierarchical tree index (JSON)
        ↓
User asks a question in natural language
        ↓
LLM reasons over document summaries → finds relevant context
        ↓
Answer with source citation (document + section)
        ↓
Conversation saved to SQLite → indexed for future recall
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| Document indexing | PageIndex — hierarchical tree, no vector DB |
| LLM inference | Ollama (fully local) |
| LLM bridge | LiteLLM |
| Conversation memory | SQLite |
| File watching | watchdog |

---

## Quickstart

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com) running locally with at least one model pulled.

```bash
# 1. Clone with submodules
git clone --recurse-submodules https://github.com/mrjunos/compass.git
cd compass

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — set your Ollama model (default: gemma4:e4b)

# 5. Run
uvicorn backend.main:app --port 8000

# Compass is now running at http://localhost:8000
```

On startup, Compass automatically indexes any documents found in `data/docs/`.

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
OLLAMA_API_BASE=http://localhost:11434   # Ollama server URL
COMPASS_MODEL=ollama/gemma4:e4b         # Any model available in your Ollama
COMPASS_DOCS_PATH=./data/docs           # Folder to watch for documents
COMPASS_WORKSPACE=./data/index          # PageIndex workspace (persisted between restarts)
```

---

## API

### `POST /chat`
Ask a question. Compass searches all indexed documents and responds with source citations.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the process for onboarding a new client?", "session_id": "my-session"}'
```

Response:
```json
{
  "answer": "The client onboarding process takes 5–7 business days... [onboarding-clientes — Step 1]",
  "sources": [
    {"doc_name": "onboarding-clientes", "doc_id": "...", "pages": "1-10"}
  ],
  "suggestion": "Consider documenting the offboarding process as well.",
  "session_id": "my-session"
}
```

### `POST /upload`
Upload a document to index. Supported formats: PDF, Markdown, TXT.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@your-document.pdf"
```

### `GET /documents`
List all indexed documents.

### `GET /health`
Check server status and number of indexed documents.

---

## Document ingestion

Two ways to add documents:

1. **Drop files** into `data/docs/` — the folder watcher picks them up automatically and indexes within seconds.
2. **Upload via API** — `POST /upload` saves the file to `data/docs/` and triggers indexing immediately.

Supported formats: `.pdf`, `.md`, `.markdown`, `.txt`

Compass deduplicates on filename — uploading the same file twice won't create duplicate index entries.

---

## Demo

The `demo/techflow/` folder contains a sample dataset for a fictional 5-person digital agency (TechFlow Agency):

| File | Contents |
|------|----------|
| `servicios.md` | Services catalog and pricing |
| `onboarding-clientes.md` | Step-by-step client onboarding process |
| `onboarding-equipo.md` | Team structure and employee onboarding |
| `decisiones.md` | Decision log with context and rationale |
| `proveedores.md` | Vendors, tools, and billing information |

To run the demo:
```bash
cp demo/techflow/*.md data/docs/
# Start the server — documents will be indexed automatically
```

Sample queries:
- *"What is the process for onboarding a new client?"*
- *"What did we decide about retainer pricing?"*
- *"I'm a new employee — what accesses do I need and who sets them up?"*

---

## Project structure

```
compass/
├── backend/
│   ├── main.py         # FastAPI app, lifespan, routes
│   ├── chat.py         # Chat logic: context retrieval + LLM response
│   ├── indexer.py      # PageIndex wrapper with deduplication
│   ├── database.py     # SQLite: conversation memory
│   └── watcher.py      # watchdog: auto-index new files
├── demo/
│   └── techflow/       # Sample dataset (fictional company)
├── pageindex/          # PageIndex submodule (VectifyAI)
├── data/
│   ├── docs/           # Documents to index (gitignored)
│   └── index/          # PageIndex workspace (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Roadmap

- [x] Document indexing (PDF, Markdown, TXT)
- [x] Natural language Q&A with source citations
- [x] Persistent conversation memory (SQLite)
- [x] Auto-indexing via folder watch
- [x] Proactive knowledge gap suggestions
- [ ] Chat UI (React + Vite)
- [ ] Multi-document context merging
- [ ] Decision capture workflow
- [ ] Multi-tenant support

---

## Built with

- [FastAPI](https://fastapi.tiangolo.com)
- [PageIndex](https://github.com/VectifyAI/PageIndex) by VectifyAI
- [Ollama](https://ollama.com)
- [LiteLLM](https://github.com/BerriAI/litellm)
- [watchdog](https://github.com/gorakhargosh/watchdog)
