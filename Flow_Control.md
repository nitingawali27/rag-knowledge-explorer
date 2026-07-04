# Flow_Control.md — RAG Explorer

A complete, diagram-first walkthrough of this project: what it is, how it's structured, and exactly how data moves through it — from a PDF on disk to a cited, LLM-generated answer.

---

## 1. What this is

**RAG Explorer** is a React + FastAPI application that demonstrates a full Retrieval-Augmented Generation (RAG) pipeline over a folder of PDFs, with every stage — ingestion, chunking, embedding, storage, retrieval, and answer generation — visible in the UI as it happens. It's a teaching/demo tool, not a production RAG system: intermediate pipeline state (chunk previews, embedding dimensions, per-document progress, similarity scores) is deliberately surfaced rather than hidden behind a single "ask a question" box.

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite 5 |
| Backend API | FastAPI (Python) |
| PDF parsing | pypdf |
| Embedding model | `nomic-embed-text`, served locally via Ollama |
| Vector store | ChromaDB (local, persistent, on disk) |
| LLM (answer generation) | Groq API — `llama-3.1-8b-instant` |

---

## 2. System architecture

```mermaid
flowchart TB
    subgraph Browser["Browser — localhost:5173"]
        UI[React App]
    end

    subgraph Backend["FastAPI Backend — localhost:8000"]
        API["main.py<br/>REST endpoints"]
        JOB["ingest_job.py<br/>background thread"]
        LOADER["pdf_loader.py"]
        CHUNKER["chunker.py"]
        EMBED["embeddings.py"]
        VSTORE["vectorstore.py"]
        LLM["llm.py"]
    end

    subgraph External["External services (local + cloud)"]
        OLLAMA["Ollama server<br/>localhost:11434<br/>nomic-embed-text"]
        CHROMA[("ChromaDB<br/>backend/chroma_db/")]
        GROQ["Groq API (cloud)<br/>llama-3.1-8b-instant"]
    end

    PDFS[("data/data/*.pdf")]

    UI <-->|fetch: /api/*| API
    API --> JOB
    JOB --> LOADER --> PDFS
    JOB --> CHUNKER
    JOB --> EMBED
    API --> EMBED
    EMBED <-->|POST /api/embed| OLLAMA
    JOB --> VSTORE
    API --> VSTORE
    VSTORE <--> CHROMA
    API --> LLM
    LLM <-->|chat.completions| GROQ
```

---

## 3. Ingestion flow — PDF → searchable vectors

Triggered when the user clicks **Run Ingestion** (`POST /api/ingest`). This starts a background thread and returns immediately; the frontend polls `GET /api/ingest/progress` every second until it finishes.

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant API as FastAPI (main.py)
    participant JOB as ingest_job.py (bg thread)
    participant PDF as pdf_loader.py
    participant CHK as chunker.py
    participant EMB as embeddings.py
    participant OLL as Ollama (nomic-embed-text)
    participant VS as vectorstore.py
    participant DB as ChromaDB

    U->>API: POST /api/ingest
    API->>JOB: start_ingestion() [spawns thread]
    API-->>U: 202 {started: true}

    JOB->>VS: reset_collection()
    VS->>DB: delete + recreate collection

    loop for each PDF in data/data/
        JOB->>PDF: load_pdf_pages(path)
        PDF-->>JOB: [{page_number, text}, ...]
        JOB->>CHK: chunk_document(pages)
        CHK-->>JOB: [Chunk(150 words, 30 overlap), ...]
    end

    loop for each document, batches of 16 chunks
        JOB->>EMB: embed_documents([chunk.text, ...])
        EMB->>OLL: POST /api/embed (x4 concurrent, "search_document: " prefix)
        OLL-->>EMB: [[768-dim vector], ...]
        EMB-->>JOB: vectors
        JOB->>VS: add_chunks(batch, vectors)
        VS->>DB: collection.add(ids, embeddings, documents, metadatas)
        JOB->>JOB: update progress state (chunks_embedded, sample_chunks)
    end

    loop every 1s until done
        U->>API: GET /api/ingest/progress
        API-->>U: {status, chunks_embedded, total_chunks, documents[], ...}
    end
```

**Chunk ID format:** `{filename}::p{page_number}::c{running_index}` — e.g. `BRD-EC-CKP-004-Checkout-Payment.pdf::p2::c14`.

### Per-document ingestion status lifecycle

```mermaid
stateDiagram-v2
    [*] --> chunked: pypdf extracts text,<br/>chunker splits into windows
    chunked --> embedding: first batch sent to Ollama
    embedding --> done: all chunks for this doc embedded + stored
    done --> [*]
