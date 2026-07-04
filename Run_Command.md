# Run_Command.md — RAG Explorer

Complete from-scratch steps to get this project running locally, assuming a brand-new machine with nothing installed yet.

> ☁️ To deploy this instead of running it locally, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.
> 📖 For architecture/diagrams, see **[Flow_Control.md](Flow_Control.md)**.

---

## 1. Install prerequisites

- **Python 3.12** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 20+** and npm — [nodejs.org](https://nodejs.org/)
- **Git**

Verify:

```bash
python --version
node --version
git --version
```

---

## 2. Get the code

```bash
git clone https://github.com/nitingawali27/rag-knowledge-explorer.git
cd rag-knowledge-explorer
```

---

## 3. Create three free cloud accounts

This backend has **no local-only mode** — it uses hosted services for embeddings and vector storage instead of a local model server and local disk, so it deploys the same way to Vercel. All three of the following are required just to run it locally too.

| Service | Sign up at | What you need |
|---|---|---|
| **Groq** (LLM) | [console.groq.com](https://console.groq.com) | API key |
| **Nomic Atlas** (embeddings) | [atlas.nomic.ai](https://atlas.nomic.ai) | API key (1M free tokens included) |
| **Chroma Cloud** (vector store) | [trychroma.com/cloud](https://www.trychroma.com/cloud) | API key + create a database → note its tenant ID and database name |

---

## 4. Set up the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Open `backend/.env` and fill in the four required keys from step 3:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

NOMIC_API_KEY=your_nomic_api_key_here
EMBED_MODEL=nomic-embed-text-v1.5

CHROMA_API_KEY=your_chroma_cloud_api_key_here
CHROMA_TENANT=your_chroma_tenant_id
CHROMA_DATABASE=your_chroma_database_name
```

> **Windows only:** if `pip install` fails on `chromadb`/`hnswlib` (no prebuilt wheel for your Python version), run:
> ```bash
> pip install chroma-hnswlib==0.7.5
> ```

---

## 5. Set up the frontend

```bash
cd ../frontend
npm install
```

No `.env` needed for local use — it defaults to talking to `http://localhost:8000`.

---

## 6. Run it (two terminals)

**Terminal 1 — backend:**

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

---

## 7. Use it

1. Open **http://localhost:5173**
2. Click **Run Ingestion** — reads the 10 sample BRD PDFs bundled in `backend/data/data/`, chunks them, embeds each chunk via Nomic, and stores vectors in your Chroma Cloud database. Watch the progress bar and per-document status fill in live.
3. Once at least one document shows `done`, type a question or click one of the sample-question chips, then **Ask**.
4. You'll see the top-4 retrieved chunks (with similarity scores and source/page) and a Groq-generated answer citing them.

To use your own PDFs instead: drop them into `backend/data/data/` and click **Run Ingestion** again (it fully re-indexes that folder from scratch).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: hnswlib` or chromadb install fails | `pip install chroma-hnswlib==0.7.5` |
| `/api/status` or `/api/query` returns `502 Could not connect to Chroma Cloud` | Check `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` in `backend/.env` and that the database exists in the Chroma Cloud dashboard |
| Ingestion fails with a Nomic error | Check `NOMIC_API_KEY` in `backend/.env` and remaining token quota |
| Query fails with a Groq error | Check `GROQ_API_KEY` in `backend/.env` and that the account has access to `GROQ_MODEL` |
| Frontend can't reach the backend | Confirm the backend is running on port 8000 (`curl http://localhost:8000/api/health`) |
