"""
勞基法違規判斷規則（共 9 條）。
每條規則接收 ParsedAttendance，回傳 ViolationResult。
"""
from dataclasses import dataclass
from typing import Callable
from .attendance_parser import ParsedAttendance, DayWork

_WEEKDAY_ZH = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]


@dataclass
class ViolationResult:
    rule_id: str
    status: str           # "suspected_violation" | "warning" | "compliant"
    title: str
    explanation: str
    confidence: str       # "high" | "medium" | "low"
    law_references: list[dict]
    missing_facts: list[str]


def _ref(article_no: str, title: str, snippet: str) -> dict:
    no = article_no.replace("第 ", "").replace(" 條", "")
    return {
        "article_no": f"第 {no} 條",
        "title": title,
        "snippet": snippet,
        "source_url": f"https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno={no}",
    }


def _ref_rule(article_no: str, title: str, snippet: str) -> dict:
    """施行細則條文引用"""
    no = str(article_no).replace("第 ", "").replace(" 條", "")
    return {
        "article_no": f"施行細則第 {no} 條",
        "title": title,
        "snippet": snippet,
        "source_url": f"https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030002&flno={no}",
    }


# ⚠️ 32 條 2 項有「但書」：經工會（無工會者經勞資會議）同意後，
#    月上限放寬為 54 小時、每三個月 138 小時（30 人以上者並應報主管機關備查）。
#    ⛔ 2026-08 修正前本規則直接把 >46h 判為疑似違規，
#       對已依但書取得同意之事業單位會產生「假陽性」——
#       告訴勞工「你老闆違法」而其實未必。故改為三段式判斷。
_OT_LIMIT_BASE = 46 * 60      # 32 條 2 項本文
_OT_LIMIT_AGREED = 54 * 60    # 32 條 2 項但書（經工會／勞資會議同意）

# 引用原文一律抄完整（含但書），不得只抄前半句
_OT_SNIPPET = (
    "前項雇主延長勞工之工作時間連同正常工作時間，一日不得超過十二小時；"
    "延長之工作時間，一個月不得超過四十六小時，但雇主經工會同意，"
    "如事業單位無工會者，經勞資會議同意後，延長之工作時間，"
    "一個月不得超過五十四小時，每三個月不得超過一百三十八小時。"
)
_OT_ASK_AGREED = "雇主是否已經工會或勞資會議同意（30 人以上並報主管機關備查）？若有，月上限為 54 小時。"
_OT_ASK_QUARTER = "每三個月合計是否超過 138 小時？（需三個月完整資料才能判斷）"
# 以下兩段逐字抄自語料庫（2026-11），含但書，不得改寫
_ART24_2 = (
    "雇主使勞工於第三十六條所定休息日工作，工作時間在二小時以內者，"
    "其工資按平日每小時工資額另再加給一又三分之一以上；"
    "工作二小時後再繼續工作者，按平日每小時工資額另再加給一又三分之二以上。"
)
_ART40_1 = (
    "因天災、事變或突發事件，雇主認有繼續工作之必要時，得停止第三十六條至第三十八條所定勞工之假期。"
    "但停止假期之工資，應加倍發給，並應於事後補假休息。"
)


# ──────────────────────────────────────────────
# 規則 1：單日工時 > 12 小時 → 第 32 條
# ──────────────────────────────────────────────
def rule_daily_hours(att: ParsedAttendance) -> ViolationResult:
    LIMIT = 12 * 60
    violations = [d for d in att.days if d.total_minutes > LIMIT]
    if not violations:
        return ViolationResult(
            rule_id="daily_overtime",
            status="compliant",
            title="單日工時",
            explanation="單日工時未超過 12 小時上限。",
            confidence="high",
            law_references=[_ref("32", "延長工時限制（32 條 2 項）", _OT_SNIPPET)],
            missing_facts=[],
        )
    worst = max(violations, key=lambda d: d.total_minutes)
    hrs = worst.total_minutes / 60
    return ViolationResult(
        rule_id="daily_overtime",
        status="suspected_violation",
        title="單日工時超過 12 小時",
        explanation=(
            f"{worst.date.strftime('%m/%d')} 工時達 {hrs:.1f} 小時，超過勞基法第 32 條第 2 項"
            "「延長勞工之工作時間連同正常工作時間，一日不得超過十二小時」之上限。"
        ),
        confidence="high" if len(violations) > 1 else "medium",
        law_references=[_ref("32", "延長工時限制（32 條 2 項）", _OT_SNIPPET)],
        missing_facts=["是否屬緊急事故或特殊行業（如醫療、運輸）？", "是否有工會或勞資會議書面同意？"],
    )


