import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import vectorstore
from .config import (
    CHUNK_OVERLAP_WORDS,
    CHUNK_SIZE_WORDS,
    DATA_DIR,
    EMBED_MODEL,
    GROQ_MODEL,
    INGEST_STEP_BATCH_SIZE,
    TOP_K,
)
from .embeddings import EmbeddingError, embed_query
from .ingest_pipeline import build_chunk_plan, run_step
from .llm import LLMError, generate_answer
from .pdf_loader import list_pdfs
from .vectorstore import VectorStoreError

app = FastAPI(title="RAG Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(VectorStoreError)
def handle_vectorstore_error(request: Request, exc: VectorStoreError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


class IngestStepRequest(BaseModel):
    offset: int = 0
    batch_size: int | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "embed_model": EMBED_MODEL,
        "llm_model": GROQ_MODEL,
        "chunk_size_words": CHUNK_SIZE_WORDS,
        "chunk_overlap_words": CHUNK_OVERLAP_WORDS,
        "top_k": TOP_K,
        "ingest_step_batch_size": INGEST_STEP_BATCH_SIZE,
        "data_dir": str(DATA_DIR),
    }


@app.get("/api/status")
def status():
    stats = vectorstore.collection_stats()
    pdfs = [p.name for p in list_pdfs(DATA_DIR)]
    return {
        "pdfs_found": pdfs,
        "indexed": stats,
        "ready_to_query": stats["chunk_count"] > 0,
    }


@app.post("/api/ingest/start")
def ingest_start():
    """Resets the vector store and returns the chunk plan (no embedding yet).

    The frontend uses total_chunks to drive a loop of /api/ingest/step calls.
    """
    vectorstore.reset_collection()
    documents, all_chunks = build_chunk_plan()
    if not all_chunks:
        raise HTTPException(status_code=404, detail=f"No PDF files found in {DATA_DIR}")
    return {"documents": documents, "total_chunks": len(all_chunks)}


@app.post("/api/ingest/step")
def ingest_step(req: IngestStepRequest):
    """Embeds and stores one batch of chunks, starting at `offset`.

    Stateless and idempotent-ish by design: each call recomputes the same
    deterministic chunk plan and only touches chunks[offset:offset+batch_size],
    so no server-side job state needs to persist between requests.
    """
    batch_size = req.batch_size or INGEST_STEP_BATCH_SIZE
    try:
        return run_step(req.offset, batch_size)
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/query")
def query(req: QueryRequest):
    stats = vectorstore.collection_stats()
    if stats["chunk_count"] == 0:
        raise HTTPException(
            status_code=400, detail="No documents indexed yet. Run ingestion first."
        )

    top_k = req.top_k or TOP_K

    retrieval_started = time.time()
    try:
        query_vector = embed_query(req.question)
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    hits = vectorstore.query(query_vector, top_k)
    retrieval_seconds = time.time() - retrieval_started

    generation_started = time.time()
    try:
        answer = generate_answer(req.question, hits)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    generation_seconds = time.time() - generation_started

    retrieved_chunks = [
        {
            "rank": i + 1,
            "source": hit["metadata"]["source"],
            "page_number": hit["metadata"]["page_number"],
            "chunk_index": hit["metadata"]["chunk_index"],
            "similarity": round(1 - hit["distance"], 4),
            "text": hit["text"],
        }
        for i, hit in enumerate(hits)
    ]

    return {
        "question": req.question,
        "retrieved_chunks": retrieved_chunks,
        "answer": answer,
        "llm_model": GROQ_MODEL,
        "embed_model": EMBED_MODEL,
        "timings_seconds": {
            "retrieval": round(retrieval_seconds, 3),
            "generation": round(generation_seconds, 3),
        },
    }
