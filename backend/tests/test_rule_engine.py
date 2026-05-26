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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
