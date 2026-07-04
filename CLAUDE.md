# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG (Retrieval-Augmented Generation) Explorer: a React UI backed by a FastAPI service that makes every stage of a RAG pipeline visible — PDF ingestion, chunking, embedding, vector storage, retrieval, and LLM answer generation. It's a demonstration/explainer tool, not a production RAG app, so intermediate pipeline state (chunk previews, embedding dimension, per-document progress, similarity scores) is deliberately surfaced in the UI rather than hidden. See `README.md` for setup/run instructions.

## Commands

Backend (from `backend/`):
- `pip install -r requirements.txt` — install deps
- `python -m uvicorn app.main:app --port 8000` — run the API

Frontend (from `frontend/`):
- `npm install`
- `npm run dev` — Vite dev server on :5173
- `npm run build`

There is no test suite yet.

## Architecture

- `data/data/` — source PDFs the pipeline ingests (sample corpus: 10 fictional e-commerce BRDs, see below).
- `backend/app/pdf_loader.py` — extracts text per page via `pypdf`.
- `backend/app/chunker.py` — splits each page's text into overlapping word-window chunks (`CHUNK_SIZE_WORDS`/`CHUNK_OVERLAP_WORDS` in config, default 150/30). Chunking is per-page (chunks never span a page boundary) so page numbers stay accurate in metadata.
- `backend/app/embeddings.py` — calls a local Ollama server's `/api/embed` for `nomic-embed-text` vectors. Uses Nomic's recommended `search_document:` / `search_query:` prefixes. Document embedding is parallelized (`ThreadPoolExecutor`, 4 workers) because CPU-only Ollama inference is the throughput bottleneck (~8-10s per 150-word chunk on this hardware) — see "Known constraints" below.
- `backend/app/vectorstore.py` — thin wrapper around a `chromadb.PersistentClient` (`backend/chroma_db/`). Embeddings are supplied explicitly (not via Chroma's own embedding function) since embedding happens through Ollama.
- `backend/app/ingest_job.py` — ingestion runs as a background thread with shared in-memory progress state (`status`, per-document status, `chunks_embedded`/`total_chunks`, sample chunk previews), because a synchronous ingest call would block far past any reasonable HTTP timeout. `POST /api/ingest` starts the job; `GET /api/ingest/progress` polls it. Only one job runs at a time.
- `backend/app/llm.py` — Groq chat completion (`GROQ_MODEL`, default `openai/gpt-oss-120b`) with a system prompt that restricts answers to the retrieved chunks and asks for source/page citations.
- `backend/app/main.py` — FastAPI routes wiring the above together: `/api/status`, `/api/ingest`, `/api/ingest/progress`, `/api/query`, `/api/config`.
- `frontend/src/App.jsx` — top-level state machine driving the pipeline stepper (`components/PipelineStepper.jsx`) across six stages (ingest → chunk → embed → store → retrieve → generate). Polls `/api/ingest/progress` every second while a job is running, and also checks for an already-running job on mount (ingestion can be kicked off independently of the UI).
- `frontend/src/components/` — `IngestPanel` (progress bar, per-doc table, sample chunks), `QueryPanel` (question box + canned sample questions), `ResultsPanel` (retrieved chunks with similarity scores + generated answer).

Config is centralized in `backend/app/config.py`, reading from `backend/.env` (see `.env.example`): `GROQ_API_KEY`, `GROQ_MODEL`, `OLLAMA_BASE_URL`, `EMBED_MODEL`, chunking params, `TOP_K`, `DATA_DIR`, `CHROMA_DIR`.

## Known environment constraints (Windows, this machine)

- `chromadb`'s compiled `chroma-hnswlib` dependency has no prebuilt wheel for every Python/OS combo and there are no C++ build tools installed here — pin `chroma-hnswlib==0.7.5` explicitly if a fresh install pulls a versionless/unbuildable one.
- The scaffolded frontend originally got Vite 8 (Rolldown-based bundler), whose native binding fails to resolve under Node 20.17 + npm 11 here (a known npm optional-deps bug). The frontend is pinned to Vite 5 (esbuild-based) instead — don't bump back to Vite 8+ without confirming the binding issue is resolved.
- Embedding throughput is CPU-bound and slow (~8-10s per 150-word chunk via local Ollama on this hardware); full ingestion of the 10-document sample corpus (~330 chunks) takes several minutes even with 4-way request concurrency. This is why ingestion is a polled background job rather than a blocking request.
- The system's standalone Chrome install attaches new `--headless --print-to-pdf` invocations to an already-running browser session on this machine instead of launching an isolated headless instance, silently producing broken single-page output. Use Playwright's bundled Chromium (already installed in this Python env) for any programmatic PDF rendering or screenshotting instead.

## Sample data

`data/data/` holds 10 sample Business Requirement Documents for a fictional e-commerce platform ("ShopSphere Technologies Pvt. Ltd."), used as realistic multi-document source material for exercising ingestion, chunking, embedding, retrieval, and Q&A. Each BRD covers one e-commerce module (registration/login, catalog, cart, checkout/payment, order management, inventory, returns/refunds, reviews, admin dashboard, notifications) and follows a consistent 23-section structure (Executive Summary, Business/Functional/Non-Functional Requirements, User Stories, Acceptance Criteria, Business Rules, Risks, Glossary, etc.) with realistic requirement IDs (BR-, FR-, NFR-, US-, AC-, RULE-). The documents intentionally share terminology, stakeholder names, and integrated systems (payment gateway, ERP, CRM, email/SMS services, inventory system) across files to simulate a real enterprise knowledge base for cross-document retrieval testing. Swap in your own PDF(s) by dropping them into `data/data/` and re-running ingestion.
