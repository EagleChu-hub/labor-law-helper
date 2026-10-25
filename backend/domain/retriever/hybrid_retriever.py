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
    # 職場霸凌口語 → 職安法 22-1 法定用詞（冒犯、威脅、冷落、孤立、侮辱）
    # 雲端只有 BM25（無向量搜尋），勞工口語與法條用詞不同字時查不到，必須靠此擴充
    "霸凌": "職場霸凌",
    "排擠": "職場霸凌 孤立 冷落",
    "孤立": "職場霸凌 冷落",
    "冷凍": "職場霸凌 冷落 孤立",
    "羞辱": "職場霸凌 侮辱",
    "辱罵": "職場霸凌 侮辱",
    "欺負": "職場霸凌 侮辱 冒犯",
    "穿小鞋": "職場霸凌 冷落",
    "精神暴力": "職場霸凌",
    "言語暴力": "職場霸凌 侮辱",
    "罵我": "職場霸凌 侮辱",
    # ── 訴訟程序口語 → 勞動事件法用詞（PR20，語料庫納入勞動事件法後才有意義）──
    # ⛔ 不加這組的話，新進的 53 條條文形同沒進來：勞工不會說「起訴」「出勤紀錄」，
    #    他說「告公司」「打卡紀錄」，BM25 逐字比對完全打不中。
    # ⚠️ 「公司」二字會把 533 條的公司法拉進來當噪音，所以是整詞（告公司）對應，
    #    不是拆字對應。
    "告公司": "起訴 訴訟 勞動事件 勞動調解",
    "告老闆": "起訴 訴訟 勞動事件 勞動調解",
    "提告": "起訴 訴訟 勞動事件",
    "打官司": "起訴 訴訟 勞動事件",
    "上法院": "起訴 訴訟 勞動調解",
    "法院調解": "勞動調解",
    "調解不成立": "調解不成立 續行訴訟 起訴",
    "打卡紀錄": "出勤紀錄",
    "打卡": "出勤紀錄",
    "出勤表": "出勤紀錄",
    "裁判費": "裁判費 暫免徵收",
    "訴訟費": "裁判費 暫免徵收",
}


def _expand_query(query: str) -> str:
    """累加所有命中的同義詞（去重保序），而非只取第一個。"""
    extras: list[str] = []
    for k, v in _SYNONYMS.items():
        if k in query:
            extras.extend(v.split())
    if not extras:
        return query
    deduped = " ".join(dict.fromkeys(extras))
    return f"{query} {deduped}"


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
