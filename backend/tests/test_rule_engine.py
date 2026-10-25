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


class TestAdvisoryProseIntegrity:
    """⛔ `/triage` advisory 散文的硬性檢查（PR19）

    ★ 這批文字是**全站風險最高的法律敘述**：直接印在畫面上給勞工讀，
      中間連 LLM 都沒有，它說什麼勞工就信什麼。
      但在 PR19 之前只驗過 `STATUTES` 的 `quote`，**advisory 的散文沒驗過**。

    完整報表見 `tools/check_frontend_statutes.py`。
    """

    def _all(self):
        from tools.check_frontend_statutes import (
            parse_advisories, parse_statute_keys, load_corpus, check_advisory)
        corpus, keymap = load_corpus(), parse_statute_keys()
        return [(a, check_advisory(a, keymap, corpus)) for a in parse_advisories()]

    # ── 正向鎖 ──────────────────────────────────────────────
    def test_advisory_散文無但書遺漏或引用不足(self):
        bad = [(a["id"], [m for lv, m in f if lv == "PROBLEM"])
               for a, f in self._all() if any(lv == "PROBLEM" for lv, _ in f)]
        assert not bad, "advisory 散文有問題：%s" % bad

    def test_practice_類型不得掛法條(self):
        """⛔ `triageTree.ts` 註解聲稱「型別上就不可能掛法條」，但
        TypeScript 的 `kind: "legal" | "practice"` 配 `statutes: string[]`
        **並不會**強制這件事——它只是個約定。約定要有東西守著才算數。"""
        bad = [a["id"] for a, _ in self._all()
               if a["kind"] == "practice" and a["statutes"]]
        assert not bad, "kind=practice 卻掛了法條：%s（經驗談不該掛法條）" % bad

    def test_legal_類型必須有法條依據(self):
        bad = [a["id"] for a, _ in self._all()
               if a["kind"] == "legal" and not a["statutes"]]
        assert not bad, "kind=legal 卻沒有法條依據：%s" % bad

    # ── 反向鎖：故意注入壞資料，工具必須叫 ──────────────────
    def test_偵測得到漏講勞工自己的義務(self):
        """⛔ PR19 修正前的原文：`mediation_shield` 只寫「公司不可以…」，
        漏掉勞資爭議處理法第 8 條同一條對勞方的要求
        （不得因該勞資爭議事件而罷工或為其他爭議行為）。

        ★ 本站立場親勞工，寫作時系統性地容易只寫雇主那一半
          ——而漏掉的那一半正是會讓勞工自己踩進去的部分。
        """
        from tools.check_frontend_statutes import (
            parse_statute_keys, load_corpus, check_advisory)
        found = check_advisory(
            {"id": "x", "kind": "legal", "statutes": ["SDA8"],
             "body": "在調解進行的期間，公司不可以因為這件事就把你解僱或做其他對你不利的事。"},
            parse_statute_keys(), load_corpus())
        assert any(lv == "PROBLEM" and "對勞工自己" in m for lv, m in found), found

    def test_偵測得到引文撐不住散文的數字(self):
        """⛔ PR19 修正前的原文：`separation_certificate` 寫了「兩年內辦」，
        但 statutes 只列就業保險法第 25 條第 3 項——那一項的引文裡沒有「二年」
        （期限在第 1 項）。勞工看到的是引文，引文撐不住就等於沒有依據。

        ★ 這一條同時鎖住檢查的**粒度**：語料庫以「條」為單位，
          整條當然含「二年」，所以比對基準必須是**畫面顯示的引文**，不是整條。
        """
        from tools.check_frontend_statutes import (
            parse_statute_keys, load_corpus, check_advisory)
        found = check_advisory(
            {"id": "x", "kind": "legal", "statutes": ["EIA25_3"],
             "body": "要在離職退保後兩年內辦。"},
            parse_statute_keys(), load_corpus())
        assert any(lv == "PROBLEM" and "引文" in m for lv, m in found), found

    def test_偵測得到body誤用markdown(self):
        """⛔ `AdvisoryCard` 以 `{b}` 純文字渲染 body，寫 `**粗體**` 會原樣印出來。
        CLAUDE.md ⓭ 在 PR17 就記過這個坑，PR19 寫新文案時**還是踩了**
        （畫面上真的印出字面的「**不等於就沒事了**」）。
        ★ 寫在文件裡不夠——重複犯的錯要有東西守著。"""
        from tools.check_frontend_statutes import (
            parse_statute_keys, load_corpus, check_advisory)
        found = check_advisory(
            {"id": "x", "kind": "practice", "statutes": [],
             "body": "你**仍然可以**先請領失業給付。"},
            parse_statute_keys(), load_corpus())
        assert any(lv == "PROBLEM" and "markdown" in m for lv, m in found), found

    def test_偵測得到practice掛法條(self):
        from tools.check_frontend_statutes import (
            parse_statute_keys, load_corpus, check_advisory)
        found = check_advisory(
            {"id": "x", "kind": "practice", "statutes": ["LSA19"], "body": "隨便寫。"},
            parse_statute_keys(), load_corpus())
        assert any(lv == "PROBLEM" and "practice" in m for lv, m in found), found

    # ── 不得狼來了 ──────────────────────────────────────────
    def test_時效advisory給得出可判斷的標準(self):
        """⛔ PR16 起連續五個 PR，這一段都只寫「本工具沒有幫你算，去打 1955」。
        ★ 期限長度是法條明文，勞工自己查得到，沒理由不告訴他
          （全域指引：籠統的「建議諮詢專業人士」是雜訊）。
        本測試鎖住它必須是 legal 且掛得上法條，不能退回純經驗談。
        """
        advs = {a["id"]: a for a, _ in self._all()}
        a = advs["no_limitation_check"]
        assert a["kind"] == "legal", "時效說明退回 practice（又變成沒有法源的空話）"
        for k in ("CIV126", "CIV129", "LSA58", "LSA61", "EIA24"):
            assert k in a["statutes"], "時效 advisory 少了 %s" % k
        # ★ 最有用的那一句不能掉：聲請調解會中斷時效（民法 129），
        #   這把「我來不來得及」變成「現在就去做這件事」。
        assert "中斷" in a["body"], "漏掉時效中斷——那是這一段唯一可行動的出口"
        assert "六個月" in a["body"], "漏掉民法 130 的六個月陷阱（只寄存證信函不夠）"

    def test_指示詞不得被當成法律數量(self):
        """⚠️「哪一天」「那一年」是指稱不是數量。
        ⛔ 不剝掉的話，白話散文寫「每一筆錢是哪一天可以請求的」會被誤報成「1 日」無法源
        ——而且會逼後人為了閃避檢查而寫出彆扭的中文。會逼人改爛文字的工具是壞工具。"""
        from tools.check_prose_statutes import legal_numbers_of
        assert legal_numbers_of("每一筆錢是哪一天可以請求的") == set()
        assert legal_numbers_of("那一年的加班費") == set()
        # 反向：法定數量不得被誤刪
        assert legal_numbers_of("一年或不及一年之定期給付債權") == {"1年"}
        assert legal_numbers_of("請求後六個月內不起訴") == {"6月"}

    def test_圈號與計數詞不得被當成法律數字(self):
        """⚠️「① ② ③」經 NFKC 會變成 1、2、3，「兩個可以一起用」也會被撿到。
        拿這些去比對法條，報表會被廢話灌滿。"""
        from tools.check_prose_statutes import legal_numbers_of
        assert legal_numbers_of("① 先跟公司要。② 公司不給。③ 還是拿不到。") == set()
        assert legal_numbers_of("這是另一道保護，兩個可以一起用。") == set()
        assert legal_numbers_of("要在離職退保後二年內辦") == {"2年"}
        assert legal_numbers_of("十日之不變期間") == {"10日"}


