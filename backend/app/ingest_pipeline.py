"""Stateless ingestion, designed for serverless deployment.

Vercel Functions are ephemeral and don't share in-memory state across
invocations, so there is no background thread here (contrast with the
local/desktop version of this app, which ran ingestion on a daemon thread).
Instead, chunking is cheap and deterministic, so each call recomputes the
full chunk plan and processes one slice of it. The frontend drives the loop,
calling /api/ingest/step repeatedly with an advancing offset until `done`.
"""

from .chunker import chunk_document
from .config import DATA_DIR
from .embeddings import embed_documents
from .pdf_loader import list_pdfs, load_pdf_pages
from .vectorstore import add_chunks


def build_chunk_plan():
    """Re-parse and re-chunk every PDF in DATA_DIR. Fast (no embedding here)."""
    pdf_paths = list_pdfs(DATA_DIR)
    documents = []
    all_chunks = []
    for pdf_path in pdf_paths:
        pages = load_pdf_pages(pdf_path)
        chunks = chunk_document(pages)
        documents.append(
            {"filename": pdf_path.name, "pages": len(pages), "chunks": len(chunks)}
        )
        all_chunks.extend(chunks)
    return documents, all_chunks


def run_step(offset: int, batch_size: int) -> dict:
    documents, all_chunks = build_chunk_plan()
    total_chunks = len(all_chunks)
    batch = all_chunks[offset : offset + batch_size]

    if not batch:
        return {
            "documents": documents,
            "total_chunks": total_chunks,
            "embedded_in_step": 0,
            "next_offset": offset,
            "done": True,
            "embedding_dimension": 0,
            "sample_chunks": [],
        }

    vectors = embed_documents([c.text for c in batch])
    add_chunks(batch, vectors)
    next_offset = offset + len(batch)

    return {
        "documents": documents,
        "total_chunks": total_chunks,
        "embedded_in_step": len(batch),
        "next_offset": next_offset,
        "done": next_offset >= total_chunks,
        "embedding_dimension": len(vectors[0]) if vectors else 0,
        "sample_chunks": [
            {
                "id": c.id,
                "source": c.source,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "word_count": c.word_count,
                "preview": c.text[:220],
            }
            for c in batch[:3]
        ],
    }
