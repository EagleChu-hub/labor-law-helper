"""BM25 關鍵字搜尋：Jieba 中文斷詞 + rank-bm25"""
import json
import logging
import warnings
from functools import lru_cache
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

# 壓制 jieba pkg_resources 警告
warnings.filterwarnings("ignore", category=UserWarning, module="jieba")

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "raw_chunks_cache.json"


def _tokenize(text: str) -> list[str]:
    return [t for t in jieba.cut(text) if t.strip()]


@lru_cache(maxsize=1)
def _get_bm25_index() -> tuple[BM25Okapi, list[dict]]:
    if not CACHE_PATH.exists():
        logger.warning("BM25 cache not found at %s — run build_index.py first", CACHE_PATH)
        return None, []
    with open(CACHE_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    corpus = [_tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(corpus)
    logger.info("BM25 index built with %d docs", len(chunks))
    return bm25, chunks


def bm25_search(query: str, top_k: int = 10) -> list[dict]:
    """回傳含 rank 的結果列表"""
    bm25, chunks = _get_bm25_index()
    if bm25 is None:
        return []
    tokens = _tokenize(query)
    scores = bm25.get_scores(tokens)
    # 取 top_k
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    output = []
    for rank, (idx, score) in enumerate(ranked, 1):
        c = chunks[idx]
        output.append({
            "rank": rank,
            "chunk_id": c["chunk_id"],
            "doc_type": c.get("doc_type", "statute"),
            "article_no": c.get("article_no", ""),
            "title": c.get("title", ""),
            "text": c["text"],
            "source_url": c.get("source_url", ""),
            "date": c.get("date", ""),
            "score": float(score),
        })
    return output