```

---

## 4. Query flow — question → grounded answer

Triggered when the user clicks **Ask** (`POST /api/query {question}`). This one is fast and synchronous (no polling needed).

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant API as FastAPI (main.py)
    participant EMB as embeddings.py
    participant OLL as Ollama
    participant VS as vectorstore.py
    participant DB as ChromaDB
    participant LLM as llm.py
    participant GROQ as Groq API

    U->>API: POST /api/query {question}
    API->>VS: collection_stats()
    alt no chunks indexed
        API-->>U: 400 "Run ingestion first"
    end

    API->>EMB: embed_query(question)
    EMB->>OLL: POST /api/embed ("search_query: " prefix)
    OLL-->>EMB: 768-dim vector
    EMB-->>API: query_vector

    API->>VS: query(query_vector, top_k=4)
    VS->>DB: collection.query(query_embeddings, n_results=4)
    DB-->>VS: 4 nearest chunks (cosine distance)
    VS-->>API: [{text, metadata, distance}, ...]

    API->>LLM: generate_answer(question, chunks)
    LLM->>LLM: build numbered context block<br/>(source + page + text per chunk)
    LLM->>GROQ: chat.completions.create(system + user prompt)
    GROQ-->>LLM: grounded answer with citations
    LLM-->>API: answer text

    API-->>U: {question, retrieved_chunks[], answer, timings}
```

The system prompt sent to Groq enforces three rules: answer **only** from the given context, **cite** `(source: FILE, p.N)` for claims, and **say so explicitly** if the context doesn't contain the answer — this is what keeps the demo grounded instead of hallucinating.

---

## 5. Frontend: pipeline stepper state machine

`App.jsx` derives a single active stage (out of 6) plus a set of "completed" stages from `status`, `progress`, `asking`, and `result` — shown visually by `PipelineStepper.jsx`.

```mermaid
stateDiagram-v2
    [*] --> Ingest
    Ingest --> Chunk: chunks_embedded > 0
    Chunk --> Embed
    Embed --> Store: any chunks persisted (ready_to_query)
    Store --> Retrieve: user clicks Ask
    Retrieve --> Generate: chunks retrieved, answer streaming
    Generate --> Retrieve: user asks another question

    note right of Store
        Steps 1-4 all light up as soon
        as ANY data is queryable — even
        if a separate ingest run is still
        embedding additional documents.
        Ingestion and querying can
        legitimately overlap.
    end note
```

### Component / data flow on the frontend

```mermaid
flowchart LR
    App["App.jsx<br/>(state + polling)"] --> Stepper[PipelineStepper.jsx]
    App --> Ingest[IngestPanel.jsx]
    App --> Query[QueryPanel.jsx]
    App --> Results[ResultsPanel.jsx]
    App <-->|api.js| Backend[("FastAPI backend")]

    Ingest -.click Run Ingestion.-> App
    Query -.click Ask.-> App
    App -.progress / result state.-> Stepper
    App -.progress state.-> Ingest
    App -.result state.-> Results
```

---

## 6. Project structure

```
RAG_Explorer_E_Commerce/
├── data/data/                  Source PDFs the pipeline ingests (10 sample BRDs)
├── backend/
│   ├── app/
│   │   ├── config.py           Central config, reads backend/.env
│   │   ├── pdf_loader.py       PDF → per-page plain text
│   │   ├── chunker.py          Per-page text → overlapping word-window chunks
│   │   ├── embeddings.py       Calls Ollama for Nomic embeddings (concurrent)
│   │   ├── vectorstore.py      ChromaDB persistent client wrapper
│   │   ├── ingest_job.py       Background-thread ingestion job + progress state
│   │   ├── llm.py              Groq chat completion, context-grounded prompt
│   │   └── main.py             FastAPI routes
│   ├── chroma_db/              ChromaDB's on-disk persistence (auto-created, gitignored)
│   ├── requirements.txt
│   ├── .env                    Actual secrets/config — gitignored, never committed
│   └── .env.example            Template for .env
├── frontend/
│   ├── src/
│   │   ├── api.js               fetch wrappers for the backend
│   │   ├── App.jsx               Top-level state machine + pipeline stepper logic
│   │   ├── App.css / index.css   Styling
│   │   └── components/
│   │       ├── PipelineStepper.jsx   6-stage visual stepper
│   │       ├── IngestPanel.jsx       Ingestion trigger + live progress
│   │       ├── QueryPanel.jsx        Question input + sample questions
│   │       └── ResultsPanel.jsx      Retrieved chunks + generated answer
│   └── package.json
├── README.md                   Setup/run instructions
├── CLAUDE.md                   Guidance for AI coding agents working in this repo
└── Flow_Control.md             This file
```

> **Note on `data/data`:** Windows filesystems are case-insensitive, so a top-level `Data/` and `data/` are the *same* physical directory here — the real path is `.../Data/data/*.pdf`. `config.py`'s `DATA_DIR` default resolves to exactly this nested path, matching the original project spec.