# ──────────────────────────────────────────────
# 規則 2：單週工時 > 40 小時 → 第 30 條
# ──────────────────────────────────────────────
def rule_weekly_hours(att: ParsedAttendance) -> ViolationResult:
    LIMIT = 40 * 60
    over_weeks = []
    for week in att.weeks:
        total = sum(d.total_minutes for d in week)  # 含打卡外加班
        if total > LIMIT:
            over_weeks.append(total)
    if not over_weeks:
        return ViolationResult(
            rule_id="weekly_hours",
            status="compliant",
            title="單週正常工時",
            explanation="各週正常工時均未超過 40 小時。",
            confidence="high",
            law_references=[_ref("30", "正常工時", "勞工正常工作時間，每日不得超過八小時，每週不得超過四十小時。")],
            missing_facts=[],
        )
    worst_hrs = max(over_weeks) / 60
    return ViolationResult(
        rule_id="weekly_hours",
        status="suspected_violation",
        title="單週工時超過 40 小時",
        explanation=f"最高週工時達 {worst_hrs:.1f} 小時，超過勞基法第 30 條規定的每週 40 小時上限。",
        confidence="high" if len(att.weeks) >= 2 else "medium",
        law_references=[_ref("30", "正常工時", "勞工正常工作時間，每日不得超過八小時，每週不得超過四十小時。")],
        missing_facts=["是否有採用彈性工時制度（每 8 週平均不超過 40 小時）？"],
    )


# ──────────────────────────────────────────────
# 規則 3：連續工作 > 6 天 → 第 36 條
# ──────────────────────────────────────────────
def rule_consecutive_days(att: ParsedAttendance) -> ViolationResult:
    if att.max_consecutive_days <= 6:
        return ViolationResult(
            rule_id="consecutive_days",
            status="compliant",
            title="連續工作天數",
            explanation="連續工作未超過 6 天，符合勞基法第 36 條規定。",
            confidence="high",
            law_references=[_ref("36", "例假規定", "勞工每七日中應有二日之休息，其中一日為例假，一日為休息日。")],
            missing_facts=[],
        )
    return ViolationResult(
        rule_id="consecutive_days",
        status="suspected_violation",
        title=f"連續工作 {att.max_consecutive_days} 天",
        explanation=f"出勤紀錄中有連續 {att.max_consecutive_days} 天工作的情況，超過勞基法第 36 條「每 7 日至少 2 日休息（1 天例假、1 天休息日）」的規定。",
        confidence="high",
        law_references=[_ref("36", "例假規定", "勞工每七日中應有二日之休息，其中一日為例假，一日為休息日。")],
        missing_facts=["是否已安排補休？", "是否有天災、事變等緊急情況？"],
    )


