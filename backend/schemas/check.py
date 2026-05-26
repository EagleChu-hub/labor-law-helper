from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date


class AttendanceRecord(BaseModel):
    date: str  # YYYY-MM-DD
    clock_in: str  # HH:mm
    clock_out: str  # HH:mm
    break_minutes: int = 60
    overtime_minutes: int = 0


class LeaveRecord(BaseModel):
    date: str
    leave_type: Literal["annual", "sick", "personal", "unpaid", "other"]
    hours: float


class SalaryInfo(BaseModel):
    base_salary: float
    hourly_rate: Optional[float] = None
    has_overtime_pay: bool = True


class CheckRequest(BaseModel):
    employment_type: Literal["monthly_salary", "hourly", "dispatch"]
    schedule_type: Literal["fixed", "shift", "rotating"] = "fixed"
    attendance_records: list[AttendanceRecord]
    leave_records: list[LeaveRecord] = []
    salary_info: Optional[SalaryInfo] = None
    # 0=週一 … 6=週日；預設週日為例假日、週六為休息日（月薪制 / 固定排班 fallback）
    mandatory_day_off_weekday: int = 6
    regular_day_off_weekday: int = 5
    # 逐日標註的例假/休息日（時薪制 / 變形工時用，優先於 weekday 設定）
    # 由前端用 7 天滾動視窗算出
    mandatory_rest_dates: list[str] = []
    regular_rest_dates: list[str] = []
    # 使用者明確標記「與雇主約定的休息日加班」：應領加班費、非違規
    agreed_rest_day_ot_dates: list[str] = []
    # 國定假日補休調整：{ 原節日日期: 補休日期 }
    # 例：{"2026-05-01": "2026-05-02"} = 把 5/1 勞動節挪到 5/2 補休
    holiday_compensation_overrides: dict[str, str] = {}
    # 時薪資訊（選填）：用於試算可能短少的加班費／假日工資
    hourly_wage_regular: Optional[float] = None  # 平日時薪
    hourly_wage_holiday: Optional[float] = None  # 假日時薪（留空則用平日 × 法定倍率）


class LawReference(BaseModel):
    article_no: str
    title: str
    snippet: str
    source_url: str = ""


class ViolationItem(BaseModel):
    rule_id: str
    status: Literal["compliant", "warning", "suspected_violation"]
    title: str
    explanation: str
    confidence: Literal["high", "medium", "low"]
    law_references: list[LawReference]
    missing_facts: list[str] = []
    # 試算可能短少金額（新台幣元）。未填時薪則為 0。
    estimated_shortfall_ntd: int = 0
    shortfall_formula: str = ""  # 公式說明，方便使用者理解


class ComputedMetrics(BaseModel):
    total_work_minutes: int
    total_overtime_minutes: int
    max_consecutive_days: int
    avg_daily_minutes: float


class CheckResult(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    headline: str
    disclaimer: str
    violations: list[ViolationItem]
    metrics: ComputedMetrics
    next_actions: list[str]
    # 試算總短少金額（已去重，避免加班費類項目互相加總）
    total_shortfall_ntd: int = 0
    # 是否有提供時薪（決定前端顯示金額 or 「請輸入時薪」）
    has_wage_input: bool = False
