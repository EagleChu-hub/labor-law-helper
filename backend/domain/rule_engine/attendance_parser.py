"""將前端傳入的出勤紀錄轉換為規則引擎可用的結構"""
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from schemas.check import AttendanceRecord
from .national_holidays import get_holiday_name


@dataclass
class DayWork:
    date: datetime
    work_minutes: int           # 實際工作分鐘（已扣休息）
    overtime_minutes: int       # 加班分鐘
    is_mandatory_rest: bool     # 是否為當事人的例假日（依設定）
    is_regular_rest: bool       # 是否為當事人的休息日（依設定）
    national_holiday_name: str  # 國定假日名稱，非假日則為空字串
    clock_in_minutes: int       # 自午夜起分鐘
    clock_out_minutes: int      # 自午夜起分鐘（跨夜可 > 1440）
    rest_minutes_before: int = 0  # 距前一個出勤日下班的休息分鐘數（0 = 無前一天或不連續）
    is_agreed_rest_day_ot: bool = False  # 是否為使用者明確標記「與雇主約定的休息日加班」
    # 推定休息日出勤：某 7 日內上班 ≥ 6 天，依第 36 條第 1 項其中必有 1 天是休息日。
    # 雇主才決定是哪一天，故取該 7 日內工時最短的一天估算（寧可少估）。
    is_implied_rest_day: bool = False

    # 相容舊介面（規則引擎用）
    @property
    def is_sunday(self) -> bool:
        return self.is_mandatory_rest

    @property
    def is_weekend(self) -> bool:
        return self.is_regular_rest

    @property
    def total_minutes(self) -> int:
        return self.work_minutes + self.overtime_minutes

    @property
    def is_national_holiday(self) -> bool:
        return bool(self.national_holiday_name)

    @property
    def is_any_rest_day(self) -> bool:
        """例假、休息日（含推定）——這些日子的工時不是「平日」工時"""
        return self.is_mandatory_rest or self.is_regular_rest or self.is_implied_rest_day

    @property
    def extended_minutes(self) -> int:
        """
        計入第 32 條第 2 項（月 46／54 小時）的延長工時。
        ⛔ 2026-11 修正前只加總「加班（分）」欄位，打卡時間內的超時完全沒算
           → 每天做 11 小時的人被判「月加班約 0 小時，合規」。
        - 平日：超過 8 小時的部分（打卡時間 + 打卡外加班）
        - 休息日：整天的工時（第 36 條第 3 項「雇主使勞工於休息日工作之時間，
          計入第三十二條第二項所定延長工作時間總數」）
        - 例假：不計入（例假出勤是另一個問題，由例假規則處理）
        - 推定休息日：只算超過 8 小時的部分。推定可能被變形工時推翻，
          不能拿推定去把月加班「升級」成違規（寧可少估）。
        """
        if self.is_mandatory_rest:
            return 0
        if self.is_regular_rest:
            return self.total_minutes
        return max(0, self.total_minutes - 8 * 60)


@dataclass
class RestHolidayCollision:
    """例假日（未出勤）與國定假日重疊：應協商擇日補假"""
    date: datetime
    holiday_name: str
    rest_type: str  # "mandatory" (例假) | "regular" (休息日)


@dataclass
class ParsedAttendance:
    days: list[DayWork]
    max_consecutive_days: int
    total_work_minutes: int
    total_overtime_minutes: int
    weeks: list[list[DayWork]]
    # 出勤紀錄涵蓋期間內，例假/休息日撞國定假日的情況（含未出勤日）
    rest_holiday_collisions: list[RestHolidayCollision] = field(default_factory=list)
    # 超時／休假日上班的時數，勞工拿到了什麼：
    # "none" 完全沒拿到｜"base_only" 照原本時薪、沒加成｜"full" 有另外領加班費｜"unknown"
    ot_pay_status: str = "unknown"

    @property
    def implied_rest_days(self) -> list[DayWork]:
        return [d for d in self.days if d.is_implied_rest_day]