# ──────────────────────────────────────────────
# 規則 4：例假日出勤（依設定之例假日，非固定週日）→ 第 36、40 條
# ──────────────────────────────────────────────
def rule_sunday_work(att: ParsedAttendance) -> ViolationResult:
    mandatory_days = [d for d in att.days if d.is_mandatory_rest]
    if not mandatory_days and att.max_consecutive_days >= 7:
        # ⛔ 2026-11 修正前：連上 12 天的人，這裡回「合規・可信度高」，
        #    就排在「連續工作 12 天・疑似違規」旁邊。
        #    連上 7 天以上代表其中必有應休的例假被拿來上班，只是無從判斷是哪一天。
        return ViolationResult(
            rule_id="sunday_work",
            status="warning",
            title="例假日出勤（無法判斷是哪一天）",
            explanation=(
                f"你連續上班 {att.max_consecutive_days} 天，期間至少有一天原本應該是例假，"
                "但系統無法判斷是哪一天，所以這一項不估金額（見「連續工作」那一項）。"
                "依勞基法第 40 條，例假只有天災、事變或突發事件才能停止，"
                "停止時工資應加倍發給，並應於事後補假休息。"
            ),
            confidence="medium",
            law_references=[
                _ref("36", "例假規定", "勞工每七日中應有二日之休息，其中一日為例假，一日為休息日。"),
                _ref("40", "例假出勤補償", _ART40_1),
            ],
            missing_facts=["公司排定的例假是哪一天？", "是否屬天災、事變等緊急情況？", "加倍工資與補假是否已給？"],
        )
    if not mandatory_days:
        # 判斷設定的例假日是哪天
        sample = next(iter(att.days), None)
        day_label = "例假日"
        return ViolationResult(
            rule_id="sunday_work",
            status="compliant",
            title="例假日出勤",
            explanation=f"無例假日（{day_label}）出勤紀錄。",
            confidence="high",
            law_references=[_ref("36", "例假規定", "其中一日為例假。")],
            missing_facts=[],
        )
    # 找出設定的例假日是星期幾（取第一筆的 weekday）
    day_label = _WEEKDAY_ZH[mandatory_days[0].date.weekday()]
    dates = [d.date.strftime(f"%m/%d（{day_label}）") for d in mandatory_days]
    return ViolationResult(
        rule_id="sunday_work",
        status="suspected_violation",
        title=f"例假日出勤（共 {len(mandatory_days)} 天）",
        explanation=(
            f"在例假日（{day_label}）出勤：{', '.join(dates)}。"
            f"依勞基法第 40 條，除天災事變外，例假日不得出勤；"
            f"若已出勤，應補給例假並加倍給付工資。"
        ),
        confidence="high",
        law_references=[
            _ref("36", "例假規定", "勞工每七日中應有二日之休息，其中一日為例假。"),
            _ref("40", "例假出勤補償", "因天災、事變或突發事件停止假期，工資應加倍發給，並應於事後補假休息。"),
        ],
        missing_facts=["是否屬天災、事變等緊急情況？", "雇主是否有補假安排？", "加倍工資是否已給付？"],
    )


# ──────────────────────────────────────────────
# 規則 5：休息日出勤未加成計薪（依設定之休息日，非固定週六）→ 第 24 條
# ──────────────────────────────────────────────
_REST_DAY_36_1 = "勞工每七日中應有二日之休息，其中一日為例假，一日為休息日。"
_REST_DAY_ASK_FLEX = "公司是否依法採用變形工時（須經工會或勞資會議同意，且限指定行業）？若有，可以兩週合計休 4 天，不一定每週都要休 2 天。"


def _implied_rest_day_result(att: ParsedAttendance) -> ViolationResult:
    """一週上班 ≥ 6 天：其中 1 天依法是休息日（推定），提醒而不逕判違規"""
    implied = att.implied_rest_days
    eg = "、".join(d.date.strftime("%m/%d") for d in implied[:4])
    more = "等" if len(implied) > 4 else ""
    return ViolationResult(
        rule_id="saturday_pay",
        status="warning",
        title=f"一週上班 6 天以上（{len(implied)} 次）：其中 1 天依法是休息日",
        explanation=(
            f"你的出勤中有 {len(implied)} 個「7 天內上班 6 天以上」的區間。"
            f"依勞基法第 36 條第 1 項「{_REST_DAY_36_1.rstrip('。')}」，"
            "所以這 6 天裡有 1 天其實是休息日——那一天的工資要依第 24 條第 2 項的休息日倍率計算。"
            "（確定是休息日之後，當天工時還要算進每月加班上限〔第 36 條第 3 項〕；"
            "在確認之前，本站的月加班先不算進去。）"
            f"是哪一天由公司排定，系統先用每段工時最短的一天估算（{eg}{more}），金額只會少算、不會多算。"
            "⚠️ 若公司依法採用變形工時，可以兩週合計休 4 天，就不一定違法——請先確認。"
        ),
        confidence="medium",
        law_references=[
            _ref("36", "例假與休息日", _REST_DAY_36_1),
            _ref("24", "休息日工資（24 條 2 項）", _ART24_2),
        ],
        missing_facts=[_REST_DAY_ASK_FLEX, "公司排定的休息日是哪一天？那天有沒有照休息日倍率給薪？"],
    )


