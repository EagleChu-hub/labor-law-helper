"""向量搜尋：使用 BAAI/bge-small-zh-v1.5 + ChromaDB"""
import os
import logging
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "labor_law"
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"


@lru_cache(maxsize=1)
def _get_embed_model() -> SentenceTransformer:
    logger.info("Loading embedding model %s ...", EMBED_MODEL)
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(COLLECTION_NAME)


def vector_search(query: str, top_k: int = 10) -> list[dict]:
    """回傳含 rank 的結果列表，rank 從 1 開始（分越低越好）"""
    try:
        model = _get_embed_model()
        collection = _get_collection()
        embedding = model.encode([query], normalize_embeddings=True).tolist()[0]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for i, (doc, meta, dist) in enumerate(
            zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
        ):
            output.append({
                "rank": i + 1,
                "chunk_id": results["ids"][0][i],
                "doc_type": meta.get("doc_type", "statute"),
                "article_no": meta.get("article_no", ""),
                "title": meta.get("title", ""),
                "text": doc,
                "source_url": meta.get("source_url", ""),
                "date": meta.get("date", ""),
                "score": 1.0 - float(dist),  # cosine similarity
            })
        return output
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        return []
