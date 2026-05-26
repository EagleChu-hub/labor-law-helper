"""載入手動匯入的判決 JSON 檔（/data/judgments/*.json）"""
import json
import logging
from pathlib import Path
from typing import Iterator
from data.crawlers.base_fetcher import LegalChunk

logger = logging.getLogger(__name__)

JUDGMENTS_DIR = Path(__file__).parent.parent / "judgments"

# 每個 JSON 檔格式：
# {
#   "case_no": "台北地院 112 年勞訴字第 1 號",
#   "court": "台灣台北地方法院",
#   "date": "2023-10-15",
#   "case_type": "勞動契約",
#   "summary": "...",
#   "key_points": ["..."],
#   "article_refs": ["30", "32"],
#   "outcome": "原告勝訴"
# }


def load_judgment_chunks() -> Iterator[LegalChunk]:
    if not JUDGMENTS_DIR.exists():
        return
    files = list(JUDGMENTS_DIR.glob("*.json"))
    logger.info("Loading %d judgment files from %s", len(files), JUDGMENTS_DIR)
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # 支援單筆或列表格式
            items = data if isinstance(data, list) else [data]
            for item in items:
                chunk = _to_chunk(item, path.stem)
                if chunk:
                    yield chunk
        except Exception as e:
            logger.warning("Failed to load %s: %s", path.name, e)


def _to_chunk(item: dict, file_stem: str) -> LegalChunk | None:
    case_no = item.get("case_no", file_stem)
    summary = item.get("summary", "")
    key_points = item.get("key_points", [])
    text = summary
    if key_points:
        text += "\n重點：\n" + "\n".join(f"• {p}" for p in key_points)
    outcome = item.get("outcome", "")
    if outcome:
        text += f"\n結果：{outcome}"
    if not text.strip():
        return None
    article_refs = item.get("article_refs", [])
    return LegalChunk(
        chunk_id=f"judgment_{case_no.replace(' ', '_')}",
        doc_type="judgment",
        article_no=", ".join(f"第 {n} 條" for n in article_refs) or "判決",
        title=f"{item.get('court', '')} {case_no}",
        text=text,
        date=item.get("date", ""),
        metadata={
            "case_no": case_no,
            "court": item.get("court", ""),
            "case_type": item.get("case_type", ""),
            "outcome": outcome,
            "article_refs": article_refs,
        },
    )
