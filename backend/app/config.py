import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env", override=True)

DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data" / "data"))
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", BACKEND_DIR / "chroma_db"))
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION", "rag_explorer_docs")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

CHUNK_SIZE_WORDS = int(os.environ.get("CHUNK_SIZE_WORDS", 150))
CHUNK_OVERLAP_WORDS = int(os.environ.get("CHUNK_OVERLAP_WORDS", 30))
TOP_K = int(os.environ.get("TOP_K", 4))
