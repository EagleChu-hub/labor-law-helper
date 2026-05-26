"""仿 LamaIndexRAG 的 BaseLegalFetcher 模式：rate limit + retry + 統一資料模型"""
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class LegalChunk:
    """一個可索引的法律文字片段"""
    chunk_id: str          # 唯一識別（e.g. "statute_30_1"）
    doc_type: str          # statute / enforcement_rule / interpretation / judgment / arbitration
    article_no: str        # 條號，e.g. "第 30 條"
    title: str             # 標題
    text: str              # 內文
    source_url: str = ""
    date: str = ""
    metadata: dict = field(default_factory=dict)


class BaseLegalFetcher(ABC):
    def __init__(self, delay: float = 1.0, retries: int = 3):
        self.delay = delay
        self.retries = retries
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (compatible; LaborLawBot/1.0; +educational)"
        )

    def _get(self, url: str, **kwargs) -> requests.Response:
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, timeout=15, **kwargs)
                resp.raise_for_status()
                time.sleep(self.delay)
                return resp
            except requests.RequestException as e:
                if attempt == self.retries - 1:
                    raise
                wait = self.delay * (2 ** attempt)
                logger.warning("Retry %d for %s after %.1fs: %s", attempt + 1, url, wait, e)
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch {url}")

    def _soup(self, url: str, **kwargs) -> BeautifulSoup:
        resp = self._get(url, **kwargs)
        # 強制 UTF-8 解碼（全國法規資料庫以 UTF-8 提供內容，但 requests 偶爾偵測錯誤）
        text = resp.content.decode("utf-8", errors="replace")
        return BeautifulSoup(text, "html.parser")

    @abstractmethod
    def fetch_chunks(self) -> Iterator[LegalChunk]:
        """Yield LegalChunk objects"""