---

## 7. API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/config` | Current embed/LLM models, chunk size/overlap, top_k, data dir |
| GET | `/api/status` | PDFs found on disk, what's indexed (chunk/doc count, source list), `ready_to_query` |
| POST | `/api/ingest` | Starts the background ingestion job (409 if one is already running) |
| GET | `/api/ingest/progress` | Poll target for live ingestion state |
| POST | `/api/query` | `{question, top_k?}` → retrieved chunks + generated answer |

CORS is restricted to `http://localhost:5173` (the Vite dev server origin).

---

## 8. Key design decisions (and why)

- **Ingestion is a background job, not a blocking request.** Embedding on CPU-only Ollama can take several seconds per chunk; a 300+ chunk corpus can take 15-20+ minutes. A blocking HTTP call would exceed any reasonable timeout and give no feedback. `ingest_job.py` runs on a `threading.Thread`, mutates a lock-guarded in-memory state dict, and `GET /api/ingest/progress` just reads it.
- **Embedding calls are concurrent (4 workers)** via `ThreadPoolExecutor`, tuned empirically for this hardware — CPU-bound Ollama inference is the throughput bottleneck, not the network.
- **Chunking is per-page**, never spanning a page boundary, so `page_number` in chunk metadata is always exactly correct — used for citations in the generated answer.
- **Nomic's prefix convention is honored**: `"search_document: "` on indexed text, `"search_query: "` on queries, for asymmetric retrieval quality.
- **The LLM is told to ground strictly in retrieved context** and cite `(source, page)`, and to admit when context is insufficient.
- **ChromaDB stores pre-computed embeddings directly** (`collection.add(embeddings=...)`) since embedding happens via an external Ollama call, not Chroma's built-in embedding function.
- **`.env` overrides the shell environment** (`load_dotenv(..., override=True)`) so the project's own config always wins over any stale environment variable.

---

## 9. Configuration reference (`backend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Groq API key for answer generation |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Set to `llama-3.1-8b-instant` in this project |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server address |
| `EMBED_MODEL` | `nomic-embed-text` | Must already be pulled: `ollama pull nomic-embed-text` |
| `CHUNK_SIZE_WORDS` | `150` | Words per chunk |
| `CHUNK_OVERLAP_WORDS` | `30` | Word overlap between consecutive chunks on the same page |
| `TOP_K` | `4` | Chunks retrieved per query |
| `DATA_DIR` | `<project_root>/data/data` | Where source PDFs are read from |
| `CHROMA_DIR` | `backend/chroma_db` | Where the vector index persists |

`backend/.env` is gitignored — never committed. Copy `backend/.env.example` and fill in your own key to run this project.

---

## 10. Running it

```bash
# Terminal 1 — embedding model server
ollama serve                                   # if not already running as a service
ollama pull nomic-embed-text                   # one-time

# Terminal 2 — backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# Terminal 3 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, click **Run Ingestion**, then ask a question once at least some documents show `done`.

---

## 11. Environment quirks hit during setup (all resolved)

1. **`chromadb`'s compiled `hnswlib` dependency** had no installable wheel for this Python/Windows combo (no C++ build tools present). Fix: pin `chroma-hnswlib==0.7.5`, which ships a prebuilt `win_amd64` wheel.
2. **Vite 8 (Rolldown bundler)** has a native-binding resolution bug on some Node/npm combinations. Fix: pinned to stable Vite 5 (`@vitejs/plugin-react@^4`), esbuild-based.
3. **A standalone system Chrome browser** can attach `--headless --print-to-pdf` invocations to an already-running session instead of launching isolated, silently producing broken output. Not relevant at runtime, but relevant if regenerating the sample PDFs — use Playwright's bundled Chromium instead.

---

## 12. Sample data

`data/data/` ships with 10 fictional Business Requirement Documents for "ShopSphere Technologies Pvt. Ltd.", an invented e-commerce platform — one BRD per module (User Registration & Login, Product Catalog, Shopping Cart, Checkout & Payment, Order Management, Inventory, Returns & Refunds, Customer Reviews, Admin Dashboard, Notification Service). Each follows a consistent 23-section structure (Executive Summary, Business/Functional/Non-Functional Requirements, User Stories, Acceptance Criteria, Business Rules, Risks, Glossary, etc.) with realistic requirement IDs (`BR-`, `FR-`, `NFR-`, `US-`, `AC-`, `RULE-`), and the documents deliberately share terminology, stakeholder names, and integrated systems across files to simulate a real enterprise knowledge base — good for exercising cross-document retrieval.

Swap in your own PDF(s) by dropping them into `data/data/` and re-running ingestion (this fully re-indexes everything currently in that folder from scratch).
