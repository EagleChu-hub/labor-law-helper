from fastapi import APIRouter
from schemas.check import CheckRequest, CheckResult
from domain.rule_engine.evaluator import evaluate

router = APIRouter()


@router.post("/analyze", response_model=CheckResult)
def analyze(request: CheckRequest):
    return evaluate(request)
