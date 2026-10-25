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


class TestProseStatuteIntegrity:
    """⛔ 提示詞「散文」法律敘述的硬性檢查（PR18）

    完整比對報表見 `tools/check_prose_statutes.py`。本類只鎖兩件事：
      1. 現行提示詞不得有 PROBLEM（正向鎖）
      2. **工具本身真的會叫**（反向鎖）

    ★ 第 2 點是重點。沒觸發過的守衛等於沒有守衛——一支因為正則寫壞而
      永遠回報「0 問題」的檢核工具，比沒有工具更危險，因為它會讓人放心。
      故下面刻意注入 PR18 修正前的原始錯誤文字，確認工具會報 PROBLEM。
    """

    def _check(self, prose: str, pcode: str, flno: str):
        from tools.check_prose_statutes import check_claim, load_corpus
        by_article, by_law = load_corpus()
        return check_claim(prose, pcode, flno, by_article, by_law)

    # ── 正向鎖：現行提示詞乾淨 ──────────────────────────────
    def test_現行提示詞散文無漏抄但書或要件(self):
        """⛔ 迴歸鎖：涵蓋後端 SYSTEM_PROMPT 與前端 promptTemplate.ts。"""
        from tools.check_prose_statutes import (
            check_claim, check_block_numbers, load_corpus, extract_backend_prose,
            extract_frontend_prose, split_claims, find_citations)
        by_article, by_law = load_corpus()
        bad = []
        for fname, const, base, text in extract_backend_prose() + extract_frontend_prose():
            carry = None
            for off, claim in split_claims(text):
                cites, carry = find_citations(claim, carry)
                if not cites:
                    continue
                hard, _soft = check_block_numbers(claim, cites, by_article, by_law)
                if hard:
                    bad.append((fname, const, base + off - 1, "〔數字〕", hard))
                for pcode, flno, inferred in cites:
                    r = check_claim(claim, pcode, flno, by_article, by_law, inferred)
                    if r["level"] in ("PROBLEM", "ERROR"):
                        bad.append((fname, const, base + off - 1, flno, r["issues"]))
        assert not bad, "提示詞散文有漏抄但書／要件、引錯條號或無法源數字：%s" % bad

    # ── 反向鎖：故意注入壞資料，工具必須叫 ──────────────────
    def test_偵測得到漏抄合法化要件(self):
        """⛔ PR18 修正前的原文（私人版）。它只寫「公告得實施變形工時的行業並已報備」，
        漏掉勞基法 36 條 4、5 項的「中央目的事業主管機關同意」與「工會／勞資會議同意」。
        ★ 後果是**假陰性**：AI 會告訴勞工「你老闆挪你例假是合法的」。"""
        r = self._check(
            "時薪制／部分工時：第 36 條原則上同樣適用；但若雇主屬於勞動部公告得實施"
            "「變形工時」（2/4/8 週）的行業並已報備，例假位置可在 7 日內彈性調整。",
            "N0030001", "36")
        assert r["level"] == "PROBLEM", "工具未偵測到漏抄合法化要件：%s" % r
        assert any("合法化要件" in i for i in r["issues"]), r["issues"]

    def test_偵測得到漏抄但書(self):
        """⛔ 職安法 22-1 的「但情節重大者，不以持續發生為必要」若漏抄，
        會讓單次重大霸凌被誤判為不成立。"""
        r = self._check(
            "職場霸凌的定義是：利用職務權勢、逾越業務上必要且合理範圍，"
            "持續以冒犯、威脅、冷落、孤立、侮辱之言行，致其身心健康遭受危害。",
            "N0060001", "22-1")
        assert r["level"] == "PROBLEM", "工具未偵測到漏抄但書：%s" % r
        assert any("但書" in i for i in r["issues"]), r["issues"]

    def test_偵測得到無法源的數字(self):
        """⛔「不得連續工作超過 12 日」在勞基法全文查無，屬無法源之法律斷言
        （PR18 修正前兩份提示詞都這樣寫）。

        ★ 這一條同時鎖住「數字必須連單位一起比」：數字 12 以「一日不得超過
          十二小時」的形式存在於第 32 條，若只比裸數字，本例會被誤判為
          「出自同法他條」而降級成 WARN 放過去。單位不同就是不同的法律主張。
        """
        from tools.check_prose_statutes import check_block_numbers, load_corpus
        by_article, by_law = load_corpus()
        hard, _soft = check_block_numbers(
            "依勞基法第 36 條，例假調整後仍不得連續工作超過 12 日。",
            [("N0030001", "36", False)], by_article, by_law)
        assert hard, "工具未偵測到無法源的數字（12 日）"
        assert any("查無" in i for i in hard), hard

    def test_數字帶單位時不得跨單位誤判為有法源(self):
        """⚠️ 反向：「每週 40 小時」確實出自勞基法第 30 條第 1 項，不該被報成無法源。"""
        from tools.check_prose_statutes import check_block_numbers, load_corpus
        by_article, by_law = load_corpus()
        hard, _ = check_block_numbers(
            "勞基法第 30 條第 1 項：每日不得超過 8 小時，每週不得超過 40 小時。",
            [("N0030001", "30", False)], by_article, by_law)
        assert not hard, "正確引用被誤判為無法源：%s" % hard

    # ── 不得狼來了：假警報也要被鎖住 ────────────────────────
    def test_不對否定句要求複述要件(self):
        """⚠️「時薪制也不會因為是時薪就可以挪例假」語意是**否認**該許可，
        不該要求它複述要件。一份會亂叫的報表等於沒有報表。"""
        r = self._check(
            "勞基法第 36 條第 1 項「勞工每七日中應有二日之休息，其中一日為例假，"
            "一日為休息日」嚴格適用；時薪制也不會因為是時薪就可以挪例假。",
            "N0030001", "36")
        assert r["level"] != "PROBLEM", "否定句被誤判為許可型敘述：%s" % r["issues"]

    def test_交叉引用與清單編號不得被當成實質數字(self):
        """⚠️「第三十六條所定」的三十六、清單編號「7.」、日期「2026 年 7 月 1 日」
        都不是法律數字；誤判會製造假警報。"""
        from tools.check_prose_statutes import numbers_of
        assert numbers_of("第三十六條所定休息日") == set()
        assert numbers_of("7. 職場霸凌問題") == set()
        assert numbers_of("已於 2026 年 7 月 1 日生效施行") == set()
        assert numbers_of("第 22-1~22-3 條") == set()

    def test_中文數字正規化(self):
        """★ 本工具的地基：法條寫「四十六小時」，提示詞寫「46 小時」，
        不正規化就無法比對，報表會把每一筆都報成漏抄。"""
        from tools.check_prose_statutes import cjk_to_int
        for s, want in [("七", 7), ("十二", 12), ("四十六", 46), ("五十四", 54),
                        ("一百三十八", 138), ("四十八", 48), ("十六", 16)]:
            assert cjk_to_int(s) == want, "%s → %s（應為 %s）" % (s, cjk_to_int(s), want)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