def rule_saturday_pay(att: ParsedAttendance) -> ViolationResult:
    regular_days = [d for d in att.days if d.is_regular_rest and d.work_minutes > 0]
    if not regular_days and att.implied_rest_days:
        # ⛔ 2026-11 修正前：時薪工一週上 6 天，這裡回「無休息日出勤紀錄・合規・可信度高」。
        #    前端只會把「沒上班的日子」標成休息日，上 6 天時休息日永遠找不到。
        return _implied_rest_day_result(att)
    result = _explicit_rest_day_result(att, regular_days)
    if att.implied_rest_days and regular_days:
        extra = _implied_rest_day_result(att)
        result.explanation += " 另外：" + extra.explanation
        result.missing_facts = result.missing_facts + [_REST_DAY_ASK_FLEX]
        result.law_references = result.law_references + extra.law_references[:1]
    return result


def _explicit_rest_day_result(att: ParsedAttendance, regular_days: list[DayWork]) -> ViolationResult:
    if not regular_days:
        return ViolationResult(
            rule_id="saturday_pay",
            status="compliant",
            title="休息日出勤",
            explanation="無休息日出勤紀錄。",
            confidence="high",
            law_references=[_ref("24", "加班費計算", "休息日工作，工資加給......")],
            missing_facts=[],
        )

    # 區分「已約定」與「未約定」
    agreed_days = [d for d in regular_days if d.is_agreed_rest_day_ot]
    unagreed_days = [d for d in regular_days if not d.is_agreed_rest_day_ot]

    refs = [
        _ref("24", "加班費計算", "休息日工作，前2小時每小時給付平日每小時工資1又1/3，超過2小時後每小時給付1又2/3。"),
    ]

    # 全部都已標記為約定加班 → 正面框架（合法、應領加班費）
    if agreed_days and not unagreed_days:
        dates_str = "、".join(d.date.strftime("%m/%d") for d in agreed_days)
        return ViolationResult(
            rule_id="saturday_pay",
            status="warning",  # 仍標 warning 以保留在違規列表（讓 AI 提及），但措辭正面
            title=f"✓ 約定休息日加班（共 {len(agreed_days)} 天，應領加班費）",
            explanation=(
                f"你已標記以下日期為與雇主約定的合法休息日加班：{dates_str}。"
                f"依勞基法第 24 條，雇主應給付：前 2 小時 1.34 倍時薪、2-8 小時 1.67 倍、超過 8 小時 2.67 倍。"
                f"請確認雇主是否依此倍率給付加班費。"
            ),
            confidence="high",
            law_references=refs,
            missing_facts=["加班費是否已依倍率給付？", "是否以補休代替加班費（需勞工書面同意）？"],
        )

    # 部分或全部未約定 → 偏警示
    parts = []
    if unagreed_days:
        dates_str = "、".join(d.date.strftime("%m/%d") for d in unagreed_days)
        parts.append(
            f"有 {len(unagreed_days)} 天系統判定為休息日但你未標記為「約定加班」：{dates_str}。"
            f"若雇主未事先取得你同意便要求出勤，可能違反勞基法第 36 條；"
            f"即使你同意，亦應依第 24 條給付加班費（前 2h ×1.34、2-8h ×1.67、>8h ×2.67）。"
        )
    if agreed_days:
        dates_str = "、".join(d.date.strftime("%m/%d") for d in agreed_days)
        parts.append(
            f"另有 {len(agreed_days)} 天已標記為約定加班（{dates_str}），應依加班費倍率給付。"
        )

    return ViolationResult(
        rule_id="saturday_pay",
        status="warning",
        title=f"休息日出勤（共 {len(regular_days)} 天）",
        explanation=" ".join(parts),
        confidence="medium",
        law_references=refs,
        missing_facts=["休息日加班費是否已依倍率給付？", "是否以補休代替加班費（需勞工書面同意）？"],
    )


