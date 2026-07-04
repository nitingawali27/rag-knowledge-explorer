# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG (Retrieval-Augmented Generation) Explorer: a React UI backed by a FastAPI service that makes every stage of a RAG pipeline visible — PDF ingestion, chunking, embedding, vector storage, retrieval, and LLM answer generation. It's a demonstration/explainer tool, not a production RAG app, so intermediate pipeline state (chunk previews, embedding dimension, per-document progress, similarity scores) is deliberately surfaced in the UI rather than hidden. See `README.md` for setup/run instructions and `Flow_Control.md` for diagrams.

The backend runs fully offline/local: embeddings come from a local **Ollama** server (`nomic-embed-text`) and vectors are stored in a local **ChromaDB** folder (`backend/chroma_db/`, gitignored). Only Groq (LLM answer generation) is a hosted API call. A later revision of this app briefly migrated to hosted cloud services (Nomic Atlas + Chroma Cloud) to support Vercel deployment; that path was reverted back to local-only (recoverable from git history if needed).

## Commands

Backend (from `backend/`):
- `pip install -r requirements.txt` — install deps
- `python -m uvicorn app.main:app --port 8000` — run the API locally

Frontend (from `frontend/`):
- `npm install`
- `npm run dev` — Vite dev server on :5173
- `npm run build`

There is no test suite yet.

## Architecture

- `backend/data/data/` — source PDFs the pipeline ingests (sample corpus: 10 fictional e-commerce BRDs, see below).
- `backend/app/pdf_loader.py` — extracts text per page via `pypdf`.
- `backend/app/chunker.py` — splits each page's text into overlapping word-window chunks (`CHUNK_SIZE_WORDS`/`CHUNK_OVERLAP_WORDS` in config, default 150/30). Chunking is per-page (chunks never span a page boundary) so page numbers stay accurate in metadata.
- `backend/app/embeddings.py` — calls a local **Ollama** server's `/api/embed` for `nomic-embed-text` vectors. Uses Nomic's recommended `search_document:` / `search_query:` prefixes. Document embedding is parallelized (`ThreadPoolExecutor`, 4 workers) because CPU-only Ollama inference is the throughput bottleneck (~8-10s per 150-word chunk on this hardware) — see "Known constraints" below.
- `backend/app/vectorstore.py` — thin wrapper around a `chromadb.PersistentClient` (`backend/chroma_db/`, gitignored). **Constructed lazily** (`_get_client()`), not at module import time, so a bad `CHROMA_DIR` path doesn't crash unrelated endpoints like `/api/health`. Every function converts failures into a typed `VectorStoreError`; `main.py` registers a global exception handler that turns those into a clean `502` instead of a raw stack trace. Embeddings are supplied explicitly (not via Chroma's own embedding function) since embedding happens through Ollama.
- `backend/app/ingest_pipeline.py` — **stateless** ingestion (no server-side background job/polling). `build_chunk_plan()` re-parses and re-chunks every PDF on each call (cheap, ~1-2s for 10 PDFs). `run_step(offset, batch_size)` embeds+stores exactly `chunks[offset:offset+batch_size]`. The frontend owns the progress loop, calling `POST /api/ingest/step` repeatedly with an advancing offset — this keeps the UI's per-batch progress bar without needing a polled `/progress` endpoint.
- `backend/app/llm.py` — Groq chat completion (`GROQ_MODEL`, default `llama-3.1-8b-instant`) with a system prompt that restricts answers to the retrieved chunks and asks for source/page citations.
- `backend/app/main.py` — FastAPI routes: `/api/status`, `/api/ingest/start`, `/api/ingest/step`, `/api/query`, `/api/config`, `/api/health`, plus the `VectorStoreError` exception handler. CORS is restricted to the local Vite dev origins (`http://localhost:5173`, `http://127.0.0.1:5173`).
- `frontend/src/App.jsx` — top-level state machine. Owns the ingestion loop directly (`startIngest()` then repeated `ingestStep(offset, batchSize)` calls, awaited in sequence). Derives per-document status (`pending`/`embedding`/`done`) client-side from cumulative chunk-count ranges vs. the current offset. Also drives the 6-stage pipeline stepper (`components/PipelineStepper.jsx`).
- `frontend/src/components/` — `IngestPanel` (progress bar, per-doc table, sample chunks), `QueryPanel` (question box + canned sample questions), `ResultsPanel` (retrieved chunks with similarity scores + generated answer).
- `frontend/src/api.js` — `BASE_URL` comes from `VITE_API_BASE_URL` (build-time Vite env var), falling back to `http://localhost:8000`.

Config is centralized in `backend/app/config.py`, reading from `backend/.env` (see `.env.example`): `GROQ_API_KEY`, `GROQ_MODEL`, `OLLAMA_BASE_URL`, `EMBED_MODEL`, chunking params, `TOP_K`, `INGEST_STEP_BATCH_SIZE`, `DATA_DIR`, `CHROMA_DIR`.

## Known environment constraints (Windows, this machine)

- Older `chromadb` releases (e.g. 0.5.15) depend on `chroma-hnswlib==0.7.6`, which has no prebuilt Windows wheel and needs C++ build tools we don't have here. Leave `chromadb` unpinned in `requirements.txt` — current releases (tested: 1.5.9) bundle their vector index differently and install cleanly with no compiled-extension build step.
- The scaffolded frontend originally got Vite 8 (Rolldown-based bundler), whose native binding fails to resolve under Node 20.17 + npm 11 here (a known npm optional-deps bug). The frontend is pinned to Vite 5 (esbuild-based) instead — don't bump back to Vite 8+ without confirming the binding issue is resolved.
- Embedding throughput is CPU-bound and slow (~8-10s per 150-word chunk via local Ollama on this hardware); full ingestion of the 10-document sample corpus (~330 chunks) takes several minutes even with 4-way request concurrency.
- Requires `ollama serve` running and `ollama pull nomic-embed-text` done beforehand — `embeddings.py` raises a clear `EmbeddingError` pointing this out if Ollama isn't reachable.
- The system's standalone Chrome install attaches new `--headless --print-to-pdf` invocations to an already-running browser session on this machine instead of launching an isolated headless instance, silently producing broken single-page output. Use Playwright's bundled Chromium (already installed in this Python env) for any programmatic PDF rendering or screenshotting instead.

## Sample data

`backend/data/data/` holds 10 sample Business Requirement Documents for a fictional e-commerce platform ("ShopSphere Technologies Pvt. Ltd."), used as realistic multi-document source material for exercising ingestion, chunking, embedding, retrieval, and Q&A. Each BRD covers one e-commerce module (registration/login, catalog, cart, checkout/payment, order management, inventory, returns/refunds, reviews, admin dashboard, notifications) and follows a consistent 23-section structure (Executive Summary, Business/Functional/Non-Functional Requirements, User Stories, Acceptance Criteria, Business Rules, Risks, Glossary, etc.) with realistic requirement IDs (BR-, FR-, NFR-, US-, AC-, RULE-). The documents intentionally share terminology, stakeholder names, and integrated systems (payment gateway, ERP, CRM, email/SMS services, inventory system) across files to simulate a real enterprise knowledge base for cross-document retrieval testing. Swap in your own PDF(s) by dropping them into `backend/data/data/` and re-running ingestion.
