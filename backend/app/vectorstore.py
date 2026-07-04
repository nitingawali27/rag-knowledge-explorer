import chromadb

from .config import CHROMA_DIR, COLLECTION_NAME

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection():
    return _client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def reset_collection():
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return get_collection()


def add_chunks(chunks, embeddings):
    if not chunks:
        return
    collection = get_collection()
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


def query(embedding, top_k):
    collection = get_collection()
    if collection.count() == 0:
        return []
    n_results = min(top_k, collection.count())
    result = collection.query(query_embeddings=[embedding], n_results=n_results)
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
    count = collection.count()
    sources = set()
    if count:
        data = collection.get(include=["metadatas"])
        sources = {m["source"] for m in data["metadatas"]}
    return {"chunk_count": count, "document_count": len(sources), "sources": sorted(sources)}
