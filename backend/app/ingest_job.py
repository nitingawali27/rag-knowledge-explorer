import threading
import time

from . import vectorstore
from .chunker import chunk_document
from .config import DATA_DIR, EMBED_MODEL
from .embeddings import EmbeddingError, embed_documents
from .pdf_loader import list_pdfs, load_pdf_pages

_lock = threading.Lock()
_state = {
    "status": "idle",  # idle | running | done | error
    "started_at": None,
    "finished_at": None,
    "documents": [],  # [{filename, pages, chunks, status}]
    "total_documents": 0,
    "total_chunks": 0,
    "chunks_embedded": 0,
    "embedding_dimension": 0,
    "current_document": None,
    "sample_chunks": [],
    "error": None,
}


def get_state():
    with _lock:
        return dict(_state)


def _reset_state():
    _state.update(
        {
            "status": "running",
            "started_at": time.time(),
            "finished_at": None,
            "documents": [],
            "total_documents": 0,
            "total_chunks": 0,
            "chunks_embedded": 0,
            "embedding_dimension": 0,
            "current_document": None,
            "sample_chunks": [],
            "error": None,
        }
    )


def start_ingestion() -> bool:
    """Returns False if a job is already running."""
    with _lock:
        if _state["status"] == "running":
            return False
        _reset_state()
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return True


def _run():
    try:
        pdf_paths = list_pdfs(DATA_DIR)
        with _lock:
            _state["total_documents"] = len(pdf_paths)

        if not pdf_paths:
            with _lock:
                _state["status"] = "error"
                _state["error"] = f"No PDF files found in {DATA_DIR}"
                _state["finished_at"] = time.time()
            return

        vectorstore.reset_collection()

        # Pass 1: load + chunk everything up front so the UI can show total chunk count.
        doc_chunks = []
        for pdf_path in pdf_paths:
            pages = load_pdf_pages(pdf_path)
            chunks = chunk_document(pages)
            doc_chunks.append((pdf_path.name, chunks))
            with _lock:
                _state["documents"].append(
                    {
                        "filename": pdf_path.name,
                        "pages": len(pages),
                        "chunks": len(chunks),
                        "status": "chunked",
                    }
                )
                _state["total_chunks"] += len(chunks)

        # Pass 2: embed + store, one document at a time, so progress is visible.
        for doc_name, chunks in doc_chunks:
            with _lock:
                _state["current_document"] = doc_name
                for d in _state["documents"]:
                    if d["filename"] == doc_name:
                        d["status"] = "embedding"

            batch_size = 16
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                vectors = embed_documents([c.text for c in batch])
                vectorstore.add_chunks(batch, vectors)
                with _lock:
                    if vectors:
                        _state["embedding_dimension"] = len(vectors[0])
                    _state["chunks_embedded"] += len(batch)
                    if len(_state["sample_chunks"]) < 6:
                        for c in batch:
                            if len(_state["sample_chunks"]) >= 6:
                                break
                            _state["sample_chunks"].append(
                                {
                                    "id": c.id,
                                    "source": c.source,
                                    "page_number": c.page_number,
                                    "chunk_index": c.chunk_index,
                                    "word_count": c.word_count,
                                    "preview": c.text[:220],
                                }
                            )

            with _lock:
                for d in _state["documents"]:
                    if d["filename"] == doc_name:
                        d["status"] = "done"

        with _lock:
            _state["status"] = "done"
            _state["current_document"] = None
            _state["finished_at"] = time.time()

    except EmbeddingError as exc:
        with _lock:
            _state["status"] = "error"
            _state["error"] = str(exc)
            _state["finished_at"] = time.time()
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        with _lock:
            _state["status"] = "error"
            _state["error"] = f"{type(exc).__name__}: {exc}"
            _state["finished_at"] = time.time()
