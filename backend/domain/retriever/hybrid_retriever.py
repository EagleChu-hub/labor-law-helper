"""RRF 混合搜尋：BM25 + Vector → Reciprocal Rank Fusion"""
import logging
from .vector_retriever import vector_search
from .bm25_retriever import bm25_search

logger = logging.getLogger(__name__)

RRF_K = 60  # RRF 平滑常數

# 勞基法常見俗稱 → 法律用語對照
_SYNONYMS: dict[str, str] = {
    "年假": "特別休假",
    "年休": "特別休假",
    "加班": "延長工時",
    "例假": "例假 休息日",
    "資遣費": "資遣 勞工退休",
    "退休金": "勞工退休金",
    "病假": "普通傷病假",
}


def _expand_query(query: str) -> str:
    for k, v in _SYNONYMS.items():
        if k in query:
            return f"{query} {v}"
    return query


def _rrf_score(rank: int, k: int = RRF_K) -> float:
    return 1.0 / (k + rank)


def hybrid_search(
    query: str,
    top_k: int = 8,
    doc_type_filter: str | None = None,
) -> list[dict]:
    """
    BM25 + 向量各取 top_k 結果，RRF 融合後回傳最終 top_k 筆。
    doc_type_filter: "all" 或 None 表示不過濾，否則限定 doc_type。
    """
    expanded = _expand_query(query)
    vec_results = vector_search(expanded, top_k=top_k * 2)
    bm25_results = bm25_search(expanded, top_k=top_k * 2)

    # 用 chunk_id 為 key，累計 RRF 分數，並保留原始 doc 資料
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for r in vec_results:
        cid = r["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + _rrf_score(r["rank"])
        docs[cid] = r

    for r in bm25_results:
        cid = r["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + _rrf_score(r["rank"])
        if cid not in docs:
            docs[cid] = r

    # 排序
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for chunk_id, rrf in ranked:
        doc = docs[chunk_id]
        if doc_type_filter and doc_type_filter != "all" and doc.get("doc_type") != doc_type_filter:
            continue
        results.append({**doc, "rrf_score": rrf})
        if len(results) >= top_k:
            break

    return results