def _parse_time(s: str) -> int:
    """'HH:mm' → 分鐘數（自午夜起）"""
    h, m = map(int, s.split(":"))
    return h * 60 + m


def _work_minutes(record: AttendanceRecord) -> int:
    start = _parse_time(record.clock_in)
    end = _parse_time(record.clock_out)
    if end < start:
        end += 24 * 60  # 跨夜
    raw = end - start - record.break_minutes
    return max(0, raw)


def _max_consecutive(days: list[DayWork]) -> int:
    if not days:
        return 0
    sorted_days = sorted(days, key=lambda d: d.date)
    max_run = run = 1
    for i in range(1, len(sorted_days)):
        diff = (sorted_days[i].date - sorted_days[i - 1].date).days
        if diff == 1:
            run += 1
            max_run = max(max_run, run)
        elif diff > 1:
            run = 1
    return max_run


def _group_weeks(days: list[DayWork]) -> list[list[DayWork]]:
    if not days:
        return []
    week_map: dict[int, list[DayWork]] = {}
    for d in days:
        week_key = d.date.isocalendar()[1]
        week_map.setdefault(week_key, []).append(d)
    return list(week_map.values())


def _mark_implied_rest_days(sorted_days: list[DayWork]) -> None:
    """
    第 36 條第 1 項：「勞工每七日中應有二日之休息，其中一日為例假，一日為休息日。」
    → 任何 7 日內上班 ≥ 6 天，其中必有 1 天是休息日出勤。

    前端的偵測只會把「沒上班的日子」標成例假／休息日，所以一週上 6 天時
    休息日永遠找不到，休息日規則一律回「合規」（2026-11 線上實測發現）。

    作法：由最早的出勤日開始，取不重疊的 7 日視窗（找到一個就跳 7 天），
    每個視窗挑「工時最短」的一天標為推定休息日——是哪一天由雇主決定，
    挑最短的那天估算金額最保守。
    已含使用者標記的休息日／例假出勤的視窗略過（已由其他規則處理）。
    未在紀錄中的日子一律視為沒上班（與前端「未點選＝休息日」一致），
    只會讓上班天數變少，不會誤判。
    """
    worked = {d.date.date(): d for d in sorted_days}
    next_allowed = None
    for d in sorted_days:
        start = d.date.date()
        if next_allowed and start < next_allowed:
            continue
        window = [worked[start + timedelta(days=i)] for i in range(7)
                  if start + timedelta(days=i) in worked]
        if len(window) < 6:
            continue
        if any(w.is_regular_rest or w.is_mandatory_rest for w in window):
            continue
        pick = min(window, key=lambda w: (w.total_minutes, w.date))
        pick.is_implied_rest_day = True
        next_allowed = start + timedelta(days=7)


def _effective_holiday(date_str: str, overrides: dict[str, str]) -> str:
    """
    回傳該日「實際應放的國定假日名稱」（考慮補休調整）。
    - 若該日是某節日的「補休日」→ 回傳「{節日名}（補休）」
    - 若該日是原節日但已被挪走 → 回傳 ""
    - 否則回傳原本的 get_holiday_name(date_str)
    """
    # 補休日：值匹配
    for orig_date, comp_date in overrides.items():
        if comp_date == date_str:
            orig_name = get_holiday_name(orig_date)
            if orig_name:
                return f"{orig_name}（補休）"
    # 已被挪走的原節日
    if date_str in overrides:
        return ""
    return get_holiday_name(date_str)


