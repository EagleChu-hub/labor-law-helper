"""
RAG 回答生成器：從 hybrid_retriever 取得相關條文，交給 Gemini 生成「律師口吻」的 Markdown 回答。
不再要求 LLM 輸出 JSON，避免格式錯誤與截斷；citations 由後端從 retriever 結果直接抽取。
"""
import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ── 律師口吻 system prompt ──
SYSTEM_PROMPT = """你是台灣勞動法專業律師，回答對象是不熟悉法律的勞工。你的任務是降低勞工申訴的門檻，用他們能理解的話說明老闆做的事情可能違反什麼規定、他們可以主張什麼權益。你的服務範圍不只是勞動基準法的工時、加班費、例假等議題，也涵蓋《職業安全衛生法》職場霸凌防治新制（2026 年 7 月 1 日施行），包含職場霸凌的定義、雇主調查處理義務與申訴管道。

## 回答原則
1. 用「老闆做了 X，可能違反 Y」的句型，**先講行為再講法條**。
   範例：「老闆排你連續上 7 天班，可能違反勞基法第 36 條規定的『每 7 天至少 1 天例假』。」
2. 每提到一條法條，**緊接著用一段白話翻譯該條文**，不要叫勞工自己去查。
3. 高風險判斷要保守，但**不要把「請諮詢律師」當作主要結論**——勞工現在就是來找你諮詢的。
   只有在雇主可能否認、或事實未明時，才在該段落最後加一句「如雇主否認，建議撥 1955 或諮詢律師」。
4. 只能引用「下方提供的條文與判決」，不要捏造法條內容、條號或案件字號。
   若 context 中有【法院判決】，在「你可以主張的權益」段落引用，格式：
   「根據[法院名稱][案號]（[年份]），[一句話說明判決結果]。」
5. 若提供的條文不足以回答，誠實說「目前資料無法完整判斷，建議補充 ⋯⋯ 後再評估」。
   ⛔ 若你**印象中有一條相關條文但下方沒有提供**：可以指出「另有○○法第○條可能相關，建議查證」，
   但**絕對不要憑記憶複述該條的內容、數字或要件**——只給條號當線索，不給內容當事實。
   ★ 理由：背出來的法條看起來和查證過的一模一樣，使用者分不出來，而勞工會照著去跟雇主主張。
   漏講一條的代價，遠小於講錯一條的代價。
6. **區分受僱型態**：若問題涉及工時、例假、加班費，要主動釐清：
   - **月薪制／全職**：適用標準工時（勞基法第 30 條第 1 項「勞工正常工作時間，每日不得超過八小時，每週不得超過四十小時」），勞基法第 36 條第 1 項「勞工每七日中應有二日之休息，其中一日為例假，一日為休息日」嚴格適用。
   - **時薪制／部分工時**：工時、例假、加班費的規定**原則上完全相同**，不因時薪制而降低標準。
   - 若勞工未說明型態，先用最常見的「月薪制」回答，並在文末加一句「如你是時薪／部分工時，規定略有差異，可再告知我細節」。
   ⛔ 受僱型態與下一點的「變形工時」是**兩件不相干的事**，不要綁在一起講——月薪制全職一樣可能被排變形工時，時薪制也不會因為是時薪就可以挪例假。
7. **雇主若主張「有變形工時」或「例假可以挪」，那是附條件的例外，不是預設**。
   ⛔ 絕對不要因為雇主說有變形工時，就告訴勞工「這樣排班是合法的」。要把它變成一張**勞工可以回頭查核的清單**：
   - 變形工時本身（勞基法第 30 條第 2、3 項、第 30 條之 1）：①須經工會同意，無工會者經勞資會議同意 ②「僅適用於經中央主管機關指定之行業」。
   ⚠️ 採變形工時後，**週工時上限仍在**，這是勞工最容易被犧牲的一道保護，務必主動講：二週變形「其分配於其他工作日之時數，每日不得超過二小時。但每週工作總時數不得超過四十八小時」；八週變形「但每日正常工作時間不得超過八小時，每週工作總時數不得超過四十八小時」。
   - 採變形工時後，例假密度**仍有法定下限**（第 36 條第 2 項）：依第 30 條第 2 項者「每七日中至少應有一日之例假，每二週內之例假及休息日至少應有四日」；依第 30 條第 3 項者「每七日中至少應有一日之例假，每八週內之例假及休息日至少應有十六日」；依第 30 條之 1 者「每二週內至少應有二日之例假，每四週內之例假及休息日至少應有八日」。
   - 把例假**挪到七日週期內的其他位置**是另一條更嚴格的規定（第 36 條第 4、5 項），四個要件須**同時**滿足：①經中央目的事業主管機關同意 ②且經中央主管機關指定之行業 ③應經工會同意，無工會者經勞資會議同意後始得為之 ④僱用勞工人數在三十人以上者，應報當地主管機關備查。
   ⚠️ 且第 4 項僅得調整「第一項、第二項第一款及第二款」所定之例假——依第 30 條之 1（四週變形）者**不在可調整之列**。
   - **連續工作天數的上限**（勞基法施行細則第 22-3 條）：「本法第三十六條第一項、第二項第一款及第二款所定之例假，以每七日為一週期，依曆計算。雇主除依同條第四項及第五項規定調整者外，**不得使勞工連續工作逾六日**。」
     → 也就是說：**預設上限是連續六日**；只有在例假確實依第 36 條第 4、5 項完成調整的情形，才不受六日限制，且調整後的例假**仍須落在各自的七日週期內**。雇主主張可以連上七日以上，就必須先證明他完成了第 4、5 項的全部程序。
     ⛔ 不要自行推算「最多可以連上幾天」這類數字——法條沒有明文，講出一個數字會被勞工當成保證。只講「預設六日」與「例假仍須在各自七日週期內」這兩件有條文依據的事。
   - **另外兩道程序，勞工同樣查得到，而且常常是突破口**：
     ① 勞基法施行細則第 20 條第 4 款：雇主「依本法第三十六條第二項或第四項規定調整勞工例假或休息日」者，**應即公告周知**——沒有公告，就是沒有依法實施。
     ② 勞基法施行細則第 22-1 條：應報備查者「雇主至遲應於開始實施……調整例假之**前一日**為之」（天災、事變或突發事件不及報備查者，應於原因消滅後二十四小時內敘明理由為之）；且該條所定僱用勞工人數「以同一雇主僱用適用本法之勞工人數計算，**包括分支機構之僱用人數**」——雇主不能用拆分店點的方式規避三十人門檻，**事後補報也不能回溯正當化已經排出去的班**。
   → 請告訴勞工：他有權要求雇主出示上述同意、指定、公告與備查文件（並注意備查日期是否在實施之前）；拿不出來，雇主就不能主張這個例外。
8. **職場霸凌問題**：引用職安法第 22-1 條、第 22-2 條（雇主知悉後應採取之立即有效適當措施：調查、協調、保護、懲戒）、第 22-3 條（申訴管道）與《職場霸凌防治措施準則》。
   第 22-1 條第 1 項定義（⛔ 下列限縮要件不可省略，省了會害勞工誤判）：「勞工**於勞動場所執行職務**，因其**事業單位人員**利用職務或權勢等關係，逾越業務上必要**且**合理範圍，持續以冒犯、威脅、冷落、孤立、侮辱或其他不當之言詞或行為，致其身心健康遭受危害。**但情節重大者，不以持續發生為必要**。」
   ⚠️ 行為人須是「事業單位人員」——客戶、廠商等外部人員之不當行為不在本條定義內（可能適用職安法第 6 條第 2 項第 3 款之不法侵害預防，須分別說明，不要混用）。
   第 22-1 條第 2 項雇主義務（勞工可直接主張）：「勞工人數在十人以上者，應訂定職場霸凌申訴管道，並在工作場所公開揭示」；「勞工人數在三十人以上者，應訂定職場霸凌防治措施、申訴及懲處規範，並在工作場所公開揭示」。
   第 22-3 條第 1 項：勞工遭受職場霸凌，**應**向雇主提起申訴（這是原則上的前置程序，不要說成「可以選擇」）；**但被申訴人為最高負責人時，得逕向直轄市或縣（市）主管機關提起申訴**。
   ⚠️ 下列期限是「逕向地方主管機關申訴」才適用（第 22-3 條第 2 項）：「自職場霸凌行為終了時起，逾三年者，不予受理」；「職場霸凌事件發生時勞工在職者，其得於離職之日起一年內申訴。但依前款規定有較長申訴期限者，從其規定」。
   明確告知此新制**已於 2026 年 7 月 1 日生效施行**（不要說「將於」）。
9. **精簡**：每段不超過 4 行，整篇回答約 800–1200 字，避免冗長。

## 輸出格式
**只輸出 Markdown，嚴禁輸出 JSON、code block、英文 key、HTML。**
固定以下四段結構，每段用 `## ` 開頭：

## 老闆可能違法的地方
（條列雇主行為與對應法條，先行為再法條）

## 你可以主張的權益
（具體說可以要回什麼：補加班費？補休？資遣費？）

## 建議保留的證據
（出勤打卡、LINE 訊息、薪資單、排班表⋯⋯）

## 申訴管道
（用一兩句話告知 1955 / 地方勞動局 / 勞動部信箱即可，前端會自動補連結）

使用繁體中文，避免過度法律術語；若必須使用，請括號附白話解釋。"""


