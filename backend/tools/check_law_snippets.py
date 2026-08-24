# -*- coding: utf-8 -*-
"""check_law_snippets.py — 規則引擎引用條文 vs 法規原文 的自動比對（報表）

【為什麼需要這支】
PR14 發現 `rule_monthly_overtime` 引用勞基法 32 條 2 項時，snippet 只寫
「每月延長工時不得超過四十六小時。」——**漏掉同項但書**（經工會／勞資會議同意者為
54 小時、每三個月 138 小時），導致對已依但書取得同意之事業單位產生「假陽性」，
告訴勞工「你老闆疑似違法」而其實未必。

⛔ 這種錯的可怕之處在於：**「只抄一半」比「完全沒寫」危險**——
完全沒寫看得出來缺，抄一半的引用**看起來是完整的**，會一路被信任下去。
人工複查抓不到，因為讀的人不會每次都回去翻原文。

★ 而本專案手上就有 ground truth：`data/raw_chunks_cache.json`（1782 chunks 法規原文）。
   本檔把 `labor_rules.py` 裡每一個 `_ref()` / `_ref_rule()` 的 snippet
   拿去跟原文自動比對。

【四項檢查】
  A 條號存在   語料庫查無該條 → 可能條號寫錯（⛔ 最嚴重，客觀可判）
  B 逐字相符   snippet 是否為原文之逐字片段（✅ 最理想）
  C 數字遺漏   snippet 所對應之「項」中出現的數字，snippet 有沒有漏（⛔ 抓「抄一半」主力）
  D 但書遺漏   該項含「但…」「不在此限」而 snippet 未提及（⛔ PR14 那個錯）

⛔ 設計決定：**本檔輸出報表，不做 pass/fail**（與 tests/ 的硬性測試分工）。
   因為「改寫得恰不恰當」需要人判斷；硬性 fail 只會逼人把白名單塞滿而失去意義。
   ⚠️ 唯一例外是檢查 A（條號不存在），那是客觀事實，已另外寫成 pytest。

用法：
    cd backend
    PYTHONIOENCODING=utf-8 python -m tools.check_law_snippets
    PYTHONIOENCODING=utf-8 python -m tools.check_law_snippets --only-problems
"""
import argparse
import ast
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(BASE, "data", "raw_chunks_cache.json")
RULES = os.path.join(BASE, "domain", "rule_engine", "labor_rules.py")

# _ref → 勞動基準法；_ref_rule → 勞動基準法施行細則
PCODE_OF = {"_ref": "N0030001", "_ref_rule": "N0030002"}
LAW_NAME = {"N0030001": "勞動基準法", "N0030002": "勞基法施行細則"}

CJK_NUM = "〇零一二三四五六七八九十百千萬兩"
_NUM_RE = re.compile(r"[0-9]+|[%s]{1,6}" % CJK_NUM)
_PROVISO_RE = re.compile(r"但[^。；]*|不在此限")
# 條號／項款交叉引用（「第三十六條」「第二項」）——指路用，不是實質數字
_XREF_RE = re.compile(r"第[0-9%s]{1,6}[條項款目]" % CJK_NUM)


def norm(s: str) -> str:
    """NFKC 正規化並移除空白與標點。⛔ 原文與 snippet 都要走這裡（雙邊一致）。"""
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[\s，。；：、（）()「」『』]", "", s)


# ── 1. 從原始碼靜態取出所有引用（含所有分支，跑規則抓不到冷門分支）──
def extract_refs(path: str):
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    consts = {}          # 模組層級的字串常數（如 _OT_SNIPPET）
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
        # 支援以字串串接寫成的常數
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.JoinedStr):
            pass

    def literal(n):
        """把參數節點還原成字串；支援常數名、隱含字串串接。"""
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return n.value
        if isinstance(n, ast.Name) and n.id in consts:
            return consts[n.id]
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            a, b = literal(n.left), literal(n.right)
            return (a or "") + (b or "") if (a is not None or b is not None) else None
        return None

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in PCODE_OF and len(node.args) >= 3:
            art, title, snip = (literal(a) for a in node.args[:3])
            if art is None or snip is None:
                out.append({"fn": node.func.id, "line": node.lineno, "dynamic": True,
                            "article": art, "title": title, "snippet": snip})
                continue
            out.append({"fn": node.func.id, "line": node.lineno, "dynamic": False,
                        "article": art.strip(), "title": title, "snippet": snip})
    return out


# ── 2. 讀語料庫，建 (pcode, flno) → 原文 ──
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
        pcode, flno = meta.get("pcode"), str(meta.get("flno", ""))
        if not pcode or not flno:
            continue
        # 同條可能被切成多個 chunk，串起來
        idx.setdefault((pcode, flno), []).append(r.get("text", ""))
    return {k: "\n".join(v) for k, v in idx.items()}


# 語料庫每條原文開頭是「勞基法第 24 條：」，該條號會被當成數字造成假警報，先剝掉
_PREFIX_RE = re.compile("^[^：:" + chr(92) + "n]{0,20}第" + r"\s*[0-9]+(?:\s*之\s*[0-9]+)?\s*條[：:]")