class TestPathProseIntegrity:
    """⛔ `/triage` 五條路線的散文檢查（PR22）

    `PATHS[*].effect` / `cannotDo` / `cost` 是**使用者據以決定走哪條路**的敘述
    ——寫錯會讓他選錯程序，代價比看錯一條法條更大。
    """

    def _all(self):
        from tools.check_frontend_statutes import (
            parse_paths, parse_statute_keys, load_corpus, check_advisory)
        corpus, keymap = load_corpus(), parse_statute_keys()
        return [(p, check_advisory(p, keymap, corpus)) for p in parse_paths()]

    def test_五條路線都解析得到(self):
        """⚠️ 承 PR17 教訓：檢查工具的涵蓋範圍本身也要被檢查。"""
        ids = {p["id"] for p, _ in self._all()}
        assert ids == {"internal", "agency", "admin_mediation",
                       "court_mediation", "litigation"}, ids

    def test_路線散文無但書遺漏或引用不足(self):
        bad = [(p["id"], [m for lv, m in f if lv == "PROBLEM"])
               for p, f in self._all() if any(lv == "PROBLEM" for lv, _ in f)]
        assert not bad, "路線散文有問題：%s" % bad

    def test_訴訟路線不得寫成不能直接起訴(self):
        """⛔ 迴歸鎖：原文寫「不能直接打」，但勞動事件法第 16 條第 2 項明定
        「前項事件當事人逕向法院起訴者，**視為調解之聲請**」——不是退件。
        ★ 把附例外的規定講成絕對的規定，會讓勞工以為送件會被拒絕而不敢送。"""
        p = {x["id"]: x for x, _ in self._all()}["litigation"]
        assert "不能直接打" not in p["body"], "又把 16 條講成絕對禁止了"
        assert "視為聲請調解" in p["body"] or "視為調解之聲請" in p["body"] \
            or "視為聲請" in p["body"], "沒講出逕行起訴會被視為調解聲請"

    def test_內部申訴路線要講出它啟動的保護(self):
        """⛔ 迴歸鎖：原文只寫「幾乎沒有強制力」，等於告訴勞工這步沒用。
        但勞基法第 74 條第 2、3 項的報復保護正是「為前項申訴」才啟動的
        ——這步拿不到錢，卻會打開他最硬的那面盾。"""
        p = {x["id"]: x for x, _ in self._all()}["internal"]
        assert "無效" in p["body"], "沒講出申訴會讓後續報復處分無效"


