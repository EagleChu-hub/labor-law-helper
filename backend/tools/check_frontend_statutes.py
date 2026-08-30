# -*- coding: utf-8 -*-
"""check_frontend_statutes.py — 前端 triageTree.ts 的法條引文 vs 法規原文（報表）

【為什麼需要這支】
`tools/check_law_snippets.py` 只掃後端 `labor_rules.py`。
⛔ **前端的法律文字從來沒有被自動比對過**——CLAUDE.md 已載明這個缺口。

PR16 新增的 `frontend/lib/triageTree.ts` 會把法條原文**直接顯示給勞工看**，
而且會被帶進 AI 提示詞。它的 `STATUTES` 是**結構化**的
（article_no / quote / verified 三元組，不像 promptTemplate.ts 是整段散文），
所以只要把每個 quote 拿去跟 `raw_chunks_cache.json` 逐字比對就行。

【判定】
  OK       verified:true 且為原文之逐字片段
  PROBLEM  verified:true 但比對不到 → ⛔ 要嘛抄錯，要嘛條號錯
  SKIP     語料庫未收錄該法規（如勞動事件法）→ **不等於通過**，須以 taiwan-law 人工覆核
  WARN     verified:false → 待查證。⚠️ 這些**不得**被逐字帶進 AI 提示詞

用法：
    cd backend
    PYTHONIOENCODING=utf-8 python -m tools.check_frontend_statutes
"""
import ast
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(BASE, "data", "raw_chunks_cache.json")
TS = os.path.join(os.path.dirname(BASE), "frontend", "lib", "triageTree.ts")

# triageTree.ts 裡的 pcode 常數 → 語料庫的 law_name
PCODE_LAW = {
    "N0030001": "勞動基準法",
    "N0020007": "勞資爭議處理法",
    "B0010064": "勞動事件法",
    "N0050021": "就業保險法",
}

# ⛔ 2026/8/30：新增就業保險法時，本檔的常數名正則原本只寫死 (LSA|SDA|LIA)，
#    EIA 的那一筆被**靜默略過**——報表少一筆卻不會報錯，是靠人工數數才發現的。
#    ★ 教訓：檢查工具的「涵蓋範圍」本身也要被檢查。故改為不列舉常數名，
#      並在最後比對「TS 裡的 STATUTES 筆數」是否等於「解析出的筆數」，不符即報錯。
_CONST_NAME = r"[A-Z]{2,4}"


def norm(s: str) -> str:
    """NFKC 正規化並移除空白與標點。⛔ 原文與引文都要走這裡（雙邊一致）。"""
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[\s，。；：、（）()「」『』]", "", s)


def load_corpus():
    data = json.load(open(CORPUS, encoding="utf-8"))
    idx = {}
    for r in data:
        if r.get("doc_type") != "statute":
            continue
        meta = r.get("metadata")
        if isinstance(meta, str):
            try:
                meta = ast.literal_eval(meta)
            except Exception:
                meta = {}
        law = meta.get("law_name")
        art = re.sub(r"[^0-9\-]", "", (r.get("article_no") or "").replace("之", "-"))
        if not law or not art:
            continue
        idx.setdefault((law, art), []).append(r.get("text", ""))
    return {k: "\n".join(v) for k, v in idx.items()}


# 語料庫每條原文開頭是「勞基法第 24 條：」，比對前剝掉
_PREFIX_RE = re.compile(r"^(?:【[^】]*】)?[^：:]{0,24}第\s*[0-9]+(?:\s*之\s*[0-9]+)?\s*條[：:]")


def parse_ts():
    """從 triageTree.ts 取出 (article_no, quote, pcode, flno, verified)。"""
    src = open(TS, encoding="utf-8").read()

    consts = dict(re.findall(r'const (%s) = "([A-Z0-9]+)";' % _CONST_NAME, src))

    # 只掃 STATUTES 區塊，避免抓到別處的字串
    m = re.search(r"export const STATUTES[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        sys.exit("找不到 STATUTES 區塊")
    body = m.group(1)

    entries = []
    for block in re.finditer(
        r"article_no:\s*\"([^\"]+)\",\s*"
        r"quote:\s*\n?\s*\"((?:[^\"\\]|\\.)*)\",\s*"
        r"source_url:\s*moj\((%s),\s*\"([0-9-]+)\"\),\s*"
        r"verified:\s*(true|false)" % _CONST_NAME,
        body,
        re.S,
    ):
        art_no, quote, cname, flno, ver = block.groups()
        entries.append({
            "article_no": art_no,
            "quote": quote.encode().decode("unicode_escape") if "\\" in quote else quote,
            "law": PCODE_LAW.get(consts.get(cname, ""), "?"),
            "flno": flno,
            "verified": ver == "true",
        })

    # ⛔ 涵蓋率自檢：STATUTES 裡有幾個 key，就該解析出幾筆。
    #    少一筆而不報錯，正是本檔 2026/8/30 犯過的錯。
    declared = len(re.findall(r"^  [A-Za-z0-9_]+: \{$", body, re.M))
    if declared != len(entries):
        sys.exit(
            "⛔ 解析涵蓋率不符：STATUTES 宣告 %d 筆，只解析出 %d 筆。\n"
            "   有法條被靜默略過——請檢查 parse_ts() 的正則與 PCODE_LAW 是否漏了新法規。"
            % (declared, len(entries))
        )
    return entries


def main():
    corpus = load_corpus()
    entries = parse_ts()
    print("語料庫條文數：%d　│　triageTree.ts 法條引文：%d\n" % (len(corpus), len(entries)))

    tally = {}
    for e in entries:
        head = "%s（%s 第 %s 條）" % (e["article_no"], e["law"], e["flno"])

        if not e["verified"]:
            level, msg = "WARN", "⚠️ 標記為待查證——⛔ 不得逐字帶進 AI 提示詞"
        else:
            original = corpus.get((e["law"], e["flno"]))
            if original is None:
                laws = {k[0] for k in corpus}
                if e["law"] not in laws:
                    level, msg = "SKIP", "－ 語料庫未收錄《%s》，**不等於通過**，須以 taiwan-law 覆核" % e["law"]
                else:
                    level, msg = "PROBLEM", "⛔ 語料庫收錄該法但查無第 %s 條——條號可能寫錯" % e["flno"]
            else:
                clean = _PREFIX_RE.sub("", original, count=1)
                if norm(e["quote"]) in norm(clean):
                    level, msg = "OK", "✅ 逐字相符"
                else:
                    level, msg = "PROBLEM", "⛔ 與原文不符——引文可能抄錯、漏抄或改寫"

        tally[level] = tally.get(level, 0) + 1
        icon = {"OK": "✅", "WARN": "⚠️ ", "PROBLEM": "⛔", "SKIP": "－"}[level]
        print("%s %s" % (icon, head))
        print("   %s" % msg)
        if level == "PROBLEM":
            print("   引文：%s" % e["quote"][:110])
        print()

    print("── 統計 ──")
    for k in ("OK", "WARN", "PROBLEM", "SKIP"):
        if k in tally:
            print("  %-8s %d" % (k, tally[k]))
    print("\n⛔ SKIP 不等於通過。語料庫未收錄的法規仍須以 taiwan-law MCP 人工覆核。")
    return 1 if tally.get("PROBLEM") else 0


if __name__ == "__main__":
    sys.exit(main())
