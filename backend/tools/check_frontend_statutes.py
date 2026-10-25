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
    "B0000001": "民法",
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


# ── advisory 散文檢查（PR19 新增）──────────────────────────────
# ⛔ 為什麼要補這一段：本檔原本只驗 `STATUTES` 的 `quote`（結構化引文），
#    但 `ADVISORIES[*].body` 是**直接印在畫面上給勞工讀的散文**，
#    中間連 LLM 都沒有，它說什麼勞工就信什麼——卻從來沒有被比對過。
#    ★ 這是全站風險最高的法律文字，比提示詞還高（提示詞至少還經過 LLM 重述）。
# ★ 這裡比提示詞好驗：advisory 的 `statutes: [...]` 已經**明確宣告**了它依據哪幾條，
#   不必像 check_prose_statutes 那樣從散文裡猜法規名。

def parse_statute_keys():
    """key → (law, flno, quote)，供 advisory 的 statutes 欄位解析。

    ⚠️ `quote` 一併帶出來，因為勞工在畫面上看到的是 quote（通常只有其中一「項」），
       不是整條。「這個數字在不在他看得到的文字裡」才是對他有意義的問題。
    """
    src = open(TS, encoding="utf-8").read()
    consts = dict(re.findall(r'const (%s) = "([A-Z0-9]+)";' % _CONST_NAME, src))
    m = re.search(r"export const STATUTES[^=]*=\s*\{(.*?)\n\};", src, re.S)
    body = m.group(1)
    out = {}
    for blk in re.finditer(
            r"\n  ([A-Za-z0-9_]+): \{(.*?)\n  \},", body + "\n  },", re.S):
        key, inner = blk.group(1), blk.group(2)
        mm = re.search(r"source_url:\s*moj\((%s),\s*\"([0-9-]+)\"\)" % _CONST_NAME, inner)
        qm = re.search(r"quote:\s*\n?\s*\"((?:[^\"\\]|\\.)*)\"", inner, re.S)
        if mm:
            out[key] = (PCODE_LAW.get(consts.get(mm.group(1), ""), "?"),
                        mm.group(2), qm.group(1) if qm else "")
    return out