class TestCorpusCoverage:
    """⛔ 語料庫涵蓋範圍的硬性檢查（PR20）

    `raw_chunks_cache.json` 是 **Render 雲端唯一的法規來源**（雲端沒有 ChromaDB），
    所以「某部法規在不在語料庫裡」不是內部細節，而是雲端查不查得到的分水嶺。
    """

    def _corpus(self):
        import ast
        import json
        from pathlib import Path
        p = Path(__file__).parent.parent / "data" / "raw_chunks_cache.json"
        out = {}
        for c in json.loads(p.read_text(encoding="utf-8")):
            m = c.get("metadata")
            if isinstance(m, str):
                try:
                    m = ast.literal_eval(m)
                except Exception:
                    m = {}
            if isinstance(m, dict) and m.get("law_name"):
                out.setdefault(m["law_name"], []).append(c)
        return out

    def test_必備法規都在語料庫裡(self):
        """⛔ 迴歸鎖：任何一部掉出語料庫，雲端就查不到該法
        （本機有 ChromaDB 不會發現，只有上線後使用者才會踩到）。

        ⚠️ 勞動事件法是 PR20 才補進來的。在那之前 `/triage` 有 7 筆引用
        只能標 SKIP，每次都得人工以 taiwan-law MCP 覆核。
        """
        corpus = self._corpus()
        required = {
            "勞動基準法": 90, "勞動基準法施行細則": 60, "職業安全衛生法": 55,
            "職場霸凌防治措施準則": 25, "勞資爭議處理法": 60,
            "就業保險法": 40, "勞動事件法": 50,
        }
        missing = {k: (len(corpus.get(k, [])), lo)
                   for k, lo in required.items() if len(corpus.get(k, [])) < lo}
        assert not missing, "語料庫缺漏或條數異常（實際, 下限）：%s" % missing

    def test_triage引用的勞動事件法條文都查得到(self):
        """★ PR20 之後這批不該再出現 SKIP——SKIP 不等於通過。"""
        from tools.check_frontend_statutes import parse_ts, load_corpus
        corpus = load_corpus()
        missing = [e["article_no"] for e in parse_ts()
                   if e["law"] == "勞動事件法"
                   and corpus.get((e["law"], e["flno"])) is None]
        assert not missing, "勞動事件法條文在語料庫查無：%s" % missing


