# RAG Explorer

A React + FastAPI demo that walks through a full **Retrieval-Augmented Generation (RAG)** pipeline end to end — PDF ingestion, chunking, embedding, vector storage, retrieval, and LLM answer generation — with every stage visible in the UI as it happens.

It's built as a *teaching tool*: instead of hiding the pipeline behind a single chat box, you see the chunks it created, the embedding vectors it generated, what got retrieved for your question and how similar each match was, and exactly which chunks the LLM used to write its answer.

> 📖 For a deep, diagram-heavy technical walkthrough of every module and design decision, see **[Flow_Control.md](Flow_Control.md)**.
> ☁️ To deploy this to Vercel, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## Table of contents

- [Demo](#demo)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running it](#running-it)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Sample data](#sample-data)
- [Troubleshooting](#troubleshooting)

---

## Demo

Asking a question retrieves the top-4 matching chunks (with similarity scores and source/page attribution) and generates a cited answer from them:

![Retrieved chunks and generated answer for "What payment methods does the Checkout & Payment module support?"](docs/screenshots/query-checkout-payment.png)

Every question is answered strictly from what was retrieved — here the retrieved chunks come from two different documents (Notification Service and Inventory Management), and the answer cites the specific requirement ID and source it drew from:

![Retrieved chunks and generated answer for "How does the platform prevent overselling during flash sales?"](docs/screenshots/query-overselling-prevention.png)

---

## How it works

### Architecture

```mermaid
flowchart TB
    subgraph Browser["Browser"]
        UI["React UI<br/>pipeline stepper · ingest panel · query box · results"]
    end

    subgraph Backend["FastAPI Backend"]
        API["main.py — REST endpoints"]
        PIPE["ingest_pipeline.py<br/>pdf_loader → chunker → embeddings → vectorstore"]
        LLM["llm.py"]
    end

    subgraph Cloud["Hosted services"]
        NOMIC["Nomic Atlas API<br/>nomic-embed-text-v1.5"]
        CHROMA[("Chroma Cloud<br/>vector store")]
        GROQ["Groq API<br/>llama-3.1-8b-instant"]
    end

    PDFS[("data/data/*.pdf")]

    UI <-->|fetch /api/*| API
    API --> PIPE
    PIPE --> PDFS
    PIPE <-->|embed| NOMIC
    PIPE <--> CHROMA
    API <-->|retrieve| CHROMA
    API --> LLM <-->|chat completion| GROQ
```

### The pipeline, step by step

```mermaid
flowchart LR
    A["📄 PDF files<br/>data/data/"] --> B["✂️ Chunk<br/>150 words,<br/>30-word overlap"]
    B --> C["🧮 Embed<br/>Nomic Atlas ·<br/>nomic-embed-text-v1.5"]
    C --> D[("🗄️ Store<br/>Chroma Cloud")]
    D --> E["🔎 Retrieve<br/>top-4 by<br/>cosine similarity"]
    E --> F["✨ Generate<br/>Groq ·<br/>llama-3.1-8b-instant"]
    F --> G["✅ Cited answer"]
```

1. **Ingest** — every PDF in `data/data/` is read page by page (`pypdf`).
2. **Chunk** — each page's text is split into overlapping ~150-word windows (chunks never cross a page boundary, so page numbers stay accurate for citations).
3. **Embed** — each chunk is sent to **Nomic's hosted Atlas API** (`nomic-embed-text-v1.5`), using Nomic's recommended `search_document` task type.
4. **Store** — chunk text, its embedding, and metadata (source file, page, chunk index) are saved in a **Chroma Cloud** collection.
5. **Retrieve** — when you ask a question, it's embedded with the `search_query` task type and Chroma Cloud returns the top-4 most similar chunks.
6. **Generate** — those 4 chunks are handed to **Groq** (`llama-3.1-8b-instant`), which is instructed to answer *only* from that context and cite `(source, page)` for every claim.

All of this — including live per-document ingestion progress and per-chunk previews — is rendered in the UI as it happens. Ingestion itself is driven from the browser: `POST /api/ingest/start` resets the store and returns the chunk plan, then the frontend loops calling `POST /api/ingest/step` with an advancing offset (each call embeds ~20 chunks) until done. This is a stateless design — no server-side background job — so it works the same whether the backend runs as a long-lived local process or as short-lived Vercel serverless functions.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite 5 |
| Backend API | FastAPI (Python) |
| PDF parsing | [pypdf](https://pypdf.readthedocs.io/) |
| Embeddings | [Nomic Atlas API](https://atlas.nomic.ai) — `nomic-embed-text-v1.5` |
| Vector store | [Chroma Cloud](https://www.trychroma.com/cloud) |
| LLM | [Groq API](https://console.groq.com) — `llama-3.1-8b-instant` |

> This project previously ran fully offline against a local Ollama server and a local ChromaDB folder. That path was replaced with the hosted services above so the same codebase deploys directly to Vercel (see [DEPLOYMENT.md](DEPLOYMENT.md)) — both Nomic Atlas and Chroma Cloud have usable free tiers.

---

## Prerequisites

- **Python 3.12** with the packages in `backend/requirements.txt`
- **Node.js 20+** and npm
- A **Groq API key** — [console.groq.com](https://console.groq.com)
- A **Nomic API key** — [atlas.nomic.ai](https://atlas.nomic.ai) (1M free tokens included)
- A **Chroma Cloud** account and database — [trychroma.com/cloud](https://www.trychroma.com/cloud)

---

## Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Open `backend/.env` and fill in your keys:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

NOMIC_API_KEY=your_nomic_api_key_here
EMBED_MODEL=nomic-embed-text-v1.5

CHROMA_API_KEY=your_chroma_cloud_api_key_here
CHROMA_TENANT=your_chroma_tenant_id
CHROMA_DATABASE=your_chroma_database_name
```

> ⚠️ **Windows note:** `chromadb` depends on a compiled `chroma-hnswlib` extension. If `pip install` pulls a version with no prebuilt wheel for your Python version, pin one explicitly:
> ```bash
> pip install chroma-hnswlib==0.7.5
> ```

### 2. Frontend

```bash
cd frontend
npm install
```

---

## Running it

```bash
# 1 — backend API
cd backend
python -m uvicorn app.main:app --port 8000

# 2 — frontend dev server
cd frontend
npm run dev
```

Then open **http://localhost:5173**.

```mermaid
sequenceDiagram
    participant You
    participant UI as Browser
    participant API as Backend

    You->>UI: Click "Run Ingestion"
    UI->>API: POST /api/ingest/start
    API-->>UI: {documents, total_chunks}
    loop until offset >= total_chunks
        UI->>API: POST /api/ingest/step {offset}
        API-->>UI: {embedded_in_step, next_offset, done, sample_chunks}
    end
    Note over UI: Progress bar + per-document<br/>status fill in live, client-driven

    You->>UI: Type a question, click "Ask"
    UI->>API: POST /api/query
    API-->>UI: retrieved chunks + generated answer
    Note over UI: Chunks + cited answer render
```

Click **Run Ingestion** to process every PDF in `data/data`, then ask a question once at least some documents show `done`. You can start asking questions about already-indexed documents while the rest are still being embedded.

---

## Configuration

Everything is configurable via `backend/.env` (see `backend/.env.example`):

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model used for answer generation |
| `NOMIC_API_KEY` | *(required)* | Your Nomic Atlas API key |
| `EMBED_MODEL` | `nomic-embed-text-v1.5` | Nomic embedding model |
| `CHROMA_API_KEY` | *(required)* | Your Chroma Cloud API key |
| `CHROMA_TENANT` | *(required)* | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | *(required)* | Chroma Cloud database name |
| `CHUNK_SIZE_WORDS` | `150` | Words per chunk |
| `CHUNK_OVERLAP_WORDS` | `30` | Word overlap between consecutive chunks |
| `TOP_K` | `4` | Number of chunks retrieved per query |
| `INGEST_STEP_BATCH_SIZE` | `20` | Chunks embedded per `/api/ingest/step` call |
| `DATA_DIR` | `backend/data/data` | Folder scanned for source PDFs |

`frontend/.env` (see `frontend/.env.example`) has one variable: `VITE_API_BASE_URL`, the backend's URL (defaults to `http://localhost:8000` if unset).

---

## Project structure

```
RAG_Explorer_E_Commerce/
├── backend/                    FastAPI app (self-contained — deployable as its own Vercel project)
│   ├── app/
│   │   ├── pdf_loader.py       Extracts per-page text from PDFs (pypdf)
│   │   ├── chunker.py          Splits page text into overlapping word-based chunks
│   │   ├── embeddings.py       Calls the Nomic Atlas API for embeddings
│   │   ├── vectorstore.py      Chroma Cloud client wrapper
│   │   ├── ingest_pipeline.py  Stateless chunk-plan + step-based ingestion
│   │   ├── llm.py              Groq chat completion, grounded in retrieved chunks
│   │   └── main.py             FastAPI routes
│   ├── data/data/               Source PDFs to ingest (sample: 10 ShopSphere e-commerce BRDs)
│   ├── main.py                 Vercel Python entrypoint (re-exports app.main:app)
│   ├── vercel.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   React (Vite) UI
│   └── src/
│       ├── App.jsx             Pipeline state machine (drives the ingest loop)
│       └── components/         Stepper, ingest panel, query panel, results
├── README.md                   This file
├── Flow_Control.md             Deep-dive: diagrams, API reference, design decisions
└── DEPLOYMENT.md               Step-by-step Vercel deployment guide
```

---

## Sample data

`backend/data/data/` ships with 10 fictional Business Requirement Documents for "ShopSphere Technologies Pvt. Ltd.", an invented e-commerce platform — one BRD per module (User Registration & Login, Product Catalog, Shopping Cart, Checkout & Payment, Order Management, Inventory, Returns & Refunds, Customer Reviews, Admin Dashboard, Notification Service). They share terminology, stakeholders, and integrated systems across files to simulate a real enterprise knowledge base, which makes for a good multi-document retrieval test.

**To use your own PDFs:** drop them into `backend/data/data/` and click **Run Ingestion** again — it fully re-chunks and re-embeds everything currently in that folder.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: hnswlib` or chromadb install fails | `pip install chroma-hnswlib==0.7.5` |
| `/api/status` or `/api/query` returns `502 Could not connect to Chroma Cloud` | Check `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` in `backend/.env` and that the database exists in the Chroma Cloud dashboard |
| Ingestion fails with a Nomic error | Check `NOMIC_API_KEY` in `backend/.env` and remaining token quota |
| Query fails with a Groq error | Check `GROQ_API_KEY` in `backend/.env` and that the account has access to `GROQ_MODEL` |
| Frontend can't reach the backend | Confirm the backend is running on port 8000; in production, confirm `VITE_API_BASE_URL` was set *before* the frontend was built |