# ──────────────────────────────────────────────
# 規則 6：月延長工時 > 46 小時 → 第 32 條第 2 項
# ──────────────────────────────────────────────
def rule_monthly_overtime(att: ParsedAttendance) -> ViolationResult:
    total_ot = att.total_overtime_minutes
    days_count = len(att.days)
    if days_count < 20:
        projected = int(total_ot * (30 / max(days_count, 1)))
        conf = "low"
    else:
        projected = total_ot
        conf = "high"
    hrs = projected // 60
    ref = [_ref("32", "月延長工時上限（含但書）", _OT_SNIPPET)]
    partial = ["需完整一個月資料才能精確判斷"] if days_count < 20 else []
    # 依打卡時間推算，不再只看「加班（分）」欄位（見 DayWork.extended_minutes）
    basis = "（依打卡時間推算：平日超過 8 小時的部分＋休息日工時）"

    # ① 未達 46 小時：合規
    if projected <= _OT_LIMIT_BASE:
        return ViolationResult(
            rule_id="monthly_overtime",
            status="compliant",
            title="月加班時數",
            explanation=(
                f"依現有資料（{days_count} 天）推估月加班時數約 {hrs} 小時{basis}，"
                "未超過勞基法第 32 條第 2 項本文之 46 小時上限。"
            ),
            confidence=conf,
            law_references=ref,
            missing_facts=partial,
        )

    # ② 46～54 小時之間：⚠️ 只有「未取得同意」才違法 → 不逕判違規，改為提醒
    if projected <= _OT_LIMIT_AGREED:
        return ViolationResult(
            rule_id="monthly_overtime",
            status="warning",
            title=f"月加班時數約 {hrs} 小時，已超過 46 小時（是否違法取決於有無工會／勞資會議同意）",
            explanation=(
                f"依出勤紀錄推估月加班時數約 {hrs} 小時{basis}，已超過勞基法第 32 條第 2 項"
                "本文之 46 小時上限。惟同項但書規定，雇主經工會同意（無工會者經勞資會議同意）後，"
                "月上限為 54 小時、每三個月 138 小時；僱用 30 人以上者並應報當地主管機關備查。"
                "因此本項是否違法，取決於雇主有無取得該同意並依規定報備——建議先向雇主或工會確認。"
            ),
            confidence=conf,
            law_references=ref,
            missing_facts=partial + [_OT_ASK_AGREED, _OT_ASK_QUARTER],
        )

    # ③ 超過 54 小時：縱經同意亦逾但書上限
    return ViolationResult(
        rule_id="monthly_overtime",
        status="suspected_violation",
        title=f"月加班時數超過 54 小時（約 {hrs} 小時）",
        explanation=(
            f"依出勤紀錄推估月加班時數約 {hrs} 小時{basis}，"
            "縱使雇主已經工會或勞資會議同意，仍超過勞基法第 32 條第 2 項但書之 54 小時上限。"
            "（未取得該同意者，本文上限為 46 小時，超過更多。）"
        ),
        confidence=conf,
        law_references=ref,
        missing_facts=partial + [
            "是否屬天災、事變或突發事件（第 32 條第 4 項，該情形不受前項上限限制）？",
            _OT_ASK_QUARTER,
        ],
    )


# ──────────────────────────────────────────────
# 規則 7：疑似無薪加班 → 第 22、24 條
# ──────────────────────────────────────────────
def _ot_days(att: ParsedAttendance) -> list[DayWork]:
    """平日（非例假／休息日／推定休息日／國定假日）工時超過 8 小時的日子"""
    return [
        d for d in att.days
        if not d.is_any_rest_day and not d.is_national_holiday and d.total_minutes > 8 * 60
    ]


