"""
條次核對：把 AI 回答裡寫到的「法規名稱＋條次」抓出來，逐一比對語料庫，
由**程式**產生文末的「請自己再核對一次」清單（PR28）。

★ 為什麼不讓 AI 自己列：PR27 實測，AI 自己寫的清單會多列正文沒引用的條文，
   而且「AI 說它核對過」不等於核對過。清單必須由程式比對出來。

⛔ 本模組只確認「這一條存在於本站收錄的法規」，**不**確認 AI 的白話轉述與原文一致。
   輸出文字必須把這件事講清楚——沒檢查就說沒檢查（CLAUDE.md ㉚）。
"""
import ast
import json
import os
import re
from functools import lru_cache

_CORPUS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "raw_chunks_cache.json",
)

SECTION_TITLE = "## 請自己再核對一次"

# 口語簡稱 → 語料庫的 law_name。只收確定的簡稱；對不到的一律報「未收錄」，不猜。
_ALIASES = {
    "勞基法施行細則": "勞動基準法施行細則",
    "勞基法": "勞動基準法",
    "職安法": "職業安全衛生法",
    "就保法": "就業保險法",
    "就服法": "就業服務法",
    "勞退條例": "勞工退休金條例",
    "勞保條例": "勞工保險條例",
    "性平法": "性別平等工作法",
    "性工法": "性別平等工作法",
    "健保法": "全民健康保險法",
    "災保法": "勞工職業災害保險及保護法",
}
_CARRY_WORDS = ("同法", "本法", "該法", "同細則", "本細則", "同條例", "本條例")
_LAW_SUFFIX_RE = re.compile(r"(?:法|條例|細則|準則|辦法|規則|規程|標準)$")
_CJK_TAIL_RE = re.compile(r"[一-鿿]{2,20}$")

_CJK_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CJK_UNIT = {"十": 10, "百": 100, "千": 1000}
_N = r"[0-9〇零一二兩三四五六七八九十百千]+"
_ONE = r"%s(?:\s*[-－]\s*%s)?" % (_N, _N)
# 第 36 條／第 30 條之 1／第 22-1 條／第 24、39 條／第 22-1~22-3 條
_ART_RE = re.compile(
    r"第\s*(%s(?:\s*[、,，及與和~～至]\s*%s)*)\s*條(?:\s*之\s*(%s))?" % (_ONE, _ONE, _N)
)


def _to_int(s: str):
    s = s.strip()
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in _CJK_DIGIT:
            cur = _CJK_DIGIT[ch]
        elif ch in _CJK_UNIT:
            total += (cur or 1) * _CJK_UNIT[ch]
            cur = 0
        else:
            return None
    return total + cur


def _canon(one: str):
    """'22-1'／'二十二'／'30' → '22-1'／'22'／'30'；無法解析回 None"""
    parts = re.split(r"\s*[-－]\s*", one.strip())
    nums = [_to_int(p) for p in parts]
    if any(n is None for n in nums):
        return None
    return "-".join(str(n) for n in nums)


def _expand(nums_text: str, zhi) -> list:
    """把一個「第…條」裡的條號展開成清單（含頓號列舉與範圍）。"""
    out = []
    tokens = re.split(r"\s*([、,，及與和~～至])\s*", nums_text)
    prev, range_pending = None, False
    for tok in tokens:
        if tok in ("~", "～", "至"):
            range_pending = True
            continue
        if tok in ("、", ",", "，", "及", "與", "和") or not tok.strip():
            continue
        cur = _canon(tok)
        if cur is None:
            continue
        if range_pending and prev:
            a, b = prev.split("-"), cur.split("-")
            if len(a) == len(b) and a[:-1] == b[:-1] and int(a[-1]) < int(b[-1]) <= int(a[-1]) + 30:
                for i in range(int(a[-1]) + 1, int(b[-1])):
                    out.append("-".join(a[:-1] + [str(i)]))
            range_pending = False
        out.append(cur)
        prev = cur
    if zhi and out:
        z = _to_int(zhi)
        if z is not None:
            out[-1] = f"{out[-1]}-{z}"
    return out


@lru_cache(maxsize=1)
def _index() -> dict:
    """{law_name: {條號: source_url}}。條號一律取 article_no 欄位（兩種來源都有，CLAUDE.md ㉗）。"""
    with open(_CORPUS, encoding="utf-8") as f:
        data = json.load(f)
    idx: dict = {}
    for r in data:
        # ⛔ 不可只收 doc_type == "statute"：施行細則、準則、辦法是 "enforcement_rule"，
        #    濾掉會把真條文報成「查無此條」（test_施行細則不可被勞基法吃掉 抓到的）
        if r.get("doc_type") not in ("statute", "enforcement_rule"):
            continue
        meta = r.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = ast.literal_eval(meta)
            except Exception:
                meta = {}
        law = meta.get("law_name")
        art = re.sub(r"[^0-9\-]", "", (r.get("article_no") or "").replace("之", "-"))
        if not law or not art:
            continue
        url = r.get("source_url") or ""
        idx.setdefault(law, {})[art] = url if "law.moj.gov.tw" in url else ""
    return idx


