"""規則引擎主入口：接收 CheckRequest，回傳 CheckResult"""
from schemas.check import CheckRequest, CheckResult, ViolationItem, ComputedMetrics, LawReference
from .attendance_parser import parse_attendance, ParsedAttendance
from .labor_rules import ALL_RULES, ViolationResult
from .wage_calculator import calc_shortfall_range, calc_total_shortfall


def _to_schema_violation(r: ViolationResult, att: ParsedAttendance, hourly: float) -> ViolationItem:
    shortfall, shortfall_max, formula = calc_shortfall_range(r.rule_id, att, hourly) if hourly else (0, 0, "")
    return ViolationItem(
        rule_id=r.rule_id,
        status=r.status,
        title=r.title,
        explanation=r.explanation,
        confidence=r.confidence,
        law_references=[LawReference(**ref) for ref in r.law_references],
        missing_facts=r.missing_facts,
        estimated_shortfall_ntd=shortfall,
        shortfall_formula=formula,
        estimated_shortfall_max_ntd=shortfall_max,
    )


_SHORTFALL_BASIS = {
    "none": "以「超時與休假日上班的時數完全沒拿到錢」計算。",
    "base_only": "以「超時與休假日上班的時數有照原本時薪領，只是沒有加成」計算，只算少給的加成。",
    "full": "你表示超時有另外領加班費，本站不另估金額；可用下方試算機核對有沒有給足。",
    "unknown": "你不確定那些時數拿到了什麼：低標＝已照原本時薪領過（只少了加成），高標＝完全沒領到。請對照薪資單。",
}


def _risk_level(violations: list[ViolationResult]) -> str:
    if any(v.status == "suspected_violation" for v in violations):
        return "high"
    if any(v.status == "warning" for v in violations):
        return "medium"
    return "low"


def _headline(risk: str, violation_count: int) -> str:
    if risk == "high":
        return f"發現 {violation_count} 項疑似違反勞基法的情況，建議進一步確認並保全證據"
    if risk == "medium":
        return f"發現 {violation_count} 項需注意的情況，建議向雇主確認相關安排"
    return "出勤狀況符合勞基法基本規定"


def _next_actions(risk: str, violations: list[ViolationResult]) -> list[str]:
    actions = []
    if risk in ("high", "medium"):
        actions += [
            "保留出勤打卡紀錄截圖或列印",
            "記錄加班時間與實際領取的加班費金額",
        ]
    if any(v.rule_id == "consecutive_days" for v in violations if v.status != "compliant"):
        actions.append("向雇主確認例假安排方式（書面為佳）")
    if any(v.rule_id in ("saturday_pay", "sunday_work") for v in violations if v.status != "compliant"):
        actions.append("確認假日出勤是否已獲得加倍工資或補休")
    if any(v.rule_id == "min_rest_hours" for v in violations if v.status != "compliant"):
        actions.append("記錄每日實際上下班時間，確認班次間休息是否達 11 小時")
    if any(v.rule_id == "national_holiday" for v in violations if v.status != "compliant"):
        actions.append("確認國定假日出勤已獲雙倍薪資，或例假日與國定假日重疊時已安排補休")
    if risk == "high":
        actions.append("可向勞工局申訴或撥打 1955 勞工諮詢專線")
    return actions or ["出勤狀況良好，繼續保留出勤紀錄以備不時之需"]


def evaluate(request: CheckRequest) -> CheckResult:
    att = parse_attendance(
        request.attendance_records,
        mandatory_day_off_weekday=request.mandatory_day_off_weekday,
        regular_day_off_weekday=request.regular_day_off_weekday,
        mandatory_rest_dates=request.mandatory_rest_dates,
        regular_rest_dates=request.regular_rest_dates,
        holiday_compensation_overrides=request.holiday_compensation_overrides,
        agreed_rest_day_ot_dates=request.agreed_rest_day_ot_dates,
    )
    att.ot_pay_status = request.ot_pay_status

    results: list[ViolationResult] = [rule(att) for rule in ALL_RULES]
    non_compliant = [r for r in results if r.status != "compliant"]

    risk = _risk_level(results)
    hourly = request.hourly_wage_regular or 0
    violations = [_to_schema_violation(r, att, hourly) for r in results]
    # 只統計疑似違規/警告類的短少金額，compliant 跳過
    counted = [v.model_dump() for v in violations if v.status != "compliant"]
    total_shortfall = calc_total_shortfall(counted) if hourly else 0
    total_shortfall_max = calc_total_shortfall(counted, key="estimated_shortfall_max_ntd") if hourly else 0

    return CheckResult(
        risk_level=risk,
        headline=_headline(risk, len(non_compliant)),
        disclaimer="本系統提供參考資訊，不構成法律意見。如有爭議，建議諮詢專業律師或撥打 1955 勞工諮詢專線。",
        violations=violations,
        metrics=ComputedMetrics(
            total_work_minutes=att.total_work_minutes,
            total_overtime_minutes=att.total_overtime_minutes,
            max_consecutive_days=att.max_consecutive_days,
            avg_daily_minutes=(
                att.total_work_minutes / len(att.days) if att.days else 0.0
            ),
        ),
        next_actions=_next_actions(risk, results),
        total_shortfall_ntd=total_shortfall,
        total_shortfall_max_ntd=total_shortfall_max,
        shortfall_basis=_SHORTFALL_BASIS[request.ot_pay_status] if hourly else "",
        has_wage_input=bool(hourly),
    )
