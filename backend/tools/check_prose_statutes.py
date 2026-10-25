# -*- coding: utf-8 -*-
"""check_prose_statutes.py — 提示詞「散文」法律敘述 vs 法規原文 的自動比對（報表）

【為什麼需要這支（PR15／PR16／PR17 連續三次掛著的缺口）】
既有兩支檢核工具掃的都是**結構化引用**：
  - `check_law_snippets.py`      → `labor_rules.py` 的 `_ref(條號, 標題, snippet)`
  - `check_frontend_statutes.py` → `triageTree.ts` 的 `STATUTES` 常數
但**真正直接送到使用者眼前（或送進 ChatGPT 嘴裡）的法律敘述不在那裡**，而在提示詞的散文裡：
  - `domain/rag/answer_generator.py` 的 `SYSTEM_PROMPT`（私人版，Gemini 照著回答）
  - `frontend/lib/promptTemplate.ts` 的 `SYSTEM_ROLE`（開源版，使用者複製去貼 ChatGPT）

⛔ 這塊的風險比結構化引用**更高**，原因有三：
  1. 散文沒有 snippet 欄位可以逐字比對，寫錯不會有人發現；
  2. 它是**給 LLM 的指令**——LLM 會把它當權威事實照著展開，錯誤會被放大成一整篇回答；
  3. 開源版那份是**公開給所有勞工**的，而它的法律要件寫得比私人版更簡略。

★ ground truth 同樣是 `data/raw_chunks_cache.json`（1782 chunks 法規原文）。

【散文檢核特有的難題：文白數字不同形】
結構化 snippet 是手抄法條，用的是中文數字（「四十六小時」），
而散文是白話，用阿拉伯數字（「46 小時」「7 日」「3 年」）。
⛔ 直接做字串比對會**全部報漏抄**，報表瞬間失去意義。
→ 本檔實作 `cjk_to_int()`，把兩邊的數字一律正規化成整數集合再比。

【五項檢查】
  A 條號存在     語料庫查無該條 → 條號或法規引錯（⛔ 客觀可判，另有 pytest）
  B 數字不符     敘述中的數字在被引條文中找不到（⛔ 抓「編造／記錯數字」）
  C 但書遺漏     被引之「項」含但書而敘述未涵蓋（⛔ 抓 PR14 那種「抄一半」）
  D 要件遺漏     被引之「項」的合法化要件（經○○同意／指定、應報備查）未被提及
                 （⛔ 本檔新增，散文最容易漏的就是這個——見下）
  E 無出處數字   數字型法律斷言但整句沒有任何條號（⚠️ 違反「查不到原文就不引」）

★ 檢查 D 是本檔存在的主要理由。散文為了好讀會把「A 且 B 且 C 才可以」
  壓縮成「有 A 就可以」，而**漏掉的要件通常正是保護勞工的那道關卡**。
  這種錯 `check_law_snippets` 抓不到（它只比數字與但書），人工也抓不到
  （讀起來很順、很專業），但後果是 AI 對勞工說「你老闆這樣做是合法的」。

⛔ 設計決定（沿用 `check_law_snippets.py`）：**本檔輸出報表，不做 pass/fail**。
   「散文改寫得恰不恰當」需要人判斷。唯檢查 A 屬客觀事實，另寫成 pytest 硬性檢查。

用法：
    cd backend
    PYTHONIOENCODING=utf-8 python -m tools.check_prose_statutes
    PYTHONIOENCODING=utf-8 python -m tools.check_prose_statutes --only-problems
    PYTHONIOENCODING=utf-8 python -m tools.check_prose_statutes --show-original
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
BACKEND_PROMPT = os.path.join(BASE, "domain", "rag", "answer_generator.py")
FRONTEND_PROMPT = os.path.normpath(
    os.path.join(BASE, "..", "frontend", "lib", "promptTemplate.ts"))

# ── 法規名 → pcode。⛔ 別名要收齊：散文會用口語簡稱（「勞基法」「職安法」）──
#    ⚠️ 順序有意義：長別名必須排在短別名之前，否則「勞動基準法施行細則」
#       會先被「勞動基準法」吃掉，比到錯的法規。
LAW_ALIASES = [
    ("勞動基準法施行細則", "N0030002"),
    ("勞基法施行細則", "N0030002"),
    ("勞動基準法", "N0030001"),
    ("勞基法", "N0030001"),
    ("職業安全衛生法", "N0060001"),
    ("職安法", "N0060001"),
    ("職場霸凌防治措施準則", "N0060085"),
    ("勞資爭議處理法", "N0050001"),
    ("就業保險法", "N0050021"),
    ("性別平等工作法", "N0030014"),
    ("勞工退休金條例", "N0030020"),
    ("最低工資法", "N0030037"),
]
# 散文寫「第 36 條」而通篇未提法規名時的推定法規。本專案主體是勞基法。
PRESUMED_LAW = "N0030001"
LAW_NAME = {
    "N0030001": "勞動基準法", "N0030002": "勞基法施行細則",
    "N0060001": "職業安全衛生法", "N0060085": "職場霸凌防治措施準則",
    "N0050001": "勞資爭議處理法", "N0050021": "就業保險法",
    "N0030014": "性別平等工作法", "N0030020": "勞工退休金條例",
    "N0030037": "最低工資法",
}

CJK_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CJK_UNIT = {"十": 10, "百": 100, "千": 1000, "萬": 10000}
CJK_NUM = "".join(CJK_DIGIT) + "".join(CJK_UNIT)

# 條號／項款交叉引用——指路用，不是實質數字（PR15 的教訓：不剝掉報表會狼來了）
# ⚠️ 必須同時吃下「第 22-1~22-3 條」這種**範圍引用**：條號只出現在尾端，
#    若只比對單一條號，「22-1」會被留下來當成實質數字 22 與 1。
# ⚠️ 三種寫法都要吃下，否則殘留的條號會被當成實質數字：
#    「第 22-1 條」單一／「第 22-1~22-3 條」範圍／「第 4、5 項」頓號列舉。
_XREF_NUM = r"[0-9%s]{1,6}(?:\s*[之\-－]\s*[0-9%s]{1,3})?" % (CJK_NUM, CJK_NUM)
_XREF_RE = re.compile(
    r"第\s*%s(?:\s*[、,，]\s*%s)*"
    r"(?:\s*[~～至]\s*%s)?"
    r"\s*[條項款目](?:之[0-9%s]{1,3})?"
    % (_XREF_NUM, _XREF_NUM, _XREF_NUM, CJK_NUM))
# 清單編號（「7. 職場霸凌問題」「二、依第三十條…」）——排版用，不是法律數字
_LIST_NO_RE = re.compile(r"^\s*(?:[0-9]{1,2}[.、)）]|[%s]{1,3}[、.]|[（(][0-9%s]{1,3}[）)])"
                         % (CJK_NUM, CJK_NUM))
# 日期（「2026 年 7 月 1 日」）——屬「施行日期」，不會寫在條文本文裡，排除以免假警報。
# ⚠️ 必須整組剝掉而非只剝年份：留下「7 月 1 日」會被當成「7 月」「1 日」兩個法律數字。
_DATE_RE = re.compile(r"(?:民國\s*)?[0-9]{2,4}\s*年(?:\s*[0-9]{1,2}\s*月)?(?:\s*[0-9]{1,2}\s*日)?")
# 分數（「三分之二」「二分之一」）要整組處理，否則會被拆成兩個無意義的數字
_FRAC_RE = re.compile(r"[0-9%s]{1,4}分之[0-9%s]{1,4}" % (CJK_NUM, CJK_NUM))
# 但書／除外規定。⚠️ 「但」後緊接「書」者要排除——法條裡的
#   「依本法第三十四條第二項**但書**規定變更…」是交叉引用，不是本條的但書，
#   誤抓會要求敘述去複述別條的除外規定（假警報）。
_PROVISO_RE = re.compile(r"但(?!書)[^。；\n]*|不在此限")
# 合法化要件：「經○○同意／指定／核准／公告」「應報○○備查」
_REQ_RE = re.compile(
    r"經[^，。；\n]{2,30}?(?:同意|指定|核准|公告|許可|商請)"
    r"|應報[^，。；\n]{0,24}?備查"
    r"|報[^，。；\n]{0,16}?主管機關備查")
# 許可型敘述的標記——「可以／得／不受限制」。檢查 D 只對這類句子啟動，
# 因為法律的許可幾乎都附條件，而散文最容易漏掉的就是那些條件。
# ⚠️ 只收**法律授權語氣**的詞。曾收過「可再」「可在」，結果
#    「規定略有差異，可再告知我細節」這種純對話句被判為許可型，
#    然後要求它複述變形工時要件——假警報。日常語氣的「可」不算。
_PERMISSIVE_RE = re.compile(
    r"可以|可不經|可逕|得(?:以|將|不|於|逕)|彈性調整|挪動|不受[^，。；\n]{0,12}限制"
    r"|屬合法|是合法|為合法|允許|沒問題")
# 法律數字單位——出現這些單位的數字才算「法律斷言」，排除「第 4 點」這種編號
_LEGAL_UNIT = r"(?:小時|日|天|週|月|年|人|倍|元|%|％|分之)"
_LEGAL_NUM_RE = re.compile(r"(?:[0-9]+|[%s]{1,6})\s*%s" % (CJK_NUM, _LEGAL_UNIT))

# 語料庫每條原文開頭是「勞基法第 24 條：」，該條號會被當成數字，先剝掉
_PREFIX_RE = re.compile(r"^[^：:\n]{0,20}第\s*[0-9]+(?:\s*之\s*[0-9]+)?\s*條[：:]")


def norm(s: str) -> str:
    """NFKC 正規化並移除空白標點。⛔ 原文與敘述都要走這裡（雙邊一致）。"""
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[\s，。；：、（）()「」『』【】\[\]*#]", "", s)


def shingles(s: str, n: int = 4) -> set:
    """字元 n-gram 集合。短於 n 時退回整串。"""
    s = s or ""
    if len(s) <= n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def coverage(needle: str, haystack: str) -> float:
    """needle 的實質內容有多少比例出現在 haystack 中（4-gram 重疊率）。

    ⛔ 不用「字元集合交集」——那是本檔第二版的做法，在區塊變大後就失效了：
       一段兩百字的敘述幾乎必然包含任何但書的每一個「單字」，涵蓋率會虛高到 90%+，
       真的漏抄但書也不會被抓到（假陰性，比假警報更危險）。
    ★ 4-gram 要求的是「連續四字一致」，長度不會讓它虛高：
      逐字寫了 → 接近 1.0；完全沒寫 → 接近 0。實測間隔極為乾淨。
    """
    ns = shingles(needle)
    if not ns:
        return 1.0
    return len(ns & shingles(haystack)) / len(ns)


# 否定詞——「也不會因為是時薪就可以挪例假」這種句子雖然有「可以」，
# 語意是**否認**該許可，不該要求它複述要件。
_NEG_RE = re.compile(r"[不非未勿毋]")


def is_permissive(claim: str) -> bool:
    """是否為「許可型」敘述（檢查 D 的啟動條件），已排除被否定者。"""
    for m in _PERMISSIVE_RE.finditer(claim):
        if not _NEG_RE.search(claim[max(0, m.start() - 12):m.start()]):
            return True
    return False


def cjk_to_int(s: str):
    """中文數字 → 整數。支援 十二→12、四十六→46、一百三十八→138。

    ★ 這是本檔的核心：法條寫「四十六小時」，提示詞寫「46 小時」，
      不正規化就無法比對，報表會把每一筆都報成漏抄。
    """
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = section = number = 0
    for ch in s:
        if ch in CJK_DIGIT:
            number = CJK_DIGIT[ch]
        elif ch in CJK_UNIT:
            unit = CJK_UNIT[ch]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section = number = 0
            else:
                section += (number or 1) * unit
                number = 0
        else:
            return None          # 混進非數字字元，放棄（交給字串比對）
    return total + section + number


# 數字 + 單位。★ 必須連單位一起比，否則分不出「十二小時」與「12 日」——
#   「不得連續工作超過 12 日」這句在勞基法毫無法源，但數字 12 以
#   「一日不得超過十二小時」的形式出現在 32 條，純比數字會誤判為「出自他條」而放過。
_UNIT_CANON = {"天": "日", "星期": "週", "個月": "月", "％": "%"}
_NUM_UNIT_RE = re.compile(
    r"([0-9]+|[%s]{1,6})\s*(小時|日|天|週|星期|個月|月|年|人|倍|元|%%|％)" % CJK_NUM)


def numbers_of(text: str) -> set:
    """取出一段文字中的「實質數字」集合，已剝交叉引用、已正規化。

    回傳元素為字串，三種形態：
      「46小時」 數字帶單位（主力；文白一律正規化成阿拉伯數字 + 統一單位）
      「2/3」    分數（分子分母拆開後毫無意義，整組保留）
      「5」      無單位的裸數字

    ⛔ 剝除順序有意義，三者都是前幾版報表狼來了的原因：
       清單編號 → 日期 → 交叉引用。先剝編號才不會把「7. 職場霸凌」的 7 當成 7 日。
    """
    t = unicodedata.normalize("NFKC", text or "")
    t = _LIST_NO_RE.sub("", t)          # 「7.」「二、」
    t = _DATE_RE.sub("", t)             # 「2026 年 7 月 1 日」
    t = _XREF_RE.sub("", t)             # 「第 22-1~22-3 條」
    out = set()

    for f in _FRAC_RE.findall(t):
        a, b = f.split("分之")
        ia, ib = cjk_to_int(a), cjk_to_int(b)
        if ia and ib:
            out.add("%d/%d" % (ib, ia))      # 「三分之二」→ 2/3（分子在前）
    t = _FRAC_RE.sub("", t)

    for num, unit in _NUM_UNIT_RE.findall(t):
        v = cjk_to_int(num)
        if v is not None and v > 0:
            out.add("%d%s" % (v, _UNIT_CANON.get(unit, unit)))
    t = _NUM_UNIT_RE.sub("", t)          # 已帶單位者不再以裸數字重複計入

    for m in re.findall(r"[0-9]+|[%s]{1,6}" % CJK_NUM, t):
        v = cjk_to_int(m)
        if v is not None and v > 0:
            out.add(str(v))
    return out


def legal_numbers_of(text: str) -> set:
    """只取**帶單位**的數字（與分數）。

    ⛔ 散文裡的裸數字幾乎都不是法律主張：圈號「①②③」經 NFKC 會變成 1、2、3，
       「兩個可以一起用」的「兩」「一」也會被撿進來。拿這些去比對法條，
       報表會被「散文的『1』不在所引條文中」這種廢話灌滿。
    ★ 反過來說，散文裡真正的法律斷言幾乎必然帶單位
      （十日、六十日、二倍、三十人、四十八小時），所以用「有沒有單位」
      當過濾條件既簡單又站得住。
    """
    return {n for n in numbers_of(text) if not n.isdigit()}


# ── 1. 抽出散文來源 ──────────────────────────────────────────────
def extract_backend_prose():
    """從 answer_generator.py 以 AST 取出模組層級的字串常數（SYSTEM_PROMPT 等）。"""
    src = open(BACKEND_PROMPT, encoding="utf-8").read()
    tree = ast.parse(src, BACKEND_PROMPT)
    out = []
    declared = 0
    for node in tree.body:                      # 只看模組層級，不進函數
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and len(node.value.value) > 80:
            declared += 1
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.append(("answer_generator.py", t.id,
                                node.lineno, node.value.value))
    if declared != len(out):                    # 涵蓋率自檢（PR17 教訓）
        print("🔴 answer_generator.py 符合條件 %d 筆，僅取出 %d 筆"
              % (declared, len(out)), file=sys.stderr)
        sys.exit(2)
    return out


def extract_frontend_prose():
    """從 promptTemplate.ts 以正則取出 template literal 常數。

    ⚠️ 不用完整 TS parser：這裡只需要模組層級的 const X = `...`，
       正則足夠且不必為專案引入 node 依賴。
    ⛔ 但要自檢涵蓋率——PR17 的教訓：檢查工具自己漏檢，而且不會報錯。
       宣告筆數 ≠ 解析筆數就直接 exit 2，不容許靜默略過。
    """
    src = open(FRONTEND_PROMPT, encoding="utf-8").read()
    decl_re = re.compile(r"^const\s+([A-Z][A-Z0-9_]*)\s*=\s*`", re.M)
    declared = {m.group(1) for m in decl_re.finditer(src)}
    out, parsed = [], set()
    for m in re.finditer(r"^const\s+([A-Z][A-Z0-9_]*)\s*=\s*`([^`]*)`", src, re.M):
        name, body = m.group(1), m.group(2)
        parsed.add(name)
        if len(body) > 80:
            out.append(("promptTemplate.ts", name,
                        src[:m.start()].count("\n") + 1, body))
    if declared != parsed:
        print("🔴 promptTemplate.ts 宣告 %s，僅解析 %s —— 有常數被靜默略過"
              % (sorted(declared), sorted(parsed)), file=sys.stderr)
        sys.exit(2)
    return out


# ── 2. 讀語料庫（與 check_law_snippets.py 同邏輯）────────────────
def load_corpus():
    data = json.load(open(CORPUS, encoding="utf-8"))
    idx = {}
    for r in data:
        if r.get("doc_type") not in ("statute", "enforcement_rule"):
            continue
        meta = r.get("metadata")
        if isinstance(meta, str):
            try:
                meta = ast.literal_eval(meta)
            except Exception:
                meta = {}
        if not isinstance(meta, dict):
            continue
        pcode, flno = meta.get("pcode"), str(meta.get("flno", ""))
        if not pcode or not flno:
            continue
        idx.setdefault((pcode, flno), []).append(r.get("text", ""))
    by_article = {k: "\n".join(v) for k, v in idx.items()}
    # 同法全文索引：供檢查 B 區分「數字出自同法他條」與「全法皆無」
    by_law = {}
    for (pcode, _flno), txt in by_article.items():
        by_law.setdefault(pcode, []).append(txt)
    return by_article, {k: "\n".join(v) for k, v in by_law.items()}


# ── 3. 把散文切成「法律主張單元」並找出其引用 ────────────────────
# 條號：支援「第 22-1 條」「第 22-1~22-3 條」「第 30 條之 1」
_ART_RE = re.compile(
    r"第\s*(\d+(?:\s*[-－之]\s*\d+)?)\s*(?:[~～至]\s*(\d+(?:\s*[-－之]\s*\d+)?)\s*)?條")


def split_claims(text: str):
    """切成主張單元：以換行與句號切，保留行號以便回報位置。

    ⚠️ 不用更細的切法（如逗號）——法律要件常跨逗號，切太碎會讓
       「經 A 同意，且經 B 指定」被拆成兩個互不相干的單元，涵蓋率檢查就廢了。

    ⛔ 反過來切太碎更糟，第一版與第二版各踩了一次，而且**都是假警報**：
       1. 第一版逐行切：提示詞寫成「5. 職場霸凌問題：…（第 22-1~22-3 條）：」+ 下面的子項，
          條號在標題行、實質內容在子項，標題行被判定「引了 22-1 卻沒寫但書」。
       2. 第二版改成「冒號標題 + 子項」併為一塊，但標題以「。」收尾的那些還是散開；
          而且句號切分會把「…一年內申訴。但依前款規定有較長申訴期限者，從其規定。」
          **從句號處剖成兩半**，後半的但書明明寫了，卻被報成漏抄。

    ★ 第三版改為**以「編號項」為單位**（「6.」「7.」… 直到下一個編號項）。
      這才對應散文實際的組織方式，也對應法律現實：一個編號項 = 一個完整的法律主張，
      它的要件與但書本來就會分散在該項的數行之內。
      ⚠️ 代價是區塊變大、定位變粗（只回報該項起始行）。這個交換是划算的——
         一份會亂叫的報表等於沒有報表，而定位粗一點人還是找得到。
      ⛔ 但區塊變大會讓「字元集合涵蓋率」失效（長文幾乎必然包含所有單字），
         故涵蓋率一律改用 4-gram（見 `coverage()`）。
    """
    raw = text.split("\n")
    # 頂層編號項：行首（容許少量縮排）的「6.」「6、」
    top = re.compile(r"^\s{0,2}\d{1,2}[.、]")
    heads = [i for i, ln in enumerate(raw) if top.match(ln)]
    bounds = heads + [len(raw)]

    blocks = []
    if heads and heads[0] > 0:                       # 第一個編號項之前的前言
        blocks.append((1, "\n".join(raw[:heads[0]])))
    if not heads:
        blocks.append((1, text))
    for k, start in enumerate(heads):
        blocks.append((start + 1, "\n".join(raw[start:bounds[k + 1]])))

    claims = []
    for line_no, block in blocks:
        b = block.strip()
        if len(b) > 6:
            claims.append((line_no, b))
    return claims


def _canon_art(s: str) -> str:
    """「22 之 1」「22－1」→「22-1」。"""
    return re.sub(r"\s", "", s).replace("之", "-").replace("－", "-")


def find_citations(claim: str, carry_law):
    """找出主張中的法規引用。回傳 ([(pcode, flno, inferred)], 更新後的 carry_law)。

    `carry_law` 是同一常數內前文提過的法規——散文常寫「第 22-2 條（雇主…）」
    而省略法規名，沿用前文是正確解讀。

    ⛔ `inferred=True` 表示**整個常數內都沒出現過法規名**，是本檔推定為勞基法的。
       第一版遇到這種情形直接跳過不檢查，結果漏掉了開源版提示詞那條
       「第 36 條 … 若雇主有報備變形工時，例假位置可在 7 日內彈性調整」
       ——那是公開給所有勞工的版本，法律要件漏得比私人版更多，卻因為少寫三個字
       （「勞基法」）而逃過檢核。**沉默略過比報錯危險**，故改為推定後照常檢查，
       並另外把「未指明法規名」本身列為一項發現（LLM 同樣會猜，而且可能猜錯）。

    ⛔ 一個區塊可以引用**多部**法規，必須逐條號各自認祖歸宗。
       本檔有一版是「整個區塊取位置最前的法規名」，結果一段同時寫了
       「勞基法第 30 條……勞基法施行細則第 22-3 條」時，後者被判成
       「勞動基準法第 22-3 條」（該條不存在）而報 ERROR。
    ★ 正確規則是法律散文的實際讀法：**每個條號取其最近的前方法規名**。
    """
    # 1. 掃出所有法規名出現位置。同一位置上長別名優先
    #    （「勞基法施行細則」必須贏過「勞基法」，否則施行細則會被當成本法）。
    # ⛔ 只採「引用前綴」——法規名之後必須緊接條號才算。
    #    否則「…第 22-3 條（申訴管道）與《職場霸凌防治措施準則》。」句末那個
    #    **順帶提及**的法規名，會被下一行的裸條號「第 22-1 條」當成所屬法規，
    #    於是去查「職場霸凌防治措施準則第 22-1 條」（不存在）而報 ERROR。
    #    順帶提及 ≠ 引用，不該改變上下文。
    marks = []                                # [(pos, pcode, len(alias))]
    for alias, pcode in LAW_ALIASES:
        for m in re.finditer(re.escape(alias), claim):
            tail = claim[m.end():m.end() + 12]
            if not re.match(r"\s*[之第]?\s*第?\s*[0-9%s]" % CJK_NUM, tail):
                continue                      # 非引用前綴，略過
            marks.append((m.start(), pcode, len(alias)))
    marks.sort(key=lambda x: (x[0], -x[2]))
    pruned, seen_at = [], {}
    for pos, pcode, ln in marks:
        if seen_at.get(pos) is None:
            seen_at[pos] = ln
            pruned.append((pos, pcode))
    marks = pruned

    def law_for(at: int):
        """取 at 之前最近的法規名；沒有則沿用前文，再沒有則推定。"""
        best = None
        for pos, pcode in marks:
            if pos <= at:
                best = pcode
            else:
                break
        if best:
            return best, False
        if carry_law:
            return carry_law, False
        return PRESUMED_LAW, True

    out = []
    for m in _ART_RE.finditer(claim):
        law, inferred = law_for(m.start())
        a = _canon_art(m.group(1))
        out.append((law, a, inferred))
        if m.group(2):                        # 範圍引用「22-1~22-3」：展開
            b = _canon_art(m.group(2))
            out.append((law, b, inferred))
            ma, mb = re.match(r"(\d+)-(\d+)$", a), re.match(r"(\d+)-(\d+)$", b)
            if ma and mb and ma.group(1) == mb.group(1):
                for k in range(int(ma.group(2)) + 1, int(mb.group(2))):
                    out.append((law, "%s-%d" % (ma.group(1), k), inferred))
    # 區塊內最後出現的法規名才是下一區塊的 carry（推定值不該污染後續主張）
    next_carry = marks[-1][1] if marks else carry_law
    return list(dict.fromkeys(out)), next_carry


def strip_prefix(t):
    return _PREFIX_RE.sub("", t or "", count=1)


def best_paragraph(original: str, claim: str) -> str:
    """找出主張最可能對應的「項」（原文以換行分項）。

    ★ 與 check_law_snippets 同理：拿整條（可能六、七項）去比，雜訊會蓋掉訊號。
      但散文用白話，字元重疊率較低，故**同時以數字集合的交集**加權。
    """
    paras = [p for p in original.split("\n") if len(norm(p)) > 5]
    if not paras:
        return strip_prefix(original)
    nc, numc = set(norm(claim)), numbers_of(claim)

    def score(p):
        np_ = set(norm(strip_prefix(p)))
        char = len(nc & np_) / max(len(nc), 1)
        num = len(numc & numbers_of(p)) / max(len(numc), 1) if numc else 0
        return char + num                     # 數字命中是強訊號，等權加上
    return strip_prefix(max(paras, key=score))


def check_block_numbers(claim: str, cites, by_article: dict, by_law: dict):
    """檢查 B：敘述中的數字有沒有法源。★ 以「區塊」為單位，不逐條。

    ⛔ 為什麼不能逐條：一個編號項常同時引用數條（例如同時講第 30 條與第 36 條），
       各自引用的數字散落兩邊。若逐條問「這個數字在本條嗎」，比對第 30 條時
       會把所有屬於第 36 條的數字全報一次，反之亦然——實測一個區塊可以噴出
       十幾筆這種交叉噪音，真正的訊號完全被埋掉。
    ★ 正確語意是：「這個區塊引用了這些條，區塊裡的數字應該在這些條之中找得到」。

    三級判定（嚴重度不同，不可混為一類）：
      在所引各條之中       → 通過
      只在同法他條         → WARN，建議補註正確條號
      該法全文均查無       → PROBLEM，此敘述疑無法源
    """
    cited_nums, law_nums, laws = set(), set(), []
    for pcode, flno, _inf in cites:
        txt = by_article.get((pcode, flno))
        if txt:
            cited_nums |= numbers_of(txt)
        if pcode not in laws:
            laws.append(pcode)
            law_nums |= numbers_of(by_law.get(pcode, ""))

    hard, soft = [], []
    for n in sorted(numbers_of(claim)):
        if n in cited_nums:
            continue
        if n in law_nums:
            soft.append("⚠️ 數字「%s」不在所引條文中，但出現在同法他條"
                        "——建議補註正確條號" % n)
        else:
            hard.append("⛔ 數字「%s」在《%s》全文均查無——此敘述疑無法源"
                        % (n, "》《".join(LAW_NAME.get(p, p) for p in laws)))
    return hard, soft


def check_claim(claim: str, pcode: str, flno: str, by_article: dict, by_law: dict,
                inferred: bool = False):
    original = by_article.get((pcode, flno))
    issues, soft = [], []
    if inferred:
        soft.append("⚠️ 敘述只寫「第 %s 條」而通篇未指明法規名，本檔推定為《%s》"
                    "——LLM 同樣得靠猜，請在提示詞補上法規名" % (flno, LAW_NAME[pcode]))

    # A 條號存在
    if not original:
        return {"level": "ERROR", "para": None,
                "issues": ["⛔ 語料庫查無 %s第 %s 條（條號或法規可能引錯，"
                           "或該法未收錄→須以 taiwan-law MCP 覆核）"
                           % (LAW_NAME.get(pcode, pcode), flno)]}

    para = best_paragraph(original, claim)
    n_claim = norm(claim)

    # 整條逐字包含 → 最理想，直接過（先剝括號內的白話註解）
    if norm(re.sub(r"[（(][^）)]*[）)]", "", claim)) in norm(original):
        return {"level": "OK", "para": para, "issues": ["✅ 逐字相符"]}

    # ── C 但書遺漏 ────────────────────────────────────────────
    # ⚠️ 門檻 0.40（4-gram 重疊率）。白話散文不會照抄法律虛字（「從其規定」「依前款」），
    #    故不要求高重疊；但 4-gram 一旦逐字寫了就會接近 1.0，間隔很乾淨。
    #
    # ⛔ **但書逐「項」檢查，且須先過相關性門檻**——這點與檢查 D 相反，不可混用：
    #    但書是附麗於特定「項」的除外規定。敘述在講第 1 項，**沒有義務**複述
    #    第 3 項的「但因天災、事變或突發事件…」。
    #    本檔有一版把 C 也改成掃整條，結果每個引用 36 條的敘述都被報一次天災但書，
    #    九筆 PROBLEM 裡七筆是這種噪音——訊號完全被蓋掉。
    # ★ 相關性＝「該項本文（去但書後）有多少出現在敘述中」。
    #   敘述真的在談那一項，才要求它把那一項的但書講完。
    for p in [x for x in original.split("\n") if len(norm(x)) > 5]:
        body = norm(_PROVISO_RE.sub("", strip_prefix(p)))
        if len(body) < 8:
            continue
        if coverage(body, n_claim) < 0.25:        # 敘述沒在談這一項 → 不要求
            continue
        for pv in dict.fromkeys(_PROVISO_RE.findall(p)):
            pv_n = norm(_XREF_RE.sub("", pv))
            if len(pv_n) < 8:
                continue
            cov = coverage(pv_n, n_claim)
            if cov < 0.40:
                issues.append("⛔ 敘述所述之該項含但書／除外規定而未涵蓋其內容"
                              "（4-gram 涵蓋率 %.0f%%）：「%s」" % (cov * 100, pv[:60]))

    # ── D 要件遺漏 ★ 本檔存在的主要理由 ──────────────────────
    # ⛔ 只對「許可型敘述」做這項檢查，且掃**整條**而非僅最相近的那一項。
    #    兩個設計決定都是前一版失敗後改的：
    #    1. 只掃該項 → 「例假可彈性調整」比到的是 36 條 2 項 1 款（無要件），
    #       而要件其實在 4 項與 5 項，整個漏掉（假陰性，最不該發生的那種）。
    #    2. 不分敘述類型全掃 → 單純描述性的句子也被要求複述要件，報表會狼來了。
    #    ★ 聚焦「許可型」在實質上也正確：法律的許可幾乎都是附條件的，
    #      而被省略的條件**通常正是保護勞工的那道關卡**。
    if is_permissive(claim):
        for rq in dict.fromkeys(_REQ_RE.findall(original)):
            rq_n = norm(rq)
            if len(rq_n) < 5:
                continue
            cov = coverage(rq_n, n_claim)
            if cov < 0.40:
                issues.append("⛔ 敘述稱「得／可以」，但本條之合法化要件未被涵蓋"
                              "（4-gram 涵蓋率 %.0f%%）：「%s」" % (cov * 100, rq[:52]))

    if issues:
        return {"level": "PROBLEM", "para": para, "issues": issues + soft}
    if soft:
        return {"level": "WARN", "para": para, "issues": soft}
    return {"level": "WARN", "para": para,
            "issues": ["⚠️ 非逐字（屬改寫），未偵測到數字／但書／要件遺漏"
                       "——仍請人工確認語意"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-problems", action="store_true")
    ap.add_argument("--show-original", action="store_true",
                    help="PROBLEM 時印出法規原文該項全文")
    a = ap.parse_args()

    by_article, by_law = load_corpus()
    sources = extract_backend_prose() + extract_frontend_prose()
    print("語料庫條文數：%d（%d 部法規）　│　散文來源：%d 筆常數\n"
          % (len(by_article), len(by_law), len(sources)))

    tally = {}
    uncited = []
    for fname, const, base_line, text in sources:
        print("=" * 72)
        print("【%s】%s（L%d 起）" % (fname, const, base_line))
        print("=" * 72)
        carry = None
        shown = 0
        for off, claim in split_claims(text):
            cites, carry = find_citations(claim, carry)
            if not cites:
                if _LEGAL_NUM_RE.search(claim):      # E 無出處的法律數字
                    uncited.append((fname, const, base_line + off - 1, claim))
                continue

            # B 數字來源：以區塊為單位（見 check_block_numbers 的說明）
            hard, soft = check_block_numbers(claim, cites, by_article, by_law)
            if hard or (soft and not a.only_problems):
                lvl = "PROBLEM" if hard else "WARN"
                tally[lvl] = tally.get(lvl, 0) + 1
                print("%s  L%-4d 〔區塊數字來源〕%s"
                      % ("⛔" if hard else "WARN", base_line + off - 1,
                         "、".join("%s第 %s 條" % (LAW_NAME.get(p, p), f)
                                   for p, f, _ in cites)))
                for i in hard + soft:
                    print("      %s" % i)
                print()

            for pcode, flno, inferred in cites:
                r = check_claim(claim, pcode, flno, by_article, by_law, inferred)
                tally[r["level"]] = tally.get(r["level"], 0) + 1
                if a.only_problems and r["level"] in ("OK", "WARN"):
                    continue
                shown += 1
                print("%s  L%-4d %s第 %s 條"
                      % ({"OK": "OK ", "WARN": "WARN", "PROBLEM": "⛔",
                          "ERROR": "🔴"}[r["level"]],
                         base_line + off - 1, LAW_NAME.get(pcode, pcode), flno))
                print("      敘述：%s" % claim[:150])
                for i in r["issues"]:
                    print("      %s" % i)
                if r["level"] == "PROBLEM" and r["para"]:
                    cut = 600 if a.show_original else 200
                    print("      原文該項：%s" % r["para"][:cut])
                print()
        if shown == 0:
            print("（無符合列出條件者）\n")

    if uncited:
        print("=" * 72)
        print("【E 無出處的法律數字】數字型法律斷言，但整句未引任何條號")
        print("=" * 72)
        print("⚠️ 本專案鐵則是「查不到原文就不引」。以下敘述帶有法律效果的數字，")
        print("   卻沒有可回溯的條號——請補條號，或改寫成不帶數字的提示。\n")
        for fname, const, line, claim in uncited:
            print("WARN  %s %s L%d" % (fname, const, line))
            print("      %s\n" % claim[:170])

    print("=" * 72)
    print("── 統計 ──")
    for k in ("OK", "WARN", "PROBLEM", "ERROR"):
        if k in tally:
            print("  %-8s %d" % (k, tally[k]))
    print("  %-8s %d" % ("UNCITED", len(uncited)))
    print("\n⛔ 以上為報表，非 pass/fail。「散文改寫得恰不恰當」需人工判斷；")
    print("   唯『條號不存在』屬客觀事實，已另寫成 pytest 硬性檢查。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