def _build_context(retrieval_results: list[dict]) -> str:
    if not retrieval_results:
        return "（未找到相關條文）"
    parts = []
    for r in retrieval_results[:6]:  # 判決 2 + 條文 4
        badge = "法院判決" if r.get("doc_type") == "judgment" else r.get("doc_type", "statute")
        parts.append(
            f"【{badge}】{r.get('article_no', '')} "
            f"{r.get('title', '')}\n{r.get('text', '')[:300]}"
        )
    return "\n\n".join(parts)


def _json_to_markdown(obj: dict) -> str:
    """若 Gemini 倒退回 JSON 格式，將舊 schema 轉成乾淨 Markdown"""
    parts = []
    headline = obj.get("headline") or ""
    summary = obj.get("summary") or ""
    reasoning = obj.get("reasoning") or ""
    suggestions = obj.get("suggestions") or []
    missing = obj.get("missing_facts") or []

    parts.append("## 老闆可能違法的地方")
    if headline:
        parts.append(f"**{headline}**\n")
    if summary:
        parts.append(summary)
    if reasoning:
        parts.append("")
        parts.append(reasoning)

    if suggestions:
        parts.append("\n## 你可以主張的權益")
        for s in suggestions:
            parts.append(f"- {s}")

    if missing:
        parts.append("\n## 建議保留的證據")
        parts.append("為了確認上述判斷，建議補充以下事實或證據：")
        for m in missing:
            parts.append(f"- {m}")
    else:
        parts.append("\n## 建議保留的證據")
        parts.append("出勤打卡記錄、薪資單、排班表、與主管的 LINE 對話。")

    parts.append("\n## 申訴管道")
    parts.append("撥打 1955 勞工諮詢專線，或向地方勞動局申訴。")
    return "\n".join(parts)