def parse_attendance(
    records: list[AttendanceRecord],
    mandatory_day_off_weekday: int = 6,  # 0=週一…6=週日
    regular_day_off_weekday: int = 5,
    mandatory_rest_dates: list[str] | None = None,
    regular_rest_dates: list[str] | None = None,
    holiday_compensation_overrides: dict[str, str] | None = None,
    agreed_rest_day_ot_dates: list[str] | None = None,
) -> ParsedAttendance:
    # 逐日標註優先（時薪制 / 變形工時）；若提供則完全取代 weekday 判斷
    mandatory_set = set(mandatory_rest_dates or [])
    regular_set = set(regular_rest_dates or [])
    use_date_based = bool(mandatory_set or regular_set)
    holiday_overrides = holiday_compensation_overrides or {}
    agreed_ot_set = set(agreed_rest_day_ot_dates or [])

    days: list[DayWork] = []
    for r in records:
        try:
            date = datetime.strptime(r.date, "%Y-%m-%d")
        except ValueError:
            continue
        wm = _work_minutes(r)
        clock_in = _parse_time(r.clock_in)
        clock_out = _parse_time(r.clock_out)
        if clock_out < clock_in:
            clock_out += 24 * 60

        if use_date_based:
            is_mand = r.date in mandatory_set
            is_reg = r.date in regular_set
        else:
            is_mand = (date.weekday() == mandatory_day_off_weekday)
            is_reg = (date.weekday() == regular_day_off_weekday)

        days.append(DayWork(
            date=date,
            work_minutes=wm,
            overtime_minutes=r.overtime_minutes,
            is_mandatory_rest=is_mand,
            is_regular_rest=is_reg,
            national_holiday_name=_effective_holiday(r.date, holiday_overrides),
            clock_in_minutes=clock_in,
            clock_out_minutes=clock_out,
            is_agreed_rest_day_ot=(r.date in agreed_ot_set),
        ))

    # 計算各出勤日距前一出勤日的休息時間
    sorted_days = sorted(days, key=lambda d: d.date)
    for i in range(1, len(sorted_days)):
        prev = sorted_days[i - 1]
        curr = sorted_days[i]
        gap_days = (curr.date - prev.date).days
        if gap_days == 1 and prev.clock_out_minutes <= 24 * 60:
            # 跨日休息分鐘 = (今日 0:00 距前一天下班) + 今日上班前
            rest = (24 * 60 - prev.clock_out_minutes) + curr.clock_in_minutes
            curr.rest_minutes_before = rest

    _mark_implied_rest_days(sorted_days)

    # 掃描出勤期間內例假/休息日是否撞國定假日（含未出勤日）
    # 範圍：以出勤紀錄的首尾為界，並向兩側各延伸 1 天，
    # 以涵蓋「連續工作 6 天 → 邊界外的例假日（如 6/19、6/26）」這種情況。
    collisions: list[RestHolidayCollision] = []
    if sorted_days:
        worked_dates = {d.date.date() for d in sorted_days}
        start = sorted_days[0].date.date() - timedelta(days=1)
        end = sorted_days[-1].date.date() + timedelta(days=1)
        cur = start
        while cur <= end:
            cur_str = cur.strftime("%Y-%m-%d")
            holiday = _effective_holiday(cur_str, holiday_overrides)
            if holiday and cur not in worked_dates:
                # 判斷該日是否為例假/休息日
                if use_date_based:
                    is_mand = cur_str in mandatory_set
                    is_reg = cur_str in regular_set
                else:
                    wd = cur.weekday()
                    is_mand = (wd == mandatory_day_off_weekday)
                    is_reg = (wd == regular_day_off_weekday)
                if is_mand:
                    collisions.append(RestHolidayCollision(
                        date=datetime(cur.year, cur.month, cur.day),
                        holiday_name=holiday,
                        rest_type="mandatory",
                    ))
                elif is_reg:
                    collisions.append(RestHolidayCollision(
                        date=datetime(cur.year, cur.month, cur.day),
                        holiday_name=holiday,
                        rest_type="regular",
                    ))
            cur += timedelta(days=1)

    return ParsedAttendance(
        days=sorted_days,
        max_consecutive_days=_max_consecutive(days),
        total_work_minutes=sum(d.work_minutes for d in days),
        # 延長工時一律由 extended_minutes 推算（見其說明），不再只看「加班（分）」欄位
        total_overtime_minutes=sum(d.extended_minutes for d in days),
        weeks=_group_weeks(days),
        rest_holiday_collisions=collisions,
    )
