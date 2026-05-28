"""
即時從 tlr.dr-lawbot.com 抓取台灣法院判決，作為補充 context 注入 RAG。
每次查詢最多 2 筆，5 秒 timeout，失敗靜默回空 list，不影響現有功能。
"""
import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

TLR_BASE = "https://tlr.dr-lawbot.com"
_ARTICLE_RE = re.compile(r"勞動基準法§(\d+)")


def fetch_judgments(query: str, top_k: int = 2) -> list[dict]:
    """查詢時即時抓取相關判決，失敗靜默回空。"""
    try:
        payload = json.dumps({"query": query[:500], "max_results": top_k},
                             ensure_ascii=False).encode("utf-8")
        r = requests.post(
            f"{TLR_BASE}/v1/search",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10.0,
        )
        r.raise_for_status()
        items = r.json().get("results", [])
        results = [_to_chunk(item) for item in items[:top_k]]
        logger.info("tlr: fetched %d judgments for query=%r", len(results), query[:30])
        return results
    except Exception as e:
        logger.warning("tlr fetch failed (query=%r): %s", query[:30], e)
        return []


def _to_chunk(item: dict) -> dict:
    snippet = item.get("snippet", "")
    article_nos = _ARTICLE_RE.findall(snippet)
    article_no_str = "、".join(f"第 {n} 條" for n in dict.fromkeys(article_nos)) if article_nos else ""

    # snippet 格式：「〔案件名稱〕 | 判決結果: X | 引用: ... | 類型: ...」
    # 取第二行以後（去掉前兩行的引用連結/引用字號）
    lines = [l.strip() for l in snippet.splitlines() if l.strip()]
    summary_lines = [l for l in lines if not l.startswith("引用連結") and not l.startswith("引用字號")]
    summary = " ".join(summary_lines)[:400]

    return {
        "rank": item.get("rank", 0),
        "chunk_id": f"tlr_{item.get('doc_id', '')}",
        "doc_type": "judgment",
        "article_no": article_no_str,
        "title": item.get("citation_text", ""),
        "text": summary,
        "source_url": item.get("citation_url", ""),
        "date": item.get("jdate", ""),
        "is_external": True,
    }
