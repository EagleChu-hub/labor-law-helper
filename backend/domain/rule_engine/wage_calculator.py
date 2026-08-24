"""
加班費 / 假日工資試算（勞基法第 24、39 條倍率）。

倍率表（在原時薪基礎上）：
| 情境 | 倍率 |
|------|------|
| 平日延長前 2 小時 | 1.34 倍 |
| 平日延長 2 小時後 | 1.67 倍 |
| 休息日前 2 小時    | 1.34 倍 |
| 休息日 2-8 小時    | 1.67 倍 |
| 休息日 8 小時後    | 2.67 倍 |
| 例假日出勤        | 加發 1 日工資（8h × 時薪）+ 視同加班再加成 |
| 國定假日出勤      | 加發 1 日工資（8h × 時薪） |

注意：本計算為「應給金額」的估算，假設雇主完全未給付加班費／假日工資。
若雇主已給付部分，實際短少金額 = 本估算 - 已給付。
"""
from .attendance_parser import ParsedAttendance


def _weekday_ot_pay(ot_minutes: int, hourly: float) -> float:
    """平日加班費：前 2 小時 1.34 倍、之後 1.67 倍"""
    if ot_minutes <= 0:
        return 0.0
    first2 = min(ot_minutes, 120) / 60
    after = max(0, ot_minutes - 120) / 60
    return first2 * hourly * 1.34 + after * hourly * 1.67


def _rest_day_pay(work_minutes: int, hourly: float) -> float:
    """休息日工資（含 8 小時內最低保障）"""
    if work_minutes <= 0:
        return 0.0
    hours = work_minutes / 60
    first2 = min(hours, 2) * hourly * 1.34
    next6 = min(max(hours - 2, 0), 6) * hourly * 1.67
    after8 = max(hours - 8, 0) * hourly * 2.67
    return first2 + next6 + after8


def calc_shortfall_for_rule(
    rule_id: str,
    att: ParsedAttendance,
    hourly_regular: float,
) -> tuple[int, str]:
    """
    根據違規類型，估算可能短少的金額（NT$）+ 公式說明。
    回傳 (金額, 公式說明)。
    """
    if not hourly_regular or hourly_regular <= 0:
        return 0, ""
    h = hourly_regular

    # ── 平日加班類 ──
    if rule_id == "daily_overtime":
        total = 0.0
        days_with_ot = []
        for d in att.days:
            if d.is_mandatory_rest or d.is_regular_rest or d.is_national_holiday:
                continue
            ot = max(0, d.total_minutes - 8 * 60)
            if d.total_minutes > 12 * 60:
                pay = _weekday_ot_pay(ot, h)
                total += pay
                days_with_ot.append(d.date.strftime("%m/%d"))
        if total > 0:
            return round(total), f"超時加班 ×（前 2h ×1.34 + 後續 ×1.67）×{h}/h"
        return 0, ""

    if rule_id == "weekly_hours":
        total = 0.0
        for week in att.weeks:
            week_min = sum(d.work_minutes for d in week if not (d.is_mandatory_rest or d.is_regular_rest))
            if week_min > 40 * 60:
                over = week_min - 40 * 60
                total += _weekday_ot_pay(over, h)
        if total > 0:
            return round(total), f"週超時 ÷ 60 ×（1.34 / 1.67）×{h}/h"
        return 0, ""

    if rule_id == "monthly_overtime":
        # 推估：總加班分鐘 ÷ 60 × 1.67（保守按高倍率）
        # ⚠️ 門檻須與 labor_rules.rule_monthly_overtime 一致（2026-08 同步修正）：
        #    32 條 2 項本文 46h，但書（經工會／勞資會議同意）為 54h。
        #    46～54h 之間是否違法取決於有無該同意，規則端只給 warning，
        #    ⛔ 故金額端亦不得逕行認列少領——寧可少估，不可對雇主含血噴人。
        #    超過 54h 者，縱經同意亦逾但書上限，才計入。
        from .labor_rules import _OT_LIMIT_AGREED
        total_ot = att.total_overtime_minutes
        for d in att.days:
            extra = max(0, d.work_minutes - 8 * 60)
            total_ot += extra
        if total_ot > _OT_LIMIT_AGREED:
            over = total_ot - _OT_LIMIT_AGREED
            return round(over / 60 * h * 1.67), f"超過 54h 月加班上限（32 條 2 項但書）部分 ×1.67 ×{h}/h"
        return 0, ""

    if rule_id == "unpaid_overtime":
        total = 0.0
        for d in att.days:
            if d.is_mandatory_rest or d.is_regular_rest or d.is_national_holiday:
                continue
            if d.work_minutes > 8 * 60 and d.overtime_minutes == 0:
                ot = d.work_minutes - 8 * 60
                total += _weekday_ot_pay(ot, h)
        if total > 0:
            return round(total), "未記錄加班時數 ×（1.34/1.67）×時薪"
        return 0, ""

    # ── 假日工作 ──
    if rule_id == "sunday_work":
        total = 0.0
        for d in att.days:
            if d.is_mandatory_rest and d.work_minutes > 0:
                daily_wage = 8 * h
                hours = d.work_minutes / 60
                first2 = min(hours, 2) * h * 1.34
                after = max(hours - 2, 0) * h * 1.67
                total += daily_wage + first2 + after
        if total > 0:
            return round(total), "例假日：加發 1 日工資（8h）+ 工時加成"
        return 0, ""

    if rule_id == "saturday_pay":
        total = 0.0
        for d in att.days:
            if d.is_regular_rest and d.work_minutes > 0:
                total += _rest_day_pay(d.work_minutes, h)
        if total > 0:
            return round(total), "休息日：前 2h ×1.34、2-8h ×1.67、>8h ×2.67"
        return 0, ""

    if rule_id == "national_holiday":
        total = 0.0
        # 出勤的國定假日（含補假日）：加倍工資
        # 法源：勞基法第 39 條「工資應加倍發給」
        # 公式：補發 = max(實際工時, 8h) × 時薪
        #   - 勞工已領正常工資，故補發部分為「再加一倍」
        #   - 最低保障 8h（即使工時不足 8h，仍應補發不低於 1 日工資）
        #   - 補假日法律性質等同原國定假日，適用相同計算方式
        for d in att.days:
            if d.is_national_holiday:
                actual_hours = d.work_minutes / 60
                extra_pay = max(actual_hours, 8.0) * h
                total += extra_pay
        # 撞期未補休（損失 1 日國定假日休假）
        for c in att.rest_holiday_collisions:
            total += 8 * h
        if total > 0:
            return round(total), f"國定假日/補假日：實際工時（最低 8h）× 時薪 {h} 元補發"
        return 0, ""

    # 連續工作、休息時間 — 無直接金額損失，回 0
    return 0, ""


def calc_total_shortfall(violations: list[dict]) -> int:
    """
    跨違規去重後的總短少金額。
    去重邏輯：加班費類（daily/weekly/monthly/unpaid）取最大值，避免重複計算同一段超時。
    假日類（sunday/saturday/national_holiday）獨立計算。
    """
    OT_GROUP = {"daily_overtime", "weekly_hours", "monthly_overtime", "unpaid_overtime"}
    ot_max = 0
    others = 0
    for v in violations:
        amt = v.get("estimated_shortfall_ntd", 0) or 0
        rid = v.get("rule_id", "")
        if rid in OT_GROUP:
            ot_max = max(ot_max, amt)
        else:
            others += amt
    return ot_max + others