def _strip_code_fences(text: str) -> str:
    """剝離 LLM 可能多包的 ```...```；若內容仍是 JSON，轉換成 Markdown 兜底"""
    t = text.strip()
    # 整段被 ``` 包起來
    m = re.match(r"^```(?:\w+)?\s*([\s\S]*?)\s*```\s*$", t)
    if m:
        t = m.group(1).strip()
    # 內含 ```json ...``` 區塊（非完整包裹）→ 抽出第一段 JSON
    m2 = re.search(r"```json\s*([\s\S]*?)```", t)
    if m2:
        candidate = m2.group(1).strip()
        try:
            obj = json.loads(candidate)
            logger.warning("Gemini regressed to JSON output; converting to markdown")
            return _json_to_markdown(obj)
        except json.JSONDecodeError:
            pass
    # 內容看起來像 JSON（以 { 開頭）→ 嘗試解析
    if t.startswith("{") and t.endswith("}"):
        try:
            obj = json.loads(t)
            logger.warning("Gemini returned raw JSON; converting to markdown")
            return _json_to_markdown(obj)
        except json.JSONDecodeError:
            pass
    return t


def _extract_headline(markdown: str) -> str:
    """從 markdown 抽 headline：第一個非空行（最多 40 字）"""
    for line in markdown.splitlines():
        line = line.strip().lstrip("#").strip()
        if not line:
            continue
        # 跳過固定的四段標題
        if line in ("老闆可能違法的地方", "你可以主張的權益", "建議保留的證據", "申訴管道"):
            continue
        # 移除 markdown 強調符號
        line = re.sub(r"[*_`]+", "", line)
        return line[:40]
    return "已生成法律分析"


def _build_law_references(retrieval_results: list[dict]) -> list[dict]:
    """從 retriever 結果建立 law_references（不依賴 LLM 輸出）"""
    refs = []
    seen = set()
    for r in retrieval_results[:6]:
        article_no = r.get("article_no", "")
        if not article_no or article_no in seen:
            continue
        seen.add(article_no)
        refs.append({
            "article_no": article_no,
            "title": r.get("title", "") or f"勞基法{article_no}",
            "snippet": (r.get("text", "") or "")[:80],
            "doc_type": r.get("doc_type", "statute"),
            "source_url": r.get("source_url", ""),
        })
    return refs


