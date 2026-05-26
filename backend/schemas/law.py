from pydantic import BaseModel
from typing import Literal, Optional


class LawSearchResult(BaseModel):
    article_no: str
    title: str
    snippet: str
    doc_type: Literal["statute", "enforcement_rule", "interpretation", "judgment", "arbitration"] = "statute"
    source_url: str = ""
    relevance_score: float = 0.0


class LawArticle(BaseModel):
    article_no: str
    title: str
    full_text: str
    doc_type: str
    source_url: str = ""
    related_articles: list[str] = []


class LawSearchResponse(BaseModel):
    results: list[LawSearchResult]
    total: int
    query: str