def rule_unpaid_overtime(att: ParsedAttendance) -> ViolationResult:
    # ⛔ 2026-11 修正前：以「加班（分）欄位 == 0」當作「沒記錄加班」的證據。
    #    但同一欄位在別處又被當成「打卡外另外加的時數」——語意互相矛盾，
    #    而且幾乎沒人知道那欄要填什麼。改為直接問勞工「超時的錢拿到了什麼」。
    suspects = _ot_days(att)
    refs = [
        _ref("22", "工資全額給付", "工資應全額直接給付勞工。"),
        _ref("24", "加班費計算", "延長工作時間，其延長之工時依規定加給工資。"),
    ]
    if not suspects:
        return ViolationResult(
            rule_id="unpaid_overtime",
            status="compliant",
            title="平日加班費",
            explanation="平日沒有超過 8 小時的出勤。",
            confidence="medium",
            law_references=[_ref("22", "工資給付", "工資應全額直接給付勞工。")],
            missing_facts=[],
        )
    n = len(suspects)
    pay = att.ot_pay_status
    if pay == "full":
        return ViolationResult(
            rule_id="unpaid_overtime",
            status="compliant",
            title=f"平日加班（{n} 天）：你表示有另外領加班費",
            explanation=(
                f"有 {n} 天工時超過 8 小時。你表示這些時數有另外領到加班費，"
                "可用下方試算機核對倍率是否足額（前 2 小時至少 1.34 倍、再 2 小時至少 1.67 倍）。"
            ),
            confidence="medium",
            law_references=refs,
            missing_facts=["加班費是否依倍率給足？"],
        )
    if pay in ("none", "base_only"):
        what = "完全沒拿到錢" if pay == "none" else "只照原本時薪算、沒有加成"
        return ViolationResult(
            rule_id="unpaid_overtime",
            status="suspected_violation",
            title=f"平日加班沒給足（{n} 天）",
            explanation=(
                f"有 {n} 天工時超過 8 小時，你表示超時的部分{what}。"
                "依勞基法第 24 條，延長工時的工資應依倍率加給；依第 22 條，工資應全額直接給付。"
            ),
            confidence="medium",
            law_references=refs,
            missing_facts=["公司是否有「責任制」約定？（大部分行業不適用）"],
        )
    return ViolationResult(
        rule_id="unpaid_overtime",
        status="warning",
        title=f"工時超過 8 小時（{n} 天）：請確認有沒有領到加班費",
        explanation=(
            f"有 {n} 天工時超過 8 小時，超過的部分是加班。"
            "依勞基法第 24 條，延長工時的工資應依倍率加給。請對照薪資單，確認這些時數有沒有領到錢、有沒有加成。"
        ),
        confidence="medium",
        law_references=refs,
        missing_facts=["超時工作是否有對應加班費？", "公司是否有「責任制」約定？（大部分行業不適用）"],
    )


# ──────────────────────────────────────────────
# 規則 8：兩班次間休息不足 11 小時（輪班制）→ 勞基法第 34 條第 2 項
# ──────────────────────────────────────────────
# ⛔ 2026-08 修正：原本引用「施行細則第 34 條」——**引錯法規**。
#    該規定在**勞動基準法第 34 條第 2 項**，施行細則並無此條，
#    產生給使用者的 source_url 會指向錯誤的法規。
# ⚠️ 同時該項亦有但書：經中央目的事業主管機關商請中央主管機關公告者，
#    得變更休息時間為**不少於連續八小時**（並須經工會／勞資會議同意，
#    30 人以上並應報備）。故與 32 條同理，改為三段式，不逕判違規。
_REST_LIMIT_BASE = 11 * 60    # 34 條 2 項本文
_REST_LIMIT_MIN = 8 * 60      # 34 條 2 項但書之下限

_REST_SNIPPET = (
    "依前項更換班次時，至少應有連續十一小時之休息時間。"
    "但因工作特性或特殊原因，經中央目的事業主管機關商請中央主管機關公告者，"
    "得變更休息時間不少於連續八小時。"
)
_REST_ASK = [
    "是否屬輪班制勞工？（非輪班制不適用本條）",
    "雇主所屬行業是否經中央主管機關公告得縮短為連續八小時？若有，並須經工會或勞資會議同意（30 人以上應報備）。",
]


