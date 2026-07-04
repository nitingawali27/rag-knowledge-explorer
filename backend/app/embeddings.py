from concurrent.futures import ThreadPoolExecutor

import requests

from .config import EMBED_MODEL, OLLAMA_BASE_URL

DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
MAX_WORKERS = 4


class EmbeddingError(RuntimeError):
    pass


def _embed_one(text: str) -> list[float]:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": [text]},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]
    except requests.RequestException as exc:
        raise EmbeddingError(
            f"Could not reach Ollama at {OLLAMA_BASE_URL}. Is `ollama serve` running "
            f"and has `{EMBED_MODEL}` been pulled (`ollama pull {EMBED_MODEL}`)? {exc}"
        ) from exc


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    prefixed = [DOCUMENT_PREFIX + t for t in texts]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(_embed_one, prefixed))


def embed_query(text: str) -> list[float]:
    return _embed_one(QUERY_PREFIX + text)
