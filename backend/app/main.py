import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import ingest_job, vectorstore
from .config import (
    CHUNK_OVERLAP_WORDS,
    CHUNK_SIZE_WORDS,
    DATA_DIR,
    EMBED_MODEL,
    GROQ_MODEL,
    TOP_K,
)
from .embeddings import EmbeddingError, embed_query
from .llm import LLMError, generate_answer
from .pdf_loader import list_pdfs

app = FastAPI(title="RAG Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


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


@app.post("/api/ingest")
def ingest():
    started = ingest_job.start_ingestion()
    if not started:
        raise HTTPException(status_code=409, detail="Ingestion is already running.")
    return {"started": True}


@app.get("/api/ingest/progress")
def ingest_progress():
    return ingest_job.get_state()


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
