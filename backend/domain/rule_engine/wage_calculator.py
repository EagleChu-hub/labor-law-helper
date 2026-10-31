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
| 國定假日出勤      | 實際工時 × 時薪 × 2（加倍發給） |

★ 每一項都分成兩個數字算：
  - 應給總額 G：那些時數依法該拿到的全部
  - 原本時薪 B：那些時數 × 1 倍時薪
  勞工「已經照原本時薪領過」時，少領的只有 G − B（加成的部分）；
  「完全沒領到」時，少領 G。

⛔ 2026-11 修正前一律假設「完全沒領到」，頁面卻沒有說：
   時薪工每小時其實都有領到時薪，拿 10,870 去談，真正少的只有約 4,206。
   金額講太大＝對雇主含血噴人，也會讓勞工在調解時被薪資單打臉。
"""
from .attendance_parser import ParsedAttendance


def _weekday_ot_pay(ot_minutes: int, hourly: float) -> float:
    """平日加班費（應給總額）：前 2 小時 1.34 倍、之後 1.67 倍"""
    if ot_minutes <= 0:
        return 0.0
    first2 = min(ot_minutes, 120) / 60
    after = max(0, ot_minutes - 120) / 60
    return first2 * hourly * 1.34 + after * hourly * 1.67


def _rest_day_pay(work_minutes: int, hourly: float) -> float:
    """休息日工資（應給總額）：第 24 條第 2 項「另再加給」"""
    if work_minutes <= 0:
        return 0.0
    hours = work_minutes / 60
    first2 = min(hours, 2) * hourly * 1.34
    next6 = min(max(hours - 2, 0), 6) * hourly * 1.67
    after8 = max(hours - 8, 0) * hourly * 2.67
    return first2 + next6 + after8


def _base(minutes: int, hourly: float) -> float:
    """那些時數 × 1 倍時薪"""
    return max(0, minutes) / 60 * hourly


def _gross_and_base(rule_id: str, att: ParsedAttendance, h: float) -> tuple[float, float, str]:
    """回傳 (應給總額 G, 其中原本時薪部分 B, 公式說明)。B 不適用者回 0。"""
    # ── 平日加班類 ──
    if rule_id == "daily_overtime":
        g = b = 0.0
        for d in att.days:
            if d.is_any_rest_day or d.is_national_holiday:
                continue
            if d.total_minutes > 12 * 60:
                ot = d.total_minutes - 8 * 60
                g += _weekday_ot_pay(ot, h)
                b += _base(ot, h)
        return g, b, f"超時加班 ×（前 2h ×1.34 + 後續 ×1.67）×{h}/h"

    if rule_id == "weekly_hours":
        g = b = 0.0
        for week in att.weeks:
            week_min = sum(d.total_minutes for d in week if not d.is_any_rest_day)
            if week_min > 40 * 60:
                over = week_min - 40 * 60
                g += _weekday_ot_pay(over, h)
                b += _base(over, h)
        return g, b, f"週超時 ÷ 60 ×（1.34 / 1.67）×{h}/h"

    if rule_id == "monthly_overtime":
        # ⚠️ 門檻須與 labor_rules.rule_monthly_overtime 一致：
        #    46～54h 之間是否違法取決於有無工會／勞資會議同意，規則端只給 warning，
        #    ⛔ 故金額端亦不得逕行認列少領——寧可少估，不可對雇主含血噴人。
        #    超過 54h 者，縱經同意亦逾但書上限，才計入。
        # ⛔ 2026-11 修正前這裡自己另算延長工時（欄位值 + 每日超過 8h），
        #    與規則端（只看欄位值）不一致 → 同一張卡寫「約 0 小時・合規」又算出少領金額。
        #    現在兩端都用 att.total_overtime_minutes（= 各日 extended_minutes 加總）。
        from .labor_rules import _OT_LIMIT_AGREED
        total_ot = att.total_overtime_minutes
        if total_ot > _OT_LIMIT_AGREED:
            over = total_ot - _OT_LIMIT_AGREED
            return over / 60 * h * 1.67, _base(over, h), f"超過 54h 月加班上限（32 條 2 項但書）部分 ×1.67 ×{h}/h"
        return 0.0, 0.0, ""

    if rule_id == "unpaid_overtime":
        g = b = 0.0
        for d in att.days:
            if d.is_any_rest_day or d.is_national_holiday:
                continue
            if d.total_minutes > 8 * 60:
                ot = d.total_minutes - 8 * 60
                g += _weekday_ot_pay(ot, h)
                b += _base(ot, h)
        return g, b, "超過 8 小時的時數 ×（前 2h ×1.34、之後 ×1.67）×時薪"

    # ── 假日工作 ──
    if rule_id == "sunday_work":
        g = b = 0.0
        for d in att.days:
            if d.is_mandatory_rest and d.work_minutes > 0:
                hours = d.total_minutes / 60
                g += 8 * h + min(hours, 2) * h * 1.34 + max(hours - 2, 0) * h * 1.67
                b += _base(d.total_minutes, h)
        return g, b, "例假日：加發 1 日工資（8h）+ 工時加成"

    if rule_id == "saturday_pay":
        g = b = 0.0
        for d in att.days:
            if (d.is_regular_rest or d.is_implied_rest_day) and d.total_minutes > 0:
                g += _rest_day_pay(d.total_minutes, h)
                b += _base(d.total_minutes, h)
        return g, b, "休息日：前 2h ×1.34、2-8h ×1.67、>8h ×2.67"

    if rule_id == "national_holiday":
        g = b = 0.0
        # 出勤的國定假日（含補假日）：第 39 條「工資應加倍發給」
        # ⛔ 2026-11 移除「最低 8 小時」：repo 內查無出處，且與卡片文字矛盾。
        #    依實際工時計算（寧可少估）。
        for d in att.days:
            if d.is_national_holiday:
                g += 2 * _base(d.total_minutes, h)
                b += _base(d.total_minutes, h)
        # 撞期未補休（損失 1 日國定假日休假）：與加班時數無關，兩種情況都算
        lost = 8 * h * len(att.rest_holiday_collisions)
        return g + lost, b, f"國定假日/補假日：實際工時 × 時薪 {h} 元 × 2（加倍發給）"

    # 連續工作、休息時間 — 無直接金額損失
    return 0.0, 0.0, ""


def calc_shortfall_range(
    rule_id: str,
    att: ParsedAttendance,
    hourly_regular: float,
) -> tuple[int, int, str]:
    """
    依勞工回答的「超時拿到了什麼」（att.ot_pay_status）估算少領金額。
    回傳 (金額, 最高金額, 公式說明)：
      - none       完全沒拿到       → (G, G)
      - base_only  照時薪、沒加成   → (G−B, G−B)
      - unknown    不確定           → (G−B, G)  ← 頁面顯示區間，主數字取低的
      - full       有另外領加班費   → (0, 0)    ← 不另估，請用試算機核對
    """
    if not hourly_regular or hourly_regular <= 0:
        return 0, 0, ""
    g, b, formula = _gross_and_base(rule_id, att, hourly_regular)
    if g <= 0:
        return 0, 0, ""
    pay = att.ot_pay_status
    if pay == "full":
        return 0, 0, ""
    if pay == "none":
        return round(g), round(g), formula
    low = round(g - b)
    if pay == "base_only":
        return low, low, formula + "，扣除已領的原本時薪"
    return low, round(g), formula + "；低標＝已照原本時薪領過，高標＝完全沒領到"


def calc_shortfall_for_rule(
    rule_id: str,
    att: ParsedAttendance,
    hourly_regular: float,
) -> tuple[int, str]:
    """相容舊介面：回傳 (金額, 公式說明)"""
    amt, _, formula = calc_shortfall_range(rule_id, att, hourly_regular)
    return amt, formula


def calc_total_shortfall(violations: list[dict], key: str = "estimated_shortfall_ntd") -> int:
    """
    跨違規去重後的總短少金額。
    去重邏輯：加班費類（daily/weekly/monthly/unpaid）取最大值，避免重複計算同一段超時。
    假日類（sunday/saturday/national_holiday）獨立計算。
    """
    OT_GROUP = {"daily_overtime", "weekly_hours", "monthly_overtime", "unpaid_overtime"}
    ot_max = 0
    others = 0
    for v in violations:
        amt = v.get(key, 0) or 0
        rid = v.get("rule_id", "")
        if rid in OT_GROUP:
            ot_max = max(ot_max, amt)
        else:
            others += amt
    return ot_max + others