def rule_min_rest_hours(att: ParsedAttendance) -> ViolationResult:
    ref = [_ref("34", "輪班換班休息時間（34 條 2 項，含但書）", _REST_SNIPPET)]
    shortfalls = [
        d for d in att.days
        if d.rest_minutes_before > 0 and d.rest_minutes_before < _REST_LIMIT_BASE
    ]
    if not shortfalls:
        return ViolationResult(
            rule_id="min_rest_hours",
            status="compliant",
            title="班次間休息時間",
            explanation="連續工作日間的休息時間均達 11 小時以上。",
            confidence="medium",
            law_references=ref,
            missing_facts=[],
        )
    worst = min(shortfalls, key=lambda d: d.rest_minutes_before)
    rest_hrs = worst.rest_minutes_before / 60
    dates_str = ", ".join(d.date.strftime("%m/%d") for d in shortfalls)
    below_min = [d for d in shortfalls if d.rest_minutes_before < _REST_LIMIT_MIN]

    # ① 8～11 小時：可能落在但書範圍 → 提醒，不逕判違規
    if not below_min:
        return ViolationResult(
            rule_id="min_rest_hours",
            status="warning",
            title=f"班次間休息不足 11 小時（{len(shortfalls)} 次，最短 {rest_hrs:.1f} 小時）",
            explanation=(
                f"以下日期上班前休息時間不足 11 小時：{dates_str}。"
                "依勞動基準法第 34 條第 2 項本文，輪班制勞工更換班次時應有連續 11 小時休息；"
                "惟同項但書規定，經中央目的事業主管機關商請中央主管機關公告之行業，"
                "得縮短為不少於連續 8 小時（並須經工會或勞資會議同意）。"
                "因所餘時間仍達 8 小時以上，是否違法取決於雇主是否屬該公告行業並已取得同意。"
            ),
            confidence="medium",
            law_references=ref,
            missing_facts=_REST_ASK,
        )

    # ② 低於 8 小時：縱依但書亦不足
    return ViolationResult(
        rule_id="min_rest_hours",
        status="suspected_violation",
        title=f"班次間休息不足 8 小時（{len(below_min)} 次，最短 {rest_hrs:.1f} 小時）",
        explanation=(
            f"以下日期上班前休息時間不足 11 小時：{dates_str}，最短僅 {rest_hrs:.1f} 小時。"
            "縱使雇主屬經公告得適用但書之行業，仍低於勞動基準法第 34 條第 2 項但書"
            "所定「不少於連續八小時」之下限。"
        ),
        confidence="high" if len(below_min) > 1 else "medium",
        law_references=ref,
        missing_facts=_REST_ASK[:1],
    )


