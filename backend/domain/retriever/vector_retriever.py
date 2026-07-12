"""向量搜尋：使用 BAAI/bge-small-zh-v1.5 + ChromaDB"""
import os
import logging
from functools import lru_cache

import chromadb

logger = logging.getLogger(__name__)

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "labor_law"
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"


@lru_cache(maxsize=1)
def _get_embed_model():
    # 延遲 import：sentence-transformers 會連帶載入 torch，記憶體成本不小。
    # 只有確定 ChromaDB collection 存在（本地開發環境）才會呼叫到這裡；
    # 雲端（Render，無 chroma_db）完全不會 import 到 torch。
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model %s ...", EMBED_MODEL)
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(COLLECTION_NAME)


def vector_search(query: str, top_k: int = 10) -> list[dict]:
    """回傳含 rank 的結果列表，rank 從 1 開始（分越低越好）"""
    try:
        collection = _get_collection()
    except Exception as e:
        # 雲端（Render）沒有 chroma_db（.gitignore 排除），此為預期中的 fallback。
        # 故意排在 _get_embed_model() 之前檢查：collection 不存在時直接短路，
        # 避免白白把 torch + sentence-transformers 整組載入記憶體（曾在 512MB 免費方案上導致 OOM 崩潰迴圈）。
        logger.info("Vector search unavailable (no ChromaDB collection), falling back to BM25 only: %s", e)
        return []
    try:
        model = _get_embed_model()
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
