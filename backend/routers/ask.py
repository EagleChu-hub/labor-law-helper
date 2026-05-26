import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.ask import AskRequest, AskResponse

router = APIRouter()

MOCK_PATH = Path(__file__).parent.parent / "mock_data" / "ask_response.json"


def _try_rag(request: AskRequest) -> dict | None:
    """嘗試用真實 RAG；若 API key 未設定或發生錯誤則回傳 None（降級 mock）"""
    try:
        from domain.rag.answer_generator import generate_answer
        return generate_answer(
            question=request.message,
            history=[m.model_dump() for m in request.history],
        )
    except Exception:
        return None


@router.post("/chat", response_model=AskResponse)
def chat(request: AskRequest):
    result = _try_rag(request)
    if result is not None:
        # 新版主要欄位
        result.setdefault("markdown", "")
        result.setdefault("headline", "")
        result.setdefault("law_references", [])
        result.setdefault("followup_questions", [])
        # 向後相容
        result.setdefault("summary", "")
        result.setdefault("reasoning", "")
        result.setdefault("missing_facts", [])
        result.setdefault("suggestions", [])
        return result

    # 降級：mock 資料
    with open(MOCK_PATH, encoding="utf-8") as f:
        return json.load(f)
