"""
從 jojostarking/law-rag-chatbot 下載相關法規並轉換為 LegalChunk 格式。

來源：https://raw.githubusercontent.com/jojostarking/law-rag-chatbot/main/laws_for_rag.json
格式：[{law_name, chapter, article_number, content}, ...]

引入策略：
- 排除「勞動基準法」和「勞動基準法施行細則」（我們已有來自 law.moj.gov.tw 的更完整版本）
- 引入其他相關法規：最低工資法、性別平等工作法、勞工請假規則、就業服務法、勞工退休金條例等
"""
import re
import logging
from typing import Iterator

import requests

from data.crawlers.base_fetcher import LegalChunk

logger = logging.getLogger(__name__)

SOURCE_URL = (
    "https://raw.githubusercontent.com/jojostarking/"
    "law-rag-chatbot/main/laws_for_rag.json"
)

# 已有更完整來源的法規，跳過避免重複
_SKIP_LAWS = {
    "勞動基準法",
    "勞動基準法施行細則",
}


def _slugify(s: str) -> str:
    """把字串轉為適合 chunk_id 的格式（移除空白與特殊符號）"""
    return re.sub(r"[^\w一-鿿]", "_", s).strip("_")


def fetch_related_laws() -> Iterator[LegalChunk]:
    """
    下載並轉換相關法規。
    若網路不通，記錄 warning 後安靜略過（不中斷整體 build_index 流程）。
    """
    logger.info("== 下載相關法規（law-rag-chatbot）==")
    try:
        resp = requests.get(SOURCE_URL, timeout=30)
        resp.raise_for_status()
        items: list[dict] = resp.json()
    except Exception as e:
        logger.warning("無法下載相關法規（%s），跳過。後端功能不受影響。", e)
        return

    count = 0
    skipped_laws: set[str] = set()

    for item in items:
        law_name: str = item.get("law_name", "").strip()
        article_no: str = item.get("article_number", "").strip()
        content: str = item.get("content", "").strip()
        chapter: str = item.get("chapter", "").strip()

        if not law_name or not content:
            continue

        # 排除已有完整來源的法規
        if law_name in _SKIP_LAWS:
            skipped_laws.add(law_name)
            continue

        chunk_id = f"related_{_slugify(law_name)}_{_slugify(article_no)}"
        title = f"{law_name}{article_no}"
        # 組合完整文字：法規名稱 + 條號 + 內容（供 BM25 和向量搜尋）
        text = f"{law_name}{article_no}：{content}"
        if chapter:
            text = f"【{chapter}】{text}"

        yield LegalChunk(
            chunk_id=chunk_id,
            doc_type="statute",
            article_no=article_no,
            title=title,
            text=text,
            source_url="https://github.com/jojostarking/law-rag-chatbot",
            date="",
            metadata={
                "law_name": law_name,
                "chapter": chapter,
            },
        )
        count += 1

    if skipped_laws:
        logger.info("已跳過（本地已有更完整版本）：%s", "、".join(sorted(skipped_laws)))
    logger.info("引入相關法規 %d 筆", count)
