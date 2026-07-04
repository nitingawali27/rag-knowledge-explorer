# Run_Command.md — RAG Explorer

Complete from-scratch steps to get this project running locally, assuming a brand-new machine with nothing installed yet.

> 📖 For architecture/diagrams, see **[Flow_Control.md](Flow_Control.md)**.

---

## 1. Install prerequisites

- **Python 3.12** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 20+** and npm — [nodejs.org](https://nodejs.org/)
- **Git**
- **Ollama** — [ollama.com/download](https://ollama.com/download) (runs the embedding model locally)

Verify:

```bash
python --version
node --version
git --version
ollama --version
```

---

## 2. Get the code

```bash
git clone https://github.com/nitingawali27/rag-knowledge-explorer.git
cd rag-knowledge-explorer
```

---

## 3. Pull the embedding model and create one free account

This backend runs fully offline except for answer generation, which uses the Groq API.

```bash
ollama pull nomic-embed-text
```

| Service | Sign up at | What you need |
|---|---|---|
| **Groq** (LLM) | [console.groq.com](https://console.groq.com) | API key |

---

## 4. Set up the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Open `backend/.env` and fill in your Groq key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

OLLAMA_BASE_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text
```

> **Windows only:** if `pip install` fails building `chroma-hnswlib` from source (needs C++ build tools), make sure `chromadb` is unpinned in `requirements.txt` — current releases don't depend on compiled `hnswlib`.

---

## 5. Set up the frontend

```bash
cd ../frontend
npm install
```

No `.env` needed for local use — it defaults to talking to `http://localhost:8000`.

---

## 6. Run it (three terminals)

**Terminal 1 — Ollama:**

```bash
ollama serve
```

(Skip if Ollama is already running as a background service, which is the default after installing on Windows/Mac.)

**Terminal 2 — backend:**

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

**Terminal 3 — frontend:**

```bash
cd frontend
npm run dev
```

---

## 7. Use it

1. Open **http://localhost:5173**
2. Click **Run Ingestion** — reads the 10 sample BRD PDFs bundled in `backend/data/data/`, chunks them, embeds each chunk via your local Ollama server, and stores vectors in a local ChromaDB folder (`backend/chroma_db/`). Watch the progress bar and per-document status fill in live. This can take a few minutes on CPU-only Ollama (~8-10s per chunk).
3. Once at least one document shows `done`, type a question or click one of the sample-question chips, then **Ask**.
4. You'll see the top-4 retrieved chunks (with similarity scores and source/page) and a Groq-generated answer citing them.

To use your own PDFs instead: drop them into `backend/data/data/` and click **Run Ingestion** again (it fully re-indexes that folder from scratch).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `chromadb` install fails building `hnswlib` (needs C++ build tools) | Remove any `chromadb==` version pin in `requirements.txt` and reinstall |
| Ingestion fails with "Could not reach Ollama" | Make sure `ollama serve` is running and `ollama pull nomic-embed-text` has completed |
| `/api/status` or `/api/query` returns `502 Could not open local Chroma store` | Check that `backend/chroma_db/` (or your custom `CHROMA_DIR`) is writable |
| Query fails with a Groq error | Check `GROQ_API_KEY` in `backend/.env` and that the account has access to `GROQ_MODEL` |
| Frontend can't reach the backend | Confirm the backend is running on port 8000 (`curl http://localhost:8000/api/health`) |
