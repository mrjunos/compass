import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pageindex"))
from pageindex.client import PageIndexClient

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


class CompassIndexer:
    def __init__(self, model: str, workspace: str):
        self.client = PageIndexClient(model=model, workspace=workspace)

    def index_document(self, filepath: str) -> str | None:
        path = Path(filepath)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file type: {path.name}")
            return None

        # Dedup: PageIndex stores doc_name without extension
        existing = next(
            (did for did, doc in self.client.documents.items()
             if doc.get("doc_name") == path.stem),
            None,
        )
        if existing:
            logger.info(f"Already indexed: {path.name} ({existing})")
            return existing

        logger.info(f"Indexing: {path.name}")
        doc_id = self.client.index(str(path))
        logger.info(f"Done: {path.name} → {doc_id}")
        return doc_id

    def get_structure(self, doc_id: str) -> str:
        return self.client.get_document_structure(doc_id)

    def get_page_content(self, doc_id: str, pages: str) -> str:
        return self.client.get_page_content(doc_id, pages)

    def get_doc_meta(self, doc_id: str) -> str:
        return self.client.get_document(doc_id)

    def list_documents(self) -> list:
        return [
            {
                "doc_id": did,
                "doc_name": doc.get("doc_name", ""),
                "doc_description": doc.get("doc_description", ""),
                "type": doc.get("type", ""),
                "page_count": doc.get("page_count"),
            }
            for did, doc in self.client.documents.items()
        ]

    @property
    def documents(self):
        return self.client.documents
