"""載入手動匯入的仲裁 JSON 檔（/data/arbitrations/*.json）"""
import json
import logging
from pathlib import Path
from typing import Iterator
from data.crawlers.base_fetcher import LegalChunk

logger = logging.getLogger(__name__)

ARBITRATIONS_DIR = Path(__file__).parent.parent / "arbitrations"

# 每個 JSON 格式：
# {
#   "decision_no": "勞裁 112 第 1 號",
#   "date": "2023-08-01",
#   "issuer": "勞動部",
#   "summary": "...",
#   "issue_type": "加班費爭議",
#   "article_refs": ["24"],
#   "outcome": "雇主應補發加班費"
# }


def load_arbitration_chunks() -> Iterator[LegalChunk]:
    if not ARBITRATIONS_DIR.exists():
        return
    files = list(ARBITRATIONS_DIR.glob("*.json"))
    logger.info("Loading %d arbitration files from %s", len(files), ARBITRATIONS_DIR)
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                chunk = _to_chunk(item, path.stem)
                if chunk:
                    yield chunk
        except Exception as e:
            logger.warning("Failed to load %s: %s", path.name, e)


def _to_chunk(item: dict, file_stem: str) -> LegalChunk | None:
    decision_no = item.get("decision_no", file_stem)
    summary = item.get("summary", "")
    outcome = item.get("outcome", "")
    text = summary
    if outcome:
        text += f"\n仲裁結果：{outcome}"
    if not text.strip():
        return None
    article_refs = item.get("article_refs", [])
    return LegalChunk(
        chunk_id=f"arbitration_{decision_no.replace(' ', '_')}",
        doc_type="arbitration",
        article_no=", ".join(f"第 {n} 條" for n in article_refs) or "仲裁決定",
        title=f"{item.get('issue_type', '勞資爭議')} — {decision_no}",
        text=text,
        date=item.get("date", ""),
        metadata={
            "decision_no": decision_no,
            "issuer": item.get("issuer", ""),
            "issue_type": item.get("issue_type", ""),
            "outcome": outcome,
            "article_refs": article_refs,
        },
    )