# ──────────────────────────────────────────────
# 規則 9：國定假日出勤未給雙倍薪 → 第 37、39 條
# ──────────────────────────────────────────────
def rule_national_holiday(att: ParsedAttendance) -> ViolationResult:
    # 找出例假日（is_mandatory_rest）與國定假日重疊 → 應有補假
    mandatory_on_holiday = [
        d for d in att.days
        if d.is_mandatory_rest and d.is_national_holiday
    ]
    # 找出非假日但有工作且為國定假日 → 應給雙倍薪
    worked_on_holiday = [
        d for d in att.days
        if d.is_national_holiday and not d.is_mandatory_rest
    ]
    # 未出勤但例假/休息日撞國定假日（從掃描期間內偵測到的）→ 應協商擇日補假
    off_day_collisions = att.rest_holiday_collisions

    if not mandatory_on_holiday and not worked_on_holiday and not off_day_collisions:
        return ViolationResult(
            rule_id="national_holiday",
            status="compliant",
            title="國定假日",
            explanation="出勤紀錄中無國定假日出勤或例假日與國定假日重疊的情況。",
            confidence="medium",
            law_references=[_ref("37", "國定假日", "內政部所定應放假之紀念日、節日、勞動節及其他中央主管機關指定應放假日，均應休假。")],
            missing_facts=[],
        )

    issues = []
    refs = [_ref("37", "國定假日休假", "內政部所定應放假之紀念日、節日、勞動節及其他中央主管機關指定應放假日，均應休假。")]

    if worked_on_holiday:
        detail_parts = []
        for d in worked_on_holiday:
            name = d.national_holiday_name
            date_str = d.date.strftime("%m/%d")
            if "補假" in name:
                # 補假日：明確說明法律性質，避免勞工誤以為補假日不算國定假日
                detail_parts.append(
                    f"{date_str}（{name}——國定假日因遇週末挪移，法律性質等同原節日）"
                )
            else:
                detail_parts.append(f"{date_str}（{name}）")
        names = "、".join(detail_parts)
        # ⛔ 2026-11 修正前：這裡寫「每小時均以雙倍計算」，金額卻以「最低 8 小時」計，
        #    4 小時的班被多算一倍。「最低 8 小時」在 repo 內找不到任何出處 → 依鐵則不採。
        issues.append(
            f"在國定假日出勤：{names}。"
            f"依勞基法第 39 條，雇主經徵得勞工同意於休假日工作者，工資應加倍發給；"
            f"補假日的法律性質等同原國定假日。本站以你實際工作的時數估算（保守算法）。"
        )
        refs.append(_ref("39", "假日工資加倍", "勞工於休假日工作，工資應加倍發給。"))

    if mandatory_on_holiday:
        names = "、".join(
            f"{d.date.strftime('%m/%d')}（{d.national_holiday_name}）"
            for d in mandatory_on_holiday
        )
        issues.append(
            f"例假日與國定假日重疊（且當日有出勤）：{names}。"
            f"依函釋，雇主應另定其他工作日補休國定假日，不得以例假日抵充；"
            f"當日出勤亦應依勞基法第 39 條加倍給付工資。"
        )

    # 未出勤的例假/休息日撞國定假日：提醒應協商補假
    if off_day_collisions:
        items = []
        for c in off_day_collisions:
            rest_label = "例假日" if c.rest_type == "mandatory" else "休息日"
            items.append(f"{c.date.strftime('%m/%d')}（{c.holiday_name}，原本就是你的{rest_label}）")
        issues.append(
            f"以下日期你原本就放假，但同時也是國定假日：{', '.join(items)}。"
            f"依勞動部函釋，國定假日不得以例假日／休息日抵充，"
            f"雇主應與你協商擇日補假（補假當日仍應給薪）。"
            f"如雇主未安排補假，等同少給你一天國定假日的休假權益。"
        )
        refs.append(_ref("39", "假日工資加倍", "勞工於休假日工作，工資應加倍發給。"))

    # 國定假日上班本身合法（經勞工同意即可），違法的是「沒加倍」。
    # ⛔ 2026-11 修正前不問有沒有加倍就標「疑似違規・可信度高」，
    #    卻又把「是否已獲得加倍工資？」列在尚需確認——自相矛盾。
    pay_known_short = att.ot_pay_status in ("none", "base_only")
    has_violation = bool(mandatory_on_holiday or (worked_on_holiday and pay_known_short))
    status = "suspected_violation" if has_violation else "warning"
    # 標題依情境調整，讓使用者快速辨識
    if worked_on_holiday and pay_known_short:
        title = "國定假日出勤未加倍給薪"
    elif worked_on_holiday:
        title = f"國定假日出勤（共 {len(worked_on_holiday)} 天）：請確認有沒有加倍給薪"
    elif mandatory_on_holiday:
        title = "例假日與國定假日重疊（仍出勤）"
    else:
        title = f"例假/休息日與國定假日重疊（共 {len(off_day_collisions)} 天，應補假）"

    return ViolationResult(
        rule_id="national_holiday",
        status=status,
        title=title,
        explanation=" ".join(issues),
        confidence="high" if has_violation else "medium",
        law_references=refs,
        missing_facts=[
            "國定假日出勤是否已獲得加倍工資？",
            "例假日與國定假日重疊時，雇主是否已安排補休國定假日？",
        ],
    )


# 所有規則清單（依此順序執行）
ALL_RULES: list[Callable[[ParsedAttendance], ViolationResult]] = [
    rule_daily_hours,
    rule_weekly_hours,
    rule_consecutive_days,
    rule_sunday_work,
    rule_saturday_pay,
    rule_monthly_overtime,
    rule_unpaid_overtime,
    rule_min_rest_hours,
    rule_national_holiday,
]
