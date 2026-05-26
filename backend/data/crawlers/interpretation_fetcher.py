"""爬取勞動部函釋（laws.mol.gov.tw），僅抓 2015 年後"""
import re
import logging
from typing import Iterator
from .base_fetcher import BaseLegalFetcher, LegalChunk

logger = logging.getLogger(__name__)

LIST_URL = "https://laws.mol.gov.tw/FLAW/FLAWQRY01.aspx"
DETAIL_BASE = "https://laws.mol.gov.tw/FLAW/"

# 用於從函釋內文解析引用法條（如「第30條」「第32條第1項」）
ARTICLE_RE = re.compile(r"第\s*(\d+)\s*條")


class InterpretationFetcher(BaseLegalFetcher):
    def __init__(self, start_year: int = 2015, max_pages: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.start_year = start_year
        self.max_pages = max_pages

    def fetch_chunks(self) -> Iterator[LegalChunk]:
        logger.info("Fetching interpretations from %d ...", self.start_year)
        count = 0
        for page in range(1, self.max_pages + 1):
            items = self._fetch_list_page(page)
            if not items:
                break
            for item in items:
                chunk = self._fetch_detail(item)
                if chunk:
                    count += 1
                    yield chunk
        logger.info("Fetched %d interpretations total", count)

    def _fetch_list_page(self, page: int) -> list[dict]:
        try:
            params = {
                "RealCategory": "N0030001",  # 勞基法法規代碼
                "PageNum": str(page),
                "MinYear": str(self.start_year),
            }
            soup = self._soup(LIST_URL, params=params)
            rows = soup.select("table.listTable tr")
            items = []
            for row in rows[1:]:  # 跳過 header
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                link = cells[0].find("a")
                if not link:
                    continue
                items.append({
                    "href": link.get("href", ""),
                    "doc_no": cells[0].get_text(strip=True),
                    "date": cells[1].get_text(strip=True),
                    "subject": cells[2].get_text(strip=True),
                })
            return items
        except Exception as e:
            logger.warning("Failed to fetch page %d: %s", page, e)
            return []

    def _fetch_detail(self, item: dict) -> LegalChunk | None:
        if not item["href"]:
            return None
        url = DETAIL_BASE + item["href"]
        try:
            soup = self._soup(url)
            content_div = soup.find("div", id="content") or soup.find("div", class_="content")
            text = content_div.get_text("\n", strip=True) if content_div else ""
            if not text:
                return None
            article_refs = list(set(ARTICLE_RE.findall(text)))
            chunk_id = f"interpretation_{item['doc_no'].replace('/', '_')}"
            return LegalChunk(
                chunk_id=chunk_id,
                doc_type="interpretation",
                article_no=", ".join(f"第 {n} 條" for n in article_refs) or "函釋",
                title=item["subject"],
                text=text[:2000],  # 截斷過長函釋
                source_url=url,
                date=item["date"],
                metadata={
                    "doc_no": item["doc_no"],
                    "article_refs": article_refs,
                },
            )
        except Exception as e:
            logger.warning("Failed to fetch interpretation %s: %s", item["doc_no"], e)
            return None