class TestCacheShrinkGuard:
    """⛔ `build_index` 的防縮水守衛（PR20）

    `raw_chunks_cache.json` 是雲端唯一的法規來源，而 `build_index` 原本
    **無條件覆寫**它。任何一個爬蟲斷線，就會靜默寫入一份少了法條的快取，
    commit 上去之後雲端查不到那些條文，而且沒有任何錯誤訊息。

    專案文件一直寫著「總數變少就不得保留」，但那是**人工紀律**，沒有東西守著。
    ★ 本類確認守衛真的會攔（沒觸發過的守衛等於沒有守衛）。
    """

    def _full(self):
        import json
        from data.build_index import CACHE_PATH
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    def test_語料整批消失時會攔下(self):
        from data.build_index import guard_cache_shrink
        full = self._full()
        shrunk = [c for c in full if "勞動基準法" not in str(c.get("metadata", ""))]
        with pytest.raises(SystemExit) as e:
            guard_cache_shrink(shrunk)
        assert e.value.code == 2

    def test_總數相同但某來源消失也會攔下(self):
        """★ 這是加「逐來源比對」的理由：勞基法掉 98 筆、函釋剛好多抓 98 筆，
        **總數看起來毫無異狀**，法條卻已經不見了。只看總數抓不到這種。"""
        import copy
        from data.build_index import guard_cache_shrink
        full = self._full()
        kept = [c for c in full if "勞動基準法'" not in str(c.get("metadata", ""))]
        filler = []
        for i in range(len(full) - len(kept)):
            f = copy.deepcopy(full[0])
            f["chunk_id"] = "fake_%d" % i
            f["metadata"] = {"law_name": "勞動部函釋", "pcode": "X", "flno": str(i)}
            filler.append(f)
        same = kept + filler
        assert len(same) == len(full), "測試前提：總數必須相同"
        with pytest.raises(SystemExit) as e:
            guard_cache_shrink(same)
        assert e.value.code == 2

    def test_只增不減時放行(self):
        """⚠️ 守衛不能擋住正常的新增，否則沒人敢跑 build_index。"""
        import copy
        from data.build_index import guard_cache_shrink
        full = self._full()
        extra = copy.deepcopy(full[0])
        extra["chunk_id"] = "brand_new"
        extra["metadata"] = {"law_name": "新法規", "pcode": "Z", "flno": "1"}
        guard_cache_shrink(full + [extra])      # 不該 raise


class TestProceduralSynonyms:
    """⛔ 訴訟程序口語 → 法條用詞的查詢擴充（PR20）

    ★ 不加這組的話，PR20 新進語料庫的 53 條勞動事件法條文**形同沒進來**：
      雲端只有 BM25 逐字比對，而勞工不會說「起訴」「出勤紀錄」，
      他說「告公司」「打卡紀錄」。
      實測：擴充前 top-5 命中 4/9，擴充後 8/9，對照組不受影響。
    """

    def _expand(self, q):
        from domain.retriever.hybrid_retriever import _expand_query
        return _expand_query(q)

    def test_口語會被擴充成法條用詞(self):
        assert "起訴" in self._expand("要告公司是不是要先調解")
        assert "出勤紀錄" in self._expand("打卡紀錄能不能當證據")
        assert "續行訴訟" in self._expand("調解不成立之後會怎樣")
        assert "暫免徵收" in self._expand("裁判費要付多少")

    def test_不相關查詢不得被擴充(self):
        """⚠️ 擴充要精準。亂擴充會把不相關的條文拉進來，
        反而稀釋原本正確的結果（PR12 已記過這個紀律）。"""
        for q in ["今天天氣如何", "中午吃什麼"]:
            assert self._expand(q) == q, "不相關查詢被擴充了：%s" % q

    def test_訴訟程序口語實際檢索得到勞動事件法(self):
        """⛔ 端到端：不是只看擴充字串，而是真的跑 BM25（模擬雲端無向量索引）。"""
        import os
        os.environ.setdefault("CHROMA_PATH", "./__nonexistent_for_test__")
        from domain.retriever.bm25_retriever import bm25_search
        cases = [
            ("要告公司是不是一定要先經過調解", "勞動事件法第 16 條"),
            ("法院給的調解方案我幾天內要回覆", "勞動事件法第 29 條"),
            ("公司說我沒加班 打卡紀錄能不能當證據", "勞動事件法第 38 條"),
        ]
        bad = []
        for q, want in cases:
            titles = [r.get("title", "") for r in bm25_search(self._expand(q), top_k=5)]
            if not any(want in t for t in titles):
                bad.append((q, want, titles[:3]))
        assert not bad, "口語問法查不到對應條文：%s" % bad


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
