"""
PR28：條次核對清單由程式產生。
⛔ 含反向鎖——故意餵不存在的條次，確認它真的會標「查無此條」。
   一支永遠回報 ✅ 的核對器比沒有更危險。
"""
from domain.rag.citation_checker import (
    SECTION_TITLE, append_verification, extract_citations,
)


def _by(text):
    return {(c["law"], c["art"]): c["status"] for c in extract_citations(text)}


def test_存在的條次標為found且附原文連結():
    cites = extract_citations("可能違反《勞動基準法》第 24 條。")
    assert len(cites) == 1
    assert cites[0]["status"] == "found"
    assert "law.moj.gov.tw" in cites[0]["url"]


def test_反向鎖_不存在的條次必須標missing():
    r = _by("依勞動基準法第 999 條，老闆要賠你三倍。")
    assert r == {("勞動基準法", "999"): "missing"}
    md = append_verification("## 老闆可能違法的地方\n依勞動基準法第 999 條。\n")
    assert "查無此條" in md
    assert "✅" not in md


def test_施行細則不可被勞基法吃掉():
    # 勞基法只有 86 條上下，施行細則才有 22-3；判錯法規會把真條文報成查無
    r = _by("勞基法施行細則第 22-3 條規定不得連續工作逾六日。")
    assert r == {("勞動基準法施行細則", "22-3"): "found"}


def test_裸條號沿用最近的前方法規名():
    r = _by("《勞動基準法》第 36 條第 2 項或第 30 條之 1 的規定；另依職安法第 22-1 條。之後第 22-3 條。")
    assert r == {
        ("勞動基準法", "36"): "found",
        ("勞動基準法", "30-1"): "found",
        ("職業安全衛生法", "22-1"): "found",
        ("職業安全衛生法", "22-3"): "found",
    }


def test_列舉與範圍都要展開():
    r = _by("勞基法第 24、39 條，以及職安法第 22-1~22-3 條。")
    assert r == {
        ("勞動基準法", "24"): "found",
        ("勞動基準法", "39"): "found",
        ("職業安全衛生法", "22-1"): "found",
        ("職業安全衛生法", "22-2"): "found",
        ("職業安全衛生法", "22-3"): "found",
    }


def test_中文數字條號():
    assert _by("勞動基準法第三十六條") == {("勞動基準法", "36"): "found"}


def test_未收錄的法規不可冒充已核對():
    cites = extract_citations("依《個人資料保護法》第 5 條，以及刑法第 304 條。")
    assert [c["status"] for c in cites] == ["unknown_law", "unknown_law"]
    assert cites[0]["law"] == "個人資料保護法"


def test_未收錄法規之後的裸條號不可算到前一部法規頭上():
    r = extract_citations("勞基法第 24 條。另依《個人資料保護法》第 5 條及第 6 條。")
    assert [(c["art"], c["status"]) for c in r] == [
        ("24", "found"), ("5", "unknown_law"), ("6", "unknown_law"),
    ]


def test_沒寫法規名稱():
    assert [c["status"] for c in extract_citations("老闆違反第 36 條。")] == ["no_law"]


def test_AI自己寫的清單會被換掉且清單只含正文條次():
    ai = (
        "## 老闆可能違法的地方\n可能違反勞動基準法第 24 條。\n\n"
        "## 申訴管道\n撥 1955。\n\n"
        f"{SECTION_TITLE}\n* 勞動基準法第 24 條\n* 勞動基準法施行細則第 50 條\n"
    )
    md = append_verification(ai)
    assert md.count(SECTION_TITLE) == 1
    tail = md.split(SECTION_TITLE)[1]
    assert "第 24 條" in tail
    assert "第 50 條" not in tail  # PR27 實測到的毛病：AI 多列正文沒引用的條文
    assert "不是 AI 寫的" in tail
    assert "沒有**確認" in tail  # 沒檢查的事要明講
    assert "主管機關或專業人員" in tail


def test_沒有任何條次時要明講():
    md = append_verification("## 老闆可能違法的地方\n資料不足。\n")
    assert "沒有寫到任何條次" in md
