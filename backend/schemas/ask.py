from pydantic import BaseModel
from typing import Literal, Optional


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class LawReference(BaseModel):
    article_no: str
    title: str
    snippet: str
    doc_type: Literal["statute", "enforcement_rule", "interpretation", "judgment", "arbitration"] = "statute"
    source_url: str = ""


class AskResponse(BaseModel):
    # 新版主要欄位：Gemini 直接吐 Markdown，前端用 react-markdown 渲染
    markdown: str = ""
    headline: str = ""
    law_references: list[LawReference] = []
    followup_questions: list[str] = []
    # 以下為向後相容，新版不再填入
    summary: str = ""
    reasoning: str = ""
    missing_facts: list[str] = []
    suggestions: list[str] = []
