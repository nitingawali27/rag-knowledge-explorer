import nomic
from nomic import embed

from .config import EMBED_MODEL, NOMIC_API_KEY

_logged_in = False


class EmbeddingError(RuntimeError):
    pass


def _ensure_login():
    global _logged_in
    if _logged_in:
        return
    if not NOMIC_API_KEY:
        raise EmbeddingError("NOMIC_API_KEY is not set.")
    nomic.login(NOMIC_API_KEY)
    _logged_in = True


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []
    _ensure_login()
    try:
        output = embed.text(texts=texts, model=EMBED_MODEL, task_type=task_type)
    except Exception as exc:  # noqa: BLE001 - surface any Nomic API failure clearly
        raise EmbeddingError(f"Nomic embedding request failed: {exc}") from exc
    return output["embeddings"]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(texts, task_type="search_document")


def embed_query(text: str) -> list[float]:
    return _embed([text], task_type="search_query")[0]
