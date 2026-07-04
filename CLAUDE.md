# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG (Retrieval-Augmented Generation) Explorer: a React UI backed by a FastAPI service that makes every stage of a RAG pipeline visible — PDF ingestion, chunking, embedding, vector storage, retrieval, and LLM answer generation. It's a demonstration/explainer tool, not a production RAG app, so intermediate pipeline state (chunk previews, embedding dimension, per-document progress, similarity scores) is deliberately surfaced in the UI rather than hidden. See `README.md` for setup/run instructions, `Flow_Control.md` for diagrams, and `DEPLOYMENT.md` for Vercel deployment.

The backend uses **hosted cloud services** (Nomic Atlas for embeddings, Chroma Cloud for the vector store) rather than local ones, specifically so it deploys on Vercel. There is no local-only mode anymore — running locally still requires Nomic Atlas + Chroma Cloud accounts (both have free tiers). An earlier version of this app ran fully offline against local Ollama + a local ChromaDB folder; that path was fully replaced, not kept side-by-side (recoverable from git history if needed).

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

- `backend/data/data/` — source PDFs the pipeline ingests (sample corpus: 10 fictional e-commerce BRDs, see below). Lives under `backend/` (not the repo root) so the backend is self-contained when deployed as its own Vercel project.
- `backend/app/pdf_loader.py` — extracts text per page via `pypdf`.
- `backend/app/chunker.py` — splits each page's text into overlapping word-window chunks (`CHUNK_SIZE_WORDS`/`CHUNK_OVERLAP_WORDS` in config, default 150/30). Chunking is per-page (chunks never span a page boundary) so page numbers stay accurate in metadata.
- `backend/app/embeddings.py` — calls the **Nomic Atlas hosted API** (`nomic.embed.text(...)`) for `nomic-embed-text-v1.5` vectors, using Nomic's `task_type="search_document"` / `"search_query"` convention (the hosted API's equivalent of the old local-Ollama text-prefix trick). `nomic.login(NOMIC_API_KEY)` is called lazily on first use, not at import time.
- `backend/app/vectorstore.py` — wraps a `chromadb.CloudClient` (Chroma Cloud). **Constructed lazily** (`_get_client()`), not at module import time — `CloudClient()` validates its connection eagerly, so building it eagerly would crash the entire API (including unrelated endpoints like `/api/health`) on any Chroma Cloud hiccup or missing credentials. Every function converts failures into a typed `VectorStoreError`; `main.py` registers a global exception handler that turns those into a clean `502` instead of a raw stack trace. Embeddings are supplied explicitly (not via Chroma's own embedding function) since embedding happens through the Nomic API.
- `backend/app/ingest_pipeline.py` — **stateless** ingestion, replacing an earlier background-thread design. `build_chunk_plan()` re-parses and re-chunks every PDF on each call (cheap, ~1-2s for 10 PDFs) so no server-side state needs to persist between requests — required because Vercel Functions don't reliably share memory across invocations and can't run a long background job past their timeout. `run_step(offset, batch_size)` embeds+stores exactly `chunks[offset:offset+batch_size]`. The frontend owns the progress loop, calling `POST /api/ingest/step` repeatedly with an advancing offset.
- `backend/app/llm.py` — Groq chat completion (`GROQ_MODEL`, default `llama-3.1-8b-instant`) with a system prompt that restricts answers to the retrieved chunks and asks for source/page citations.
- `backend/app/main.py` — FastAPI routes: `/api/status`, `/api/ingest/start`, `/api/ingest/step`, `/api/query`, `/api/config`, `/api/health`, plus the `VectorStoreError` exception handler. CORS is `allow_origins=["*"]` (tighten to the deployed frontend origin post-deploy — see `DEPLOYMENT.md`).
- `backend/main.py` — Vercel Python-runtime entrypoint; just re-exports `app.main:app` (Vercel's zero-config FastAPI detection looks for `main.py`/`app.py`/etc. at the project root).
- `frontend/src/App.jsx` — top-level state machine. Owns the ingestion loop directly (`startIngest()` then repeated `ingestStep(offset, batchSize)` calls, awaited in sequence) rather than polling a server-side progress endpoint — there isn't one anymore. Derives per-document status (`pending`/`embedding`/`done`) client-side from cumulative chunk-count ranges vs. the current offset. Also drives the 6-stage pipeline stepper (`components/PipelineStepper.jsx`).
- `frontend/src/components/` — `IngestPanel` (progress bar, per-doc table, sample chunks), `QueryPanel` (question box + canned sample questions), `ResultsPanel` (retrieved chunks with similarity scores + generated answer).
- `frontend/src/api.js` — `BASE_URL` comes from `VITE_API_BASE_URL` (build-time Vite env var), falling back to `http://localhost:8000`.

Config is centralized in `backend/app/config.py`, reading from `backend/.env` (see `.env.example`): `GROQ_API_KEY`, `GROQ_MODEL`, `NOMIC_API_KEY`, `EMBED_MODEL`, `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`, chunking params, `TOP_K`, `INGEST_STEP_BATCH_SIZE`, `DATA_DIR`.

## Known environment constraints (Windows, this machine)

- `chromadb`'s compiled `chroma-hnswlib` dependency has no prebuilt wheel for every Python/OS combo and there are no C++ build tools installed here — pin `chroma-hnswlib==0.7.5` explicitly if a fresh install pulls a versionless/unbuildable one.
- The scaffolded frontend originally got Vite 8 (Rolldown-based bundler), whose native binding fails to resolve under Node 20.17 + npm 11 here (a known npm optional-deps bug). The frontend is pinned to Vite 5 (esbuild-based) instead — don't bump back to Vite 8+ without confirming the binding issue is resolved.
- `chromadb.CloudClient()` validates its connection **eagerly at construction time** (confirmed by testing with empty credentials — it raised immediately, not on first query). This is why `vectorstore.py` constructs it lazily behind `_get_client()` rather than at module import time.
- The system's standalone Chrome install attaches new `--headless --print-to-pdf` invocations to an already-running browser session on this machine instead of launching an isolated headless instance, silently producing broken single-page output. Use Playwright's bundled Chromium (already installed in this Python env) for any programmatic PDF rendering or screenshotting instead.

## Sample data

`backend/data/data/` holds 10 sample Business Requirement Documents for a fictional e-commerce platform ("ShopSphere Technologies Pvt. Ltd."), used as realistic multi-document source material for exercising ingestion, chunking, embedding, retrieval, and Q&A. Each BRD covers one e-commerce module (registration/login, catalog, cart, checkout/payment, order management, inventory, returns/refunds, reviews, admin dashboard, notifications) and follows a consistent 23-section structure (Executive Summary, Business/Functional/Non-Functional Requirements, User Stories, Acceptance Criteria, Business Rules, Risks, Glossary, etc.) with realistic requirement IDs (BR-, FR-, NFR-, US-, AC-, RULE-). The documents intentionally share terminology, stakeholder names, and integrated systems (payment gateway, ERP, CRM, email/SMS services, inventory system) across files to simulate a real enterprise knowledge base for cross-document retrieval testing. Swap in your own PDF(s) by dropping them into `backend/data/data/` and re-running ingestion.
