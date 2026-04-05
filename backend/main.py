import os
import shutil
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from .database import init_db
from .indexer import CompassIndexer
from .watcher import start_watcher
from .chat import process_chat

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# Config
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
COMPASS_MODEL   = os.getenv("COMPASS_MODEL", "ollama/gemma4:e4b")
DOCS_PATH       = Path(os.getenv("COMPASS_DOCS_PATH", "./data/docs"))
WORKSPACE       = Path(os.getenv("COMPASS_WORKSPACE", "./data/index"))

os.environ["OLLAMA_API_BASE"] = OLLAMA_API_BASE


def get_indexer(request: Request) -> CompassIndexer:
    return request.app.state.indexer


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    DOCS_PATH.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    app.state.indexer = CompassIndexer(model=COMPASS_MODEL, workspace=str(WORKSPACE))

    for f in DOCS_PATH.iterdir():
        if f.suffix.lower() in {".pdf", ".md", ".markdown", ".txt"}:
            app.state.indexer.index_document(str(f))

    app.state.watcher = start_watcher(str(DOCS_PATH), app.state.indexer)
    logger.info(f"Compass ready — {len(app.state.indexer.documents)} doc(s) indexed")
    yield
    if app.state.watcher:
        app.state.watcher.stop()
        app.state.watcher.join()


app = FastAPI(
    title="Compass",
    description="El cerebro operativo de tu empresa.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


@app.get("/health")
def health(request: Request):
    indexer = get_indexer(request)
    return {
        "status": "ok",
        "model": COMPASS_MODEL,
        "docs_indexed": len(indexer.documents),
    }


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    indexer = get_indexer(request)
    if not indexer.documents:
        raise HTTPException(
            status_code=400,
            detail="No hay documentos indexados aún. Sube documentos primero."
        )
    return await process_chat(
        question=body.question,
        session_id=body.session_id,
        indexer=indexer,
        model=COMPASS_MODEL,
    )


@app.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...), request: Request = None):
    indexer = get_indexer(request)
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".md", ".markdown", ".txt"}:
        raise HTTPException(status_code=400, detail="Formatos soportados: PDF, Markdown, TXT")

    dest = DOCS_PATH / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc_id = indexer.index_document(str(dest))
    return {"doc_id": doc_id, "filename": file.filename}


@app.get("/documents")
def list_documents(request: Request):
    indexer = get_indexer(request)
    return {"documents": indexer.list_documents(), "total": len(indexer.documents)}