def parse_advisories():
    """從 triageTree.ts 取出 ADVISORIES 的 id / kind / body / statutes。"""
    src = open(TS, encoding="utf-8").read()
    m = re.search(r"export const ADVISORIES[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        sys.exit("找不到 ADVISORIES 區塊")
    body = m.group(1)

    out = []
    for blk in re.finditer(r"\n  ([a-z0-9_]+): \{(.*?)\n  \},", body + "\n  },", re.S):
        aid, inner = blk.group(1), blk.group(2)
        kind = (re.search(r'kind:\s*"(\w+)"', inner) or [None, "?"])[1] \
            if re.search(r'kind:\s*"(\w+)"', inner) else "?"
        bm = re.search(r"body:\s*\[(.*?)\]", inner, re.S)
        lines = re.findall(r'"((?:[^"\\]|\\.)*)"', bm.group(1)) if bm else []
        sm = re.search(r"statutes:\s*\[(.*?)\]", inner, re.S)
        keys = re.findall(r'"([A-Za-z0-9_]+)"', sm.group(1)) if sm else []
        out.append({"id": aid, "kind": kind, "body": "\n".join(lines), "statutes": keys})

    # ⛔ 涵蓋率自檢（承 PR17 教訓：檢查工具的涵蓋範圍本身也要被檢查）
    declared = len(re.findall(r"^  [a-z0-9_]+: \{$", body, re.M))
    if declared != len(out):
        sys.exit("⛔ ADVISORIES 宣告 %d 筆，只解析出 %d 筆——有 advisory 被靜默略過"
                 % (declared, len(out)))
    return out


# body 誤用 markdown。AdvisoryCard 以 `{b}` 純文字渲染，寫了會原樣顯示。
_MARKDOWN_RE = re.compile(r"\*\*|__|^\s*[#>]\s|\[[^\]]+\]\([^)]+\)", re.M)

# 課予**勞工自身**義務／限制的語句。本站立場親勞工，寫作時系統性地容易只寫
# 「雇主不得…」而漏掉同一條對勞工的要求——漏掉等於讓勞工踩進去。
# （repo 既有的 EIA36 刑責警告就是這類補強，本檢查把它制度化。）
_WORKER_DUTY_RE = re.compile(
    r"勞方不得[^。；]*|勞工不得[^。；]*|申請人[^。；]{0,8}?應[^。；]*"
    r"|不得請領[^。；]*|應[^。；]{0,10}?返還[^。；]*|視為未申請[^。；]*"
    r"|應於[^。；]{0,16}?內補正[^。；]*")


def parse_paths():
    """從 triageTree.ts 取出 PATHS 的 id / 散文欄位 / statutes。

    ⚠️ `effect`／`cannotDo`／`cost` 同樣是**直接印給勞工看的法律敘述**，
       而且它們是使用者決定「要走哪條路」的依據——寫錯會讓他選錯程序。
    """
    src = open(TS, encoding="utf-8").read()
    m = re.search(r"export const PATHS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        sys.exit("找不到 PATHS 區塊")
    body = m.group(1)

    out = []
    for blk in re.finditer(r"\n  ([a-z_]+): \{(.*?)\n  \},", body + "\n  },", re.S):
        pid, inner = blk.group(1), blk.group(2)
        texts = []
        for field in ("name", "plainName", "where", "effect", "cannotDo", "cost"):
            fm = re.search(r'%s:\s*"((?:[^"\\]|\\.)*)"' % field, inner)
            if fm:
                texts.append(fm.group(1))
        sm = re.search(r"statutes:\s*\[(.*?)\]", inner, re.S)
        keys = re.findall(r'"([A-Za-z0-9_]+)"', sm.group(1)) if sm else []
        out.append({"id": pid, "kind": "legal", "body": "\n".join(texts),
                    "statutes": keys})

    declared = len(re.findall(r"^  [a-z_]+: \{$", body, re.M))
    if declared != len(out):
        sys.exit("⛔ PATHS 宣告 %d 筆，只解析出 %d 筆——有路線被靜默略過"
                 % (declared, len(out)))
    return out


def check_advisory(adv, keymap, corpus):
    """比對 advisory 散文與其**自己宣告**的條文。回傳 [(level, msg)]。"""
    from tools.check_prose_statutes import (
        coverage, norm as pnorm, numbers_of, legal_numbers_of,
        _PROVISO_RE, _XREF_RE)

    found = []

    # ⛔ body 是**純文字**渲染（AdvisoryCard 的 `{b}`），不吃 markdown。
    #    CLAUDE.md ⓭ 在 PR17 就記過這個坑，PR19 寫新文案時**還是踩了**
    #    ——畫面上真的印出了字面的「**不等於就沒事了**」。
    # ★ 結論：寫在文件裡不夠，得有東西守著。重複犯的錯要自動化掉。
    if _MARKDOWN_RE.search(adv["body"]):
        found.append(("PROBLEM",
                      "⛔ body 含 markdown 標記（%s）——AdvisoryCard 以純文字渲染，"
                      "會原樣印在畫面上給勞工看到"
                      % "、".join(sorted(set(_MARKDOWN_RE.findall(adv["body"]))))))

    # ⛔ 型別不變式：kind === "practice" 時 statutes 必須是空陣列。
    #    triageTree.ts 的註解聲稱「型別上就不可能掛法條」，但
    #    TypeScript 的 `kind: "legal" | "practice"` 配 `statutes: string[]`
    #    **並不會**強制這件事——它只是個約定。約定要有東西守著才算數。
    if adv["kind"] == "practice" and adv["statutes"]:
        found.append(("PROBLEM", "⛔ kind=\"practice\" 卻掛了法條 %s"
                      "——經驗談不該掛法條（會被敵意讀者抓來反打）" % adv["statutes"]))
    if adv["kind"] == "legal" and not adv["statutes"]:
        found.append(("PROBLEM", "⛔ kind=\"legal\" 卻沒有任何法條依據"))

    if not adv["statutes"]:
        return found

    n_body = pnorm(adv["body"])
    cited_nums, law_nums, laws = set(), set(), []
    quote_nums = set()          # ★ 畫面上**實際顯示**的引文裡的數字
    missing_keys = []
    unresolved = False
    for k in adv["statutes"]:
        if k not in keymap:
            missing_keys.append(k)
            continue
        law, flno, quote = keymap[k]
        quote_nums |= legal_numbers_of(quote)
        # ⛔ 勞工自身的義務／限制：同一條裡課予勞工的部分，散文有沒有講
        for du in dict.fromkeys(_WORKER_DUTY_RE.findall(quote)):
            du_n = pnorm(_XREF_RE.sub("", du))
            if len(du_n) < 8:
                continue
            cov = coverage(du_n, n_body)
            if cov < 0.40:
                found.append(("PROBLEM",
                              "⛔ %s 的引文含**對勞工自己**的義務／限制，散文未提及"
                              "（4-gram %.0f%%）：「%s」" % (k, cov * 100, du[:58])))
        # ⛔ 誠實回報「比不了」，不要回報 ✅。
        #    但書／要件檢查都要先過「相關性門檻」（散文得與該條有字面重疊才算在談它），
        #    而 PATHS 的散文是**完全改寫的白話**，與法條幾乎零重疊
        #    → 所有檢查都被門檻擋掉 → 報表印出 ✅「未偵測到問題」。
        #    ★ 那是假的安心：根本沒檢查過，卻讓人以為查過了。
        #    沒檢查就說沒檢查——這比漏報更重要。
        # ★ 但「改寫」不等於「無從查核」。若散文與引文共用法律數字
        #   （散文寫「六十天」、法條寫「六十日」，正規化後都是 60日），
        #   那至少關鍵數字是對上的，算有錨點，不必要求人工重看。
        #   只有**字面無重疊且連一個共同數字都沒有**時，才是真的比不了。
        if quote:
            cov = coverage(pnorm(quote), n_body)
            shared = legal_numbers_of(quote) & legal_numbers_of(adv["body"])
            if cov < 0.15 and not shared:
                found.append(("WARN",
                              "⚠️ %s：散文與該條引文無字面重疊（4-gram %.0f%%）"
                              "且無共同數字可當錨點，本工具**無法自動比對**"
                              "——需人工確認語意是否吻合" % (k, cov * 100)))
        original = corpus.get((law, flno))
        if law not in laws:
            laws.append(law)
        if original is None:
            unresolved = True
            found.append(("SKIP", "－ 語料庫未收錄《%s》第 %s 條（%s）"
                                  "，**不等於通過**，須以 taiwan-law 覆核" % (law, flno, k)))
            continue
        clean = _PREFIX_RE.sub("", original, count=1)
        cited_nums |= legal_numbers_of(clean)

        # 但書逐「項」檢查 + 相關性門檻（與 check_prose_statutes 同一套理由：
        # 散文在講第 1 項，沒有義務複述第 3 項的除外規定）
        for p in [x for x in clean.split("\n") if len(pnorm(x)) > 5]:
            core = pnorm(_PROVISO_RE.sub("", p))
            if len(core) < 8 or coverage(core, n_body) < 0.25:
                continue
            for pv in dict.fromkeys(_PROVISO_RE.findall(p)):
                pv_n = pnorm(_XREF_RE.sub("", pv))
                if len(pv_n) < 8:
                    continue
                cov = coverage(pv_n, n_body)
                if cov < 0.40:
                    found.append(("PROBLEM",
                                  "⛔ %s 所述之該項含但書／除外規定而散文未涵蓋"
                                  "（4-gram %.0f%%）：「%s」" % (k, cov * 100, pv[:58])))

    for k in missing_keys:
        found.append(("PROBLEM", "⛔ statutes 列了 %s，但 STATUTES 裡沒有這個 key" % k))

    # 散文講了數字，但所引條文裡沒有 → 可能引用不足（漏列條號）或無法源
    # ⛔ 只在所引條文**全部都查得到**時才做這項：有任何一條語料庫沒收錄（如勞動事件法），
    #    比對基準就是殘缺的，據以報「查無法源」會是冤枉的假警報。
    #    查不到就說查不到（上面的 SKIP），不要假裝比對過。
    if unresolved:
        return found
    for law in laws:
        law_nums |= {n for (l, f), t in corpus.items() if l == law
                     for n in legal_numbers_of(_PREFIX_RE.sub("", t, count=1))}
    for n in sorted(legal_numbers_of(adv["body"])):
        if n in quote_nums:
            continue
        # ★ 分三級。關鍵在於區分「條對不對」與「**畫面上給勞工看的引文**撐不撐得住」：
        #   語料庫以「條」為單位，而 STATUTES 的 quote 往往只抄其中一「項」。
        #   勞工看到的是 quote，不是整條——quote 裡沒有的數字，對他而言就是沒有依據。
        if n in cited_nums:
            found.append(("PROBLEM",
                          "⛔ 散文的「%s」雖在所引之條文內，但**不在畫面顯示的引文**裡"
                          "——勞工看不到依據，請補一筆對應該「項」的 STATUTES" % n))
        elif n in law_nums:
            found.append(("PROBLEM", "⛔ 散文的「%s」不在所宣告的條文中，但存在於同法他條"
                                     "——**引用不足**，請把那一條列進 statutes" % n))
        else:
            found.append(("WARN", "⚠️ 散文的「%s」在所引法規中查無——請確認法源" % n))
    return found


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

    # ── advisory 散文 ──────────────────────────────────────
    keymap = parse_statute_keys()
    advisories = parse_advisories()
    print("=" * 72)
    print("【ADVISORIES 散文】直接印給勞工看的法律敘述（%d 筆）" % len(advisories))
    print("=" * 72)
    for adv in advisories:
        found = check_advisory(adv, keymap, corpus)
        worst = "OK"
        for lv, _ in found:
            if lv == "PROBLEM":
                worst = "PROBLEM"
            elif lv in ("WARN", "SKIP") and worst == "OK":
                worst = lv
        tally[worst] = tally.get(worst, 0) + 1
        icon = {"OK": "✅", "WARN": "⚠️ ", "PROBLEM": "⛔", "SKIP": "－"}[worst]
        print("%s %s（kind=%s，statutes=%s）"
              % (icon, adv["id"], adv["kind"], adv["statutes"] or "—"))
        if not found:
            print("   ✅ 未偵測到但書遺漏或引用不足")
        for lv, msg in found:
            print("   %s" % msg)
        print()

    # ── PATHS 散文 ─────────────────────────────────────────
    paths = parse_paths()
    print("=" * 72)
    print("【PATHS 散文】使用者據以決定「走哪條路」的敘述（%d 筆）" % len(paths))
    print("=" * 72)
    for p in paths:
        found = check_advisory(p, keymap, corpus)
        worst = "OK"
        for lv, _ in found:
            if lv == "PROBLEM":
                worst = "PROBLEM"
            elif lv in ("WARN", "SKIP") and worst == "OK":
                worst = lv
        tally[worst] = tally.get(worst, 0) + 1
        icon = {"OK": "✅", "WARN": "⚠️ ", "PROBLEM": "⛔", "SKIP": "－"}[worst]
        print("%s %s（statutes=%s）" % (icon, p["id"], p["statutes"] or "—"))
        if not found:
            print("   ✅ 未偵測到但書遺漏或引用不足")
        for lv, msg in found:
            print("   %s" % msg)
        print()

    print("── 統計 ──")
    for k in ("OK", "WARN", "PROBLEM", "SKIP"):
        if k in tally:
            print("  %-8s %d" % (k, tally[k]))
    print("\n⛔ SKIP 不等於通過。語料庫未收錄的法規仍須以 taiwan-law MCP 人工覆核。")
    return 1 if tally.get("PROBLEM") else 0


if __name__ == "__main__":
    sys.exit(main())
