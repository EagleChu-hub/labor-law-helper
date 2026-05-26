import json
from pathlib import Path
from fastapi import APIRouter, Query
from schemas.law import LawSearchResponse, LawSearchResult

router = APIRouter()

MOCK_PATH = Path(__file__).parent.parent / "mock_data" / "law_search.json"


def _try_hybrid_search(q: str, doc_type: str) -> list[LawSearchResult] | None:
    """嘗試用真實混合搜尋；若索引尚未建立則回傳 None（降級到 mock）"""
    try:
        from domain.retriever.hybrid_retriever import hybrid_search
        results = hybrid_search(q, top_k=8, doc_type_filter=doc_type if doc_type != "all" else None)
        return [
            LawSearchResult(
                article_no=r["article_no"],
                title=r["title"],
                snippet=r["text"][:300],
                doc_type=r.get("doc_type", "statute"),
                source_url=r.get("source_url", ""),
                relevance_score=round(r.get("rrf_score", 0.0), 4),
            )
            for r in results
        ]
    except Exception:
        return None


@router.get("/search", response_model=LawSearchResponse)
def search(
    q: str = Query(..., description="搜尋關鍵字"),
    doc_type: str = Query("all", description="all|statute|enforcement_rule|interpretation|judgment|arbitration"),
):
    results = _try_hybrid_search(q, doc_type)
    if results is not None:
        return LawSearchResponse(results=results, total=len(results), query=q)

    # 降級：回傳 mock 資料
    with open(MOCK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data["query"] = q
    return data
