"""爬取勞動基準法與施行細則（全國法規資料庫 HTML 解析）"""
import re
import logging
from typing import Iterator
from .base_fetcher import BaseLegalFetcher, LegalChunk

logger = logging.getLogger(__name__)

LAWS = [
    {
        "name": "勞動基準法",
        "pcode": "N0030001",
        "doc_type": "statute",
    },
    {
        "name": "勞動基準法施行細則",
        "pcode": "N0030002",
        "doc_type": "enforcement_rule",
    },
]

LIST_URL = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
DETAIL_URL = "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode={pcode}&flno={no}"

# 從 .col-no a 的 href 取得純數字條號（e.g. "25" 或 "30-1"）
FLNO_RE = re.compile(r"flno=([0-9-]+)")


class StatuteFetcher(BaseLegalFetcher):
    def fetch_chunks(self) -> Iterator[LegalChunk]:
        for law in LAWS:
            logger.info("Fetching %s ...", law["name"])
            yield from self._fetch_law(law)

    def _fetch_law(self, law: dict) -> Iterator[LegalChunk]:
        url = LIST_URL.format(pcode=law["pcode"])
        try:
            soup = self._soup(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", law["name"], e)
            return

        # 每個 .row 包含 .col-no（條號）和 .col-data .law-article（內文）
        rows = soup.select("div.row")
        count = 0
        for row in rows:
            col_no = row.select_one(".col-no a")
            article_div = row.select_one(".law-article")
            if not col_no or not article_div:
                continue

            # 條號文字，e.g. "第 30 條"
            article_label = col_no.get_text(strip=True)  # "第 30 條"
            # 取 flno（用於 URL）
            href = col_no.get("href", "")
            flno_match = FLNO_RE.search(href)
            flno = flno_match.group(1) if flno_match else article_label.replace("第", "").replace("條", "").strip()

            content = article_div.get_text("\n", strip=True)
            if not content:
                continue

            chunk_id = f"{law['doc_type']}_{law['pcode']}_{flno}"
            source_url = DETAIL_URL.format(pcode=law["pcode"], no=flno)
            yield LegalChunk(
                chunk_id=chunk_id,
                doc_type=law["doc_type"],
                article_no=article_label,
                title=f"{law['name']}{article_label}",
                text=f"勞基法{article_label}：{content}",
                source_url=source_url,
                metadata={"law_name": law["name"], "pcode": law["pcode"], "flno": flno},
            )
            count += 1

        logger.info("  Parsed %d articles for %s", count, law["name"])
