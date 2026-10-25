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
        "alias": "勞基法",
    },
    {
        "name": "勞動基準法施行細則",
        "pcode": "N0030002",
        "doc_type": "enforcement_rule",
        "alias": "勞基法施行細則",
    },
    # 2026-07-01 職場霸凌防治新制（PR11）
    {
        "name": "職業安全衛生法",
        "pcode": "N0060001",
        "doc_type": "statute",
        "alias": "職安法",
    },
    {
        "name": "職場霸凌防治措施準則",
        "pcode": "N0060085",
        "doc_type": "enforcement_rule",
        "alias": "職場霸凌防治措施準則",
    },
    {
        "name": "地方主管機關受理最高負責人職場霸凌事件申訴處理辦法",
        "pcode": "N0060086",
        "doc_type": "enforcement_rule",
        "alias": "地方主管機關受理最高負責人職場霸凌事件申訴處理辦法",
    },
    # PR20：勞動事件法。
    # ⛔ 不在 GitHub 靜態語料集裡（那份只收勞動部主管法規），所以必須自己爬。
    # ★ 補這部法解決三件事：
    #   ① `/triage` 有 7 筆勞動事件法引文，先前語料庫查不到，報表只能標 SKIP
    #      （SKIP 不等於通過，每次都得人工以 MCP 覆核）
    #   ② 勞工問「調解不成立怎麼辦」「要不要先經法院調解」時，RAG 原本撈不到條文
    #   ③ 十日不變期間（29 條）這種最貴的陷阱，先前只能靠前端硬寫
    # ⚠️ pcode 開頭是 B（司法院主管），與其他 N 開頭的勞動法規不同，不要誤植。
    {
        "name": "勞動事件法",
        "pcode": "B0010064",
        "doc_type": "statute",
        "alias": "勞動事件法",
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
                text=f"{law.get('alias', law['name'])}{article_label}：{content}",
                source_url=source_url,
                metadata={"law_name": law["name"], "pcode": law["pcode"], "flno": flno},
            )
            count += 1

        logger.info("  Parsed %d articles for %s", count, law["name"])
