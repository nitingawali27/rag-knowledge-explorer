import chromadb

from .config import CHROMA_API_KEY, CHROMA_DATABASE, CHROMA_TENANT, COLLECTION_NAME

_client = None


class VectorStoreError(RuntimeError):
    pass


def _get_client():
    # Constructed lazily (not at import time): chromadb.CloudClient() validates
    # the connection eagerly, so building it at module load would crash the
    # entire API — including unrelated endpoints like /api/health — on any
    # Chroma Cloud hiccup or missing credentials.
    global _client
    if _client is None:
        try:
            _client = chromadb.CloudClient(
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                api_key=CHROMA_API_KEY,
            )
        except Exception as exc:  # noqa: BLE001 - surface as a clean, typed error
            raise VectorStoreError(f"Could not connect to Chroma Cloud: {exc}") from exc
    return _client


def get_collection():
    try:
        return _get_client().get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    except VectorStoreError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Chroma Cloud request failed: {exc}") from exc


def reset_collection():
    try:
        _get_client().delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return get_collection()


def add_chunks(chunks, embeddings):
    if not chunks:
        return
    collection = get_collection()
    try:
        collection.add(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "source": c.source,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "word_count": c.word_count,
                }
                for c in chunks
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Chroma Cloud write failed: {exc}") from exc


def query(embedding, top_k):
    collection = get_collection()
    try:
        if collection.count() == 0:
            return []
        n_results = min(top_k, collection.count())
        result = collection.query(query_embeddings=[embedding], n_results=n_results)
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Chroma Cloud query failed: {exc}") from exc

    hits = []
    for i in range(len(result["ids"][0])):
        hits.append(
            {
                "id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            }
        )
    return hits


def collection_stats():
    collection = get_collection()
    try:
        count = collection.count()
        sources = set()
        if count:
            data = collection.get(include=["metadatas"])
            sources = {m["source"] for m in data["metadatas"]}
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Chroma Cloud request failed: {exc}") from exc
    return {"chunk_count": count, "document_count": len(sources), "sources": sorted(sources)}