def strip_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text or "", count=1)


def best_paragraph(original: str, snippet: str):
    """找出 snippet 最可能對應的「項」（原文以換行分項），用字元重疊率挑。

    ★ 這一步是精確度的關鍵：拿整條（可能 400 字、含五、六項）去比數字，
      會產生大量雜訊；鎖定到「項」才問得出「這一項裡的數字你漏了沒」。
    """
    paras = [p for p in original.split("\n") if len(norm(p)) > 5]
    if not paras:
        return original
    ns = set(norm(snippet))
    if not ns:
        return paras[0]
    return max(paras, key=lambda p: len(ns & set(norm(p))) / max(len(ns), 1))


def check_one(ref, corpus):
    pcode = PCODE_OF[ref["fn"]]
    flno = re.sub(r"[^0-9\-之]", "", ref["article"] or "")
    flno = flno.replace("之", "-")
    original = corpus.get((pcode, flno))
    issues = []

    if ref["dynamic"]:
        return {"level": "SKIP", "issues": ["參數非字面字串，無法靜態解析"],
                "flno": flno, "original": None, "para": None}

    # A 條號存在
    if not original:
        return {"level": "ERROR", "issues": ["⛔ 語料庫查無此條（條號可能寫錯，或該法未收錄）"],
                "flno": flno, "original": None, "para": None}

    para = strip_prefix(best_paragraph(original, ref["snippet"]))
    n_snip, n_all = norm(ref["snippet"]), norm(original)

    # B 逐字相符
    verbatim = n_snip in n_all
    if verbatim:
        return {"level": "OK", "issues": ["✅ 逐字相符"], "flno": flno,
                "original": original, "para": para}

    # C 數字遺漏（只比對所對應之「項」）
    # ⚠️ 先剝掉「第三十六條」這類**條號交叉引用**——那是指路，不是實質數字。
    #    不剝掉會把「第三十六條所定休息日」的三十六當成漏抄，報表就會狼來了。
    body = _XREF_RE.sub("", para)
    nums_para = [m for m in _NUM_RE.findall(body)
                 if len(m) > 1 or m not in "一二三四五六七八九十"]
    missing_nums = [n for n in dict.fromkeys(nums_para) if norm(n) not in n_snip]
    if missing_nums:
        issues.append("⛔ 該項出現而 snippet 未提及之數字：" + "、".join(missing_nums))

    # D 但書遺漏
    # ⚠️ 不能只看有沒有「但」字——snippet 可能把但書「改寫」進去而未用該字
    #    （40 條那筆即如此）。改看**但書的實質內容**有沒有被涵蓋。
    for pv in _PROVISO_RE.findall(para):
        pv_n = norm(_XREF_RE.sub("", pv))
        if len(pv_n) < 6:
            continue
        covered = len(set(pv_n) & set(n_snip)) / len(set(pv_n))
        if covered < 0.6:
            issues.append("⛔ 該項含但書／除外規定，snippet 未涵蓋其內容（字元涵蓋率 %.0f%%）：「%s」"
                          % (covered * 100, pv[:44]))
            break

    if not issues:
        issues.append("⚠️ 非逐字（屬改寫），但未偵測到數字或但書遺漏——仍請人工確認語意")
        level = "WARN"
    else:
        level = "PROBLEM"
    return {"level": level, "issues": issues, "flno": flno,
            "original": original, "para": para}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-problems", action="store_true", help="只列出有問題的")
    a = ap.parse_args()

    corpus = load_corpus()
    refs = extract_refs(RULES)
    print("語料庫條文數：%d　│　labor_rules.py 引用數：%d\n" % (len(corpus), len(refs)))

    tally = {}
    for ref in refs:
        r = check_one(ref, corpus)
        tally[r["level"]] = tally.get(r["level"], 0) + 1
        if a.only_problems and r["level"] in ("OK", "WARN"):
            continue
        head = "%s  L%-4d %s第 %s 條" % (
            {"OK": "✅", "WARN": "⚠️ ", "PROBLEM": "⛔", "ERROR": "🔴", "SKIP": "－"}[r["level"]],
            ref["line"], LAW_NAME[PCODE_OF[ref["fn"]]], r["flno"])
        print(head)
        print("      snippet：%s" % (ref["snippet"] or "")[:100])
        for i in r["issues"]:
            print("      %s" % i)
        if r["level"] == "PROBLEM" and r["para"]:
            print("      原文該項：%s" % r["para"][:160])
        print()

    print("── 統計 ──")
    for k in ("OK", "WARN", "PROBLEM", "ERROR", "SKIP"):
        if k in tally:
            print("  %-8s %d" % (k, tally[k]))
    print("\n⛔ 以上為報表，非 pass/fail。「改寫得恰不恰當」需人工判斷；")
    print("   唯『條號不存在』屬客觀事實，已另寫成 pytest 硬性檢查。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
