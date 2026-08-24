"""規則引擎單元測試：8 個情境（合規×2、違規×5、邊界×1）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import date, timedelta
from schemas.check import AttendanceRecord, CheckRequest
from domain.rule_engine.evaluator import evaluate


def _record(d: date, clock_in="09:00", clock_out="18:00", break_min=60, ot_min=0) -> AttendanceRecord:
    return AttendanceRecord(
        date=d.strftime("%Y-%m-%d"),
        clock_in=clock_in,
        clock_out=clock_out,
        break_minutes=break_min,
        overtime_minutes=ot_min,
    )


def _request(records: list[AttendanceRecord]) -> CheckRequest:
    return CheckRequest(
        employment_type="monthly_salary",
        schedule_type="fixed",
        attendance_records=records,
    )


# 週一=0，週日=6；找最近的週一
def _monday(offset_weeks: int = 0) -> date:
    today = date.today()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday) - timedelta(weeks=offset_weeks)
    return monday


class TestCompliant:
    """✅ 合規情境"""

    def test_normal_5day_week(self):
        """標準週一到週五，每天 8 小時，應完全合規"""
        mon = _monday(1)
        records = [_record(mon + timedelta(days=i)) for i in range(5)]
        result = evaluate(_request(records))
        assert result.risk_level == "low"
        non_compliant = [v for v in result.violations if v.status != "compliant"]
        assert len(non_compliant) == 0

    def test_6day_work_not_7(self):
        """連上 6 天班（剛好合法上限），不應觸發連續天數規則"""
        mon = _monday(1)
        records = [_record(mon + timedelta(days=i)) for i in range(6)]  # 週一到週六
        result = evaluate(_request(records))
        consecutive = next(v for v in result.violations if v.rule_id == "consecutive_days")
        assert consecutive.status == "compliant"


class TestViolations:
    """🚨 違規情境"""

    def test_consecutive_7_days(self):
        """連上 7 天班，應觸發連續天數違規"""
        mon = _monday(1)
        records = [_record(mon + timedelta(days=i)) for i in range(7)]
        result = evaluate(_request(records))
        assert result.risk_level == "high"
        v = next(v for v in result.violations if v.rule_id == "consecutive_days")
        assert v.status == "suspected_violation"

    def test_sunday_work(self):
        """例假日（週日）出勤，應觸發例假日違規"""
        sun = _monday(1) + timedelta(days=6)  # 週日
        records = [_record(sun)]
        result = evaluate(_request(records))
        v = next(v for v in result.violations if v.rule_id == "sunday_work")
        assert v.status == "suspected_violation"
        assert "第 36 條" in [ref.article_no for ref in v.law_references]

    def test_daily_overtime_over_12h(self):
        """單日工時 13 小時，應觸發每日工時超標"""
        mon = _monday(1)
        records = [_record(mon, clock_in="08:00", clock_out="21:30", break_min=30, ot_min=0)]
        result = evaluate(_request(records))
        v = next(v for v in result.violations if v.rule_id == "daily_overtime")
        assert v.status == "suspected_violation"

    def test_weekly_hours_over_40(self):
        """每天 9 小時工作 5 天 = 45 小時，超過週 40 小時"""
        mon = _monday(1)
        records = [_record(mon + timedelta(days=i), clock_out="19:00") for i in range(5)]
        result = evaluate(_request(records))
        v = next(v for v in result.violations if v.rule_id == "weekly_hours")
        assert v.status in ("suspected_violation", "warning")

    def test_unpaid_overtime_detection(self):
        """每天打卡 10 小時但未記加班，應觸發疑似無薪加班警告"""
        mon = _monday(1)
        records = [
            _record(mon + timedelta(days=i), clock_out="19:30", break_min=60, ot_min=0)
            for i in range(5)
        ]
        result = evaluate(_request(records))
        v = next(v for v in result.violations if v.rule_id == "unpaid_overtime")
        assert v.status in ("warning", "suspected_violation")


class TestEdgeCases:
    """🔲 邊界情境"""

    def test_exactly_8_hours_no_violation(self):
        """剛好 8 小時工作（不含加班），不應觸發日工時超標或無薪加班"""
        mon = _monday(1)
        # 09:00 ~ 18:00，扣 1 小時休息 = 8 小時
        records = [_record(mon, clock_in="09:00", clock_out="18:00", break_min=60, ot_min=0)]
        result = evaluate(_request(records))
        daily = next(v for v in result.violations if v.rule_id == "daily_overtime")
        unpaid = next(v for v in result.violations if v.rule_id == "unpaid_overtime")
        assert daily.status == "compliant"
        assert unpaid.status == "compliant"


class TestMonthlyOvertimeProviso:
    """⚠️ 32 條 2 項但書：46h（本文）／54h（經工會或勞資會議同意）／138h（每三個月）

    2026-08 修正前，本規則直接把 >46h 判為 suspected_violation，
    對已依但書取得同意之事業單位會產生假陽性。以下三段式邊界一律不得回歸。
    """

    def _month_with_ot(self, ot_hours_total: int):
        """造一個滿 20 天以上的月份，把加班時數平均攤到每一天（避開單日 >12h 的另一條規則）"""
        mon = _monday(4)
        days = 22
        per_day = ot_hours_total * 60 // days
        rest = ot_hours_total * 60 - per_day * days
        records = []
        for i in range(days):
            extra = per_day + (rest if i == 0 else 0)
            records.append(_record(mon + timedelta(days=i), ot_min=extra))
        return evaluate(_request(records))

    def test_46h_以下為合規(self):
        result = self._month_with_ot(40)
        v = next(v for v in result.violations if v.rule_id == "monthly_overtime")
        assert v.status == "compliant"

    def test_46至54之間不得逕判違規(self):
        """⛔ 核心迴歸測試：50h 只能是 warning，不能是 suspected_violation"""
        result = self._month_with_ot(50)
        v = next(v for v in result.violations if v.rule_id == "monthly_overtime")
        assert v.status == "warning", "46~54h 是否違法取決於有無工會／勞資會議同意，不得逕判違規"
        assert any("工會" in m for m in v.missing_facts), "必須主動問有無工會或勞資會議同意"

    def test_超過54小時才是疑似違規(self):
        result = self._month_with_ot(60)
        v = next(v for v in result.violations if v.rule_id == "monthly_overtime")
        assert v.status == "suspected_violation"
        assert "54" in v.title

    def test_金額端門檻須與規則端一致(self):
        """⛔ 規則端說「可能合法」，金額端就不能認列少領——兩邊門檻必須同源"""
        from domain.rule_engine.labor_rules import _OT_LIMIT_AGREED
        import inspect
        from domain.rule_engine import wage_calculator
        src = inspect.getsource(wage_calculator.calc_shortfall_for_rule)
        assert "_OT_LIMIT_AGREED" in src, "金額端應引用規則端常數，不得各自寫死數字"
        assert _OT_LIMIT_AGREED == 54 * 60

    def test_引用條文必須含但書(self):
        """⛔ 只抄前半句（46 小時）而漏掉但書，正是修正前的錯法"""
        result = self._month_with_ot(50)
        v = next(v for v in result.violations if v.rule_id == "monthly_overtime")
        snippet = "".join(r.get("snippet", "") if isinstance(r, dict) else getattr(r, "snippet", "")
                          for r in v.law_references)
        assert "四十六小時" in snippet
        assert "五十四小時" in snippet, "引用 32 條 2 項必須連但書一起抄"
        assert "一百三十八小時" in snippet


class TestLawReferenceIntegrity:
    """⛔ 引用條文與法規原文的硬性檢查（客觀事實部分）

    完整比對報表見 `tools/check_law_snippets.py`（該支輸出報表、不做 pass/fail，
    因為「改寫得恰不恰當」需人工判斷）。
    ⚠️ 但「條號存不存在」「引到哪一部法規」是客觀的，所以鎖在測試裡。
    """

    def _run(self):
        from tools.check_law_snippets import extract_refs, load_corpus, check_one, RULES
        corpus = load_corpus()
        return [(r, check_one(r, corpus)) for r in extract_refs(RULES)]

    def test_所有引用的條號都存在於法規語料庫(self):
        """⛔ 迴歸鎖：2026-08 曾把勞基法 34 條 2 項誤引為「施行細則第 34 條」，
        產生給使用者的連結指向錯誤的法規。"""
        bad = [(r["line"], r["article"], r["fn"]) for r, c in self._run() if c["level"] == "ERROR"]
        assert not bad, "以下引用在語料庫查無該條（條號或法規引錯）：%s" % bad

    def test_沒有引用漏抄但書或關鍵數字(self):
        """⛔ 迴歸鎖：32 條 2 項（46/54/138）與 34 條 2 項（11/8 小時）都曾只抄前半句。"""
        bad = [(r["line"], r["article"], c["issues"]) for r, c in self._run() if c["level"] == "PROBLEM"]
        assert not bad, "以下引用漏抄但書或關鍵數字：%s" % bad


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