def _fallback_response(question: str, retrieval_results: list[dict], error: str) -> dict:
    """LLM 呼叫失敗時的降級回應（仍回 markdown 格式）"""
    logger.error("LLM call failed: %s", error)
    refs = _build_law_references(retrieval_results)
    md = (
        "## 老闆可能違法的地方\n\nAI 分析服務暫時不可用，無法即時判斷你的情況。\n\n"
        "## 你可以主張的權益\n\n請參考下方系統找到的相關法條，或撥打 1955 勞工諮詢專線。\n\n"
        "## 建議保留的證據\n\n保留出勤打卡記錄、薪資單、LINE 對話、排班表等書面或電子證據。\n\n"
        "## 申訴管道\n\n撥打 1955 勞工諮詢專線，或向地方勞動局申訴。\n"
    )
    return {
        "markdown": md,
        "headline": "系統暫時無法分析，請稍後再試",
        "law_references": refs,
        "followup_questions": [],
    }


def generate_answer(
    question: str,
    history: list[dict],
    retrieval_results: Optional[list[dict]] = None,
) -> dict:
    """
    生成 RAG 回答。
    retrieval_results: 若 None 則自動從 hybrid_retriever 取得。
    回傳 dict 格式：{markdown, headline, law_references, followup_questions}
    """
    # 自動取得相關條文
    if retrieval_results is None:
        try:
            from domain.retriever.hybrid_retriever import hybrid_search
            retrieval_results = hybrid_search(question, top_k=4)
        except Exception as e:
            logger.warning("Retrieval failed: %s", e)
            retrieval_results = []

    # 即時抓取相關法院判決，排在條文前面讓 Gemini 優先引用
    try:
        from domain.retriever.dr_lawbot_retriever import fetch_judgments
        ext_judgments = fetch_judgments(question, top_k=2)
        retrieval_results = ext_judgments + retrieval_results
    except Exception as e:
        logger.warning("tlr judgment fetch skipped: %s", e)

    context = _build_context(retrieval_results)

    user_message = f"""以下是與問題相關的勞基法條文（僅供你引用，請勿捏造其他條文）：

{context}

---

勞工的問題：{question}

請依照系統指示，用 Markdown 格式（## 標題 + 條列）回答。先講老闆做了什麼，再說可能違反哪條，並用白話翻譯該條文。"""

    api_key = os.getenv("GOOGLEAI_Studio_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_response(question, retrieval_results, "No API key configured")

    raw = ""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # 組裝對話歷史
        contents = []
        for msg in history[-6:]:  # 最多保留 3 輪對話
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))
        # 加入當前問題
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))

        # gemini-2.5-flash 預設啟用「thinking」模式，思考過程會消耗大量 output tokens、
        # 導致實際回應被切短到 100 多字。明確設定 thinking_budget=0 關閉思考模式，
        # 並把 max_output_tokens 拉到 8192 充裕應對。
        config_kwargs = dict(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=8192,
        )
        try:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except AttributeError:
            # 舊版 SDK 沒有 ThinkingConfig：直接略過，靠 max_tokens 撐住
            logger.info("SDK has no ThinkingConfig; relying on max_output_tokens")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        raw = response.text or ""
        # 若 SDK .text 為空但有 candidates，組合 parts
        if not raw and getattr(response, "candidates", None):
            try:
                parts = response.candidates[0].content.parts
                raw = "".join(getattr(p, "text", "") for p in parts)
            except Exception:
                pass

        # 偵測截斷原因，方便除錯
        try:
            finish = response.candidates[0].finish_reason if response.candidates else None
            if finish and str(finish).upper() not in ("STOP", "FINISH_REASON_STOP"):
                logger.warning("Gemini finish_reason=%s (response length=%d chars)", finish, len(raw))
        except Exception:
            pass

        markdown = _strip_code_fences(raw)

        return {
            "markdown": markdown,
            "headline": _extract_headline(markdown),
            "law_references": _build_law_references(retrieval_results),
            "followup_questions": [],
        }

    except Exception as e:
        logger.exception("Gemini call failed (raw=%s): %s", raw[:200], e)
        return _fallback_response(question, retrieval_results, str(e))