def _law_before(prefix: str, names: list):
    """
    判斷「第 X 條」前面緊接的法規名。
    回傳 ("known", 正式名)／("unknown", 顯示名)／("carry", None)／None（前面不是法規名）。
    ⛔ 必須「緊接」才算——順帶提及的法規名不改變上下文（CLAUDE.md ⓳）。
    """
    p = re.sub(r"[\s*_`]+$", "", prefix)
    bracket = None
    if p.endswith(("》", "」")):
        m = re.search(r"[《「]([^《》「」]{2,40})[》」]$", p)
        if m:
            bracket = m.group(1)
            p = p[: m.start()] + bracket
    for w in _CARRY_WORDS:
        if p.endswith(w):
            return ("carry", None)
    for n in names:  # 已依長度由長到短排序：「勞基法施行細則」必須先於「勞基法」
        if p.endswith(n):
            return ("known", _ALIASES.get(n, n))
    if bracket:
        return ("unknown", bracket)
    if _LAW_SUFFIX_RE.search(p):
        m = _CJK_TAIL_RE.search(p)
        return ("unknown", "…" + (m.group(0)[-12:] if m else p[-12:]))
    return None


def extract_citations(text: str) -> list:
    """
    回傳依出現順序、去重後的引用清單：
      {"law": 顯示名, "art": "22-1", "status": "found"|"missing"|"unknown_law"|"no_law", "url": str}
    """
    idx = _index()
    names = sorted(list(idx.keys()) + list(_ALIASES.keys()), key=len, reverse=True)
    carry = None  # ("known"|"unknown", name)
    seen, out = set(), []
    for m in _ART_RE.finditer(text):
        arts = _expand(m.group(1), m.group(2))
        if not arts:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        hit = _law_before(text[line_start:m.start()], names)
        if hit and hit[0] != "carry":
            carry = hit
        cur = carry
        for art in arts:
            if cur is None:
                item = {"law": "", "art": art, "status": "no_law", "url": ""}
            elif cur[0] == "unknown":
                item = {"law": cur[1], "art": art, "status": "unknown_law", "url": ""}
            else:
                url = idx.get(cur[1], {}).get(art)
                item = {"law": cur[1], "art": art,
                        "status": "found" if url is not None else "missing", "url": url or ""}
            key = (item["law"], item["art"], item["status"])
            if key not in seen:
                seen.add(key)
                out.append(item)
    return out


def _fmt_art(art: str) -> str:
    return f"第 {art} 條"


def strip_ai_section(markdown: str) -> str:
    """AI 若自己寫了核對段落，一律拿掉——清單只能由程式產生。"""
    i = markdown.find(SECTION_TITLE)
    return markdown[:i].rstrip() + "\n" if i >= 0 else markdown


def build_section(markdown_body: str) -> str:
    cites = extract_citations(markdown_body)
    lines = [SECTION_TITLE, "", "這一段是程式拿上面的回答去比對本站收錄的法規原文後產生的，不是 AI 寫的。", ""]
    if not cites:
        lines.append("- 上面的回答沒有寫到任何條次，程式沒有東西可以比對。")
    for c in cites:
        name = f"{c['law']}{_fmt_art(c['art'])}"
        if c["status"] == "found":
            link = f"[看原文]({c['url']})" if c["url"] else "請到全國法規資料庫查原文"
            lines.append(f"- ✅ {name}：本站資料庫有這一條。{link}")
        elif c["status"] == "missing":
            lines.append(f"- ⚠️ {name}：本站資料庫**查無此條**。在你自己查到原文之前，請不要引用這一條。")
        elif c["status"] == "unknown_law":
            lines.append(f"- ❓ {name}：本站沒有收錄這部法規，程式無法核對，請自己查原文。")
        else:
            lines.append(f"- ❓ {_fmt_art(c['art'])}：回答沒有寫是哪一部法規，程式無法核對。")
    lines += [
        "",
        "⚠️ 程式只確認「這一條存在」，**沒有**確認上面的白話說明和原文意思一致。要拿去主張之前，請自己讀一次原文。",
        "",
        "以上條文可到全國法規資料庫（law.moj.gov.tw）輸入法規名稱與條次，核對現行原文。",
        "",
        "本工具提供的是參考資訊；你的個案最後仍以主管機關或專業人員的確認為準。",
    ]
    return "\n".join(lines) + "\n"


def append_verification(markdown: str) -> str:
    body = strip_ai_section(markdown)
    return body.rstrip() + "\n\n" + build_section(body)
