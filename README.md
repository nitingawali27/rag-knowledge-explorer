# RAG Explorer

A React + FastAPI demo that walks through a full Retrieval-Augmented Generation pipeline end to end: PDF ingestion, chunking, embedding, vector storage, retrieval, and LLM answer generation — all visible in the UI as it happens.

## Architecture

```
data/data/        Source PDFs to ingest (sample: 10 ShopSphere e-commerce BRDs)
backend/          FastAPI app
  app/
    pdf_loader.py     Extracts per-page text from PDFs (pypdf)
    chunker.py         Splits page text into overlapping word-based chunks
    embeddings.py       Calls a local Ollama server for Nomic Embed vectors
    vectorstore.py      ChromaDB persistent client (backend/chroma_db)
    ingest_job.py        Background thread + progress state for /api/ingest
    llm.py               Groq chat completion (openai/gpt-oss-120b) grounded in retrieved chunks
    main.py               FastAPI routes
frontend/         React (Vite) UI: pipeline stepper, ingestion progress, query box, retrieved chunks, answer
```

Flow: PDFs in `data/data` → chunked (150 words, 30-word overlap, per page) → embedded via Ollama's `nomic-embed-text` (with the `search_document:` / `search_query:` prefixes Nomic recommends) → stored in a persistent local ChromaDB collection → top-K retrieval by cosine similarity → Groq's `openai/gpt-oss-120b` generates the final answer strictly from the retrieved chunks.

## Prerequisites

- Python 3.12 with the packages in `backend/requirements.txt`
- Node.js 20+ and npm
- [Ollama](https://ollama.com) installed locally, with the embedding model pulled:
  ```
  ollama pull nomic-embed-text
  ```
- A Groq API key ([console.groq.com](https://console.groq.com))

## Setup

**Backend**

```
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in GROQ_API_KEY
```

> Note (Windows): `chromadb` depends on a compiled `chroma-hnswlib` extension. If pip pulls a version with no prebuilt wheel for your Python version, pin one explicitly, e.g. `pip install chroma-hnswlib==0.7.5`.

**Frontend**

```
cd frontend
npm install
```

## Running

1. Start Ollama (if it isn't already running as a service): `ollama serve`
2. Start the backend: `cd backend && python -m uvicorn app.main:app --port 8000`
3. Start the frontend: `cd frontend && npm run dev`
4. Open http://localhost:5173

Click **Run Ingestion** to process every PDF in `data/data`, then ask a question. Ingestion runs as a background job with live progress (it embeds on CPU via Ollama, so processing the full 10-document sample corpus — ~330 chunks — takes several minutes).

## Configuration

All configurable via `backend/.env` (see `.env.example`): `GROQ_API_KEY`, `GROQ_MODEL`, `OLLAMA_BASE_URL`, `EMBED_MODEL`, `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`, `TOP_K`, `DATA_DIR`, `CHROMA_DIR`.

## Swapping in your own PDF(s)

Drop any PDF(s) into `data/data/` and click **Run Ingestion** again — it re-chunks and re-embeds everything currently in that folder from scratch.
