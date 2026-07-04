import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env", override=True)

# DATA_DIR defaults to backend/data/data so the backend is self-contained when
# deployed as its own Vercel project (Vercel only bundles files under the
# project's configured root directory).
DATA_DIR = Path(os.environ.get("DATA_DIR", BACKEND_DIR / "data" / "data"))
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION", "rag_explorer_docs")

# Chroma Cloud (https://trychroma.com/cloud) — replaces the local
# PersistentClient used in the desktop/local-Ollama version of this app.
CHROMA_API_KEY = os.environ.get("CHROMA_API_KEY", "")
CHROMA_TENANT = os.environ.get("CHROMA_TENANT", "")
CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", "")

# Nomic's hosted Atlas Embedding API — replaces the local Ollama
# nomic-embed-text server used in the desktop/local version of this app.
NOMIC_API_KEY = os.environ.get("NOMIC_API_KEY", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text-v1.5")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

CHUNK_SIZE_WORDS = int(os.environ.get("CHUNK_SIZE_WORDS", 150))
CHUNK_OVERLAP_WORDS = int(os.environ.get("CHUNK_OVERLAP_WORDS", 30))
TOP_K = int(os.environ.get("TOP_K", 4))
INGEST_STEP_BATCH_SIZE = int(os.environ.get("INGEST_STEP_BATCH_SIZE", 20))
