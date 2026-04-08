import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .indexer import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class DocumentHandler(FileSystemEventHandler):
    def __init__(self, indexer):
        self.indexer = indexer

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            logger.info(f"New file detected: {path.name}")
            self.indexer.index_document(str(path))


def start_watcher(docs_path: str, indexer) -> Observer:
    handler = DocumentHandler(indexer)
    observer = Observer()
    observer.schedule(handler, docs_path, recursive=False)
    observer.start()
    logger.info(f"Watching {docs_path}")
    return observer
