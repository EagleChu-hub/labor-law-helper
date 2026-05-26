# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 專案定位

**勞基法查詢小幫手**——協助台灣勞工判斷出勤是否違反勞基法、估算可能少領的加班費，並以律師口吻提供情境詢問。本專案**沒有**期貨、股票、金融資料等相關邏輯，勿混入其他專案的規格。

---

## 啟動指令

### 後端（FastAPI）
```bash
cd backend
python -m venv venv && venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
> Windows 若 port 8000 被佔用（WinError 10013），改用 `--port 8001`。

### 前端（Next.js 14）
```bash
cd frontend
npm install
npm run dev          # 預設 port 3000；若被佔用自動遞增
```

---

## 模組呼叫關係與資料流

### 快速判斷流程（`/check/analyze`）

```
前端 app/check/page.tsx
  └─ buildPayload()                  # 組裝 CheckRequest（含逐日 rest dates）
       └─ POST /check/analyze
            └─ routers/check.py
                 └─ domain/rule_engine/evaluator.py  ← 主入口
                      ├─ attendance_parser.py         # 原始紀錄 → ParsedAttendance
                      │    └─ national_holidays.py    # 靜態 dict，查國定假日名稱
                      ├─ labor_rules.py               # 9 條規則，各回傳 ViolationResult
                      └─ wage_calculator.py           # 依 rule_id 計算 NT$ 短少金額
```

**資料型別鏈：**
```
CheckRequest (schemas/check.py)
  → ParsedAttendance
    ├─ days: list[DayWork]           # 每個出勤日的計算結果
    ├─ weeks: list[list[DayWork]]    # 依 ISO week 分組，用於週工時計算
    └─ rest_holiday_collisions       # 例/休假日撞國定假日（含未出勤日）
  → list[ViolationResult] (labor_rules.py)
  → list[ViolationItem] (schemas/check.py) ← 附加 estimated_shortfall_ntd
  → CheckResult (schemas/check.py)
```

### 情境詢問流程（`/api/v1/ask/chat`）

```
前端 app/ask/page.tsx 或 check/result/page.tsx
  ├─ [private 模式] POST /api/v1/ask/chat
  │    └─ routers/ask.py → _try_rag()
  │         └─ domain/rag/answer_generator.py
  │              ├─ hybrid_retriever.py  # BM25 + ChromaDB RRF fusion
  │              └─ Gemini 2.5 Flash     # 生成律師口吻 Markdown
  │
  └─ [opensource 模式] OpenSourceAiButtons.tsx
       └─ 複製提示詞 → 使用者自行貼到 ChatGPT / Gemini（不打後端 LLM API）
```

### 法條搜尋流程（`/law/search`）

```
前端 app/law/page.tsx
  └─ GET /law/search?q=...
       └─ routers/law.py
            └─ hybrid_retriever.py
                 ├─ bm25_retriever.py    # BM25 全文搜尋
                 └─ vector_retriever.py  # ChromaDB 向量搜尋
```

### 前端模組依賴

```
lib/mode.ts              IS_OPENSOURCE / IS_PRIVATE（讀 NEXT_PUBLIC_MODE）
lib/api.ts               checkAnalyze() 等 API 呼叫封裝
lib/promptTemplate.ts    buildResultPrompt() / buildAskPrompt()（開源版）
types/index.ts           所有 TypeScript 型別（前後端共用格式）
components/shared/
  OpenSourceAiButtons.tsx  開源版：複製提示詞 + ChatGPT/Gemini 連結
  RiskBadge.tsx / DisclaimerBanner.tsx / ...
```

---

## 國定假日為何不走 API，用靜態 dict

`backend/domain/rule_engine/national_holidays.py` 是手動維護的靜態 dict（2024–2026）。**不呼叫外部 API** 的原因：

1. 台灣國定假日由行政院人事行政總處每年年初公告一次，不需要即時查詢
2. 假日含農曆節日（春節、端午、中秋），各年實際日期不同，可靠的機器可讀 API 來源不穩定
3. 靜態 dict 讓規則引擎完全離線運作，不因外部服務失效影響判斷

**維護方式**：每年年底手動新增下一年資料，來源為行政院人事行政總處「各機關上班及放假日期」公告。

---

## 規則引擎的 9 條規則（`labor_rules.py`）

| rule_id | 對應法條 | 說明 |
|---------|---------|------|
| `daily_overtime` | 第 32 條 | 單日工時超過 12 小時 |
| `weekly_hours` | 第 30 條 | 單週工時超過 40 小時 |
| `monthly_overtime` | 第 32 條 | 月加班超過 46 小時 |
| `consecutive_days` | 第 36 條 | 連續出勤超過 6 天無例假 |
| `min_rest_hours` | 施行細則第 17 條 | 班次間休息未達 11 小時 |
| `unpaid_overtime` | 第 24 條 | 工時超 8 小時但加班費記錄為 0 |
| `sunday_work` | 第 36、40 條 | 例假日出勤（加發 1 日工資 + 加成） |
| `saturday_pay` | 第 24、36 條 | 休息日出勤（1.34/1.67/2.67 倍） |
| `national_holiday` | 第 37、39 條 | 國定假日出勤或撞例假未補休 |

新增規則：在 `labor_rules.py` 末尾定義函數並加入 `ALL_RULES` list；在 `wage_calculator.py` 的 `calc_shortfall_for_rule()` 新增對應 `rule_id` 分支。

---

## 踩坑規則（下次 Claude 不讀程式碼就會踩的坑）

### ❶ 日期一律用本地時間，禁止 `toISOString()`

```typescript
// ❌ toISOString() 回傳 UTC，台灣時區（UTC+8）晚上 8 點後點日曆偏移一天
const dateStr = date.toISOString().slice(0, 10);

// ✅ 統一使用這個 helper
function toLocalDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
```

這個 bug 非常隱性：早上測試正常，晚上 8 點後測試才出現偏移。整個 `check/page.tsx` 日曆邏輯都依賴此函數。

---

### ❷ Gemini 2.5 Flash 必須設 `thinking_budget=0`

```python
# ❌ 不設定：thinking tokens 先消耗 output budget，回答截斷在 ~120 字
config = GenerateContentConfig(max_output_tokens=8192)

# ✅ 正確
config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
config_kwargs["max_output_tokens"] = 8192
```

Gemini 2.5 Flash 預設啟用 thinking 模式，思考過程的 token 先從 output budget 扣除，導致實際回答只剩幾行就截斷。`thinking_budget=0` 關閉 thinking，output token 才完整可用。SDK 舊版沒有 `ThinkingConfig` 有 `try/except` 兜底，但若未來升級 SDK 發現回答又截斷，先檢查這裡。

---

### ❸ 例假日偵測用逐日標記，絕對不要改回 weekday

前端 `detectRestDates()` 用 **7 天滾動視窗**，輸出逐日的 `mandatory_rest_dates` / `regular_rest_dates`（`YYYY-MM-DD` 字串列表）傳給後端。

後端 `attendance_parser.py` 判斷優先級：
```python
use_date_based = bool(mandatory_set or regular_set)
if use_date_based:
    is_mand = r.date in mandatory_set   # 逐日標記優先
else:
    is_mand = (date.weekday() == mandatory_day_off_weekday)  # fallback
```

**不要改回 weekday 判斷**——時薪制、輪班制排班不規則，weekday 方式會嚴重誤判（例：只有週二、四、六上班的時薪工，系統會誤把週三標為例假日）。

---

### ❹ 國定假日撞例假的掃描範圍要延伸邊界 ±1 天

`attendance_parser.py` 掃描 `rest_holiday_collisions` 時：

```python
start = sorted_days[0].date.date() - timedelta(days=1)  # 延伸 1 天
end   = sorted_days[-1].date.date() + timedelta(days=1)  # 延伸 1 天
```

原因：若勞工連上 6 天班（週一~週六），其例假日是週日（出勤紀錄範圍外），若那天同時是國定假日，不延伸就掃不到撞期。

---

### ❺ 加班費去重：OT 類取最大值，不加總

```python
# wage_calculator.py
OT_GROUP = {"daily_overtime", "weekly_hours", "monthly_overtime", "unpaid_overtime"}
# 這四條計算的是同一段超時的不同角度，取最大值
ot_max = max(各 OT 規則的金額)
total  = ot_max + 假日類金額（各自獨立相加）
```

若直接把四條 OT 規則相加，同一段超時會被算 4 次，金額嚴重虛高。

---

### ❻ AI 回答走 Markdown，不走 JSON

`answer_generator.py` 三層防護：
1. system prompt 明確要求「只輸出 Markdown，嚴禁 JSON、code block」
2. `_strip_code_fences()`：剝離殘留的 ` ```json ` 包裝
3. `_json_to_markdown()`：若 Gemini 仍輸出 JSON，fallback 轉換

前端用 `react-markdown` 渲染，不做 `JSON.parse`。若未來更換 LLM 後前端出現 ` ```json ` 原始碼，就是這層防護沒生效。

---

### ❼ 雙模式架構：`NEXT_PUBLIC_MODE` 環境變數

| 模式 | AI 按鈕行為 | 部署位置 |
|------|-----------|---------|
| `private`（預設） | 呼叫後端 LLM API | Vercel 私人版 |
| `opensource` | 複製提示詞，不打 API | Vercel 開源版 |

兩個 Vercel 專案指向同一 GitHub repo，只差環境變數。開源版前端仍會打 `/check/analyze` 和 `/law/search`（這兩條不吃 LLM quota）。

---

### ❽ API 金鑰安全

- 真實 Gemini API key 在 `backend/.env`（`GOOGLEAI_Studio_API_KEY=AIza...`）
- `.gitignore` 已排除 `.env`，**絕對不能 commit**
- Render 部署：在 Dashboard → Environment 設定 `GOOGLEAI_Studio_API_KEY`
- 程式讀取：`os.getenv("GOOGLEAI_Studio_API_KEY") or os.getenv("GEMINI_API_KEY")`（雙 key 名兜底）

---

### ❾ JSX 裡比較符號不能直接用 `>`

```tsx
// ❌ JSX parser 把 > 誤判為標籤
<span>超過 8>小時</span>

// ✅ 改用文字描述或 HTML entity
<span>超過 8h 以上</span>
<span>超過 8{">"}h</span>
```

---

### ❿ TypeScript Set 迭代用 `Array.from()`

```typescript
// ❌ TS2802：spread 在 target < ES2015 環境報錯
const arr = [...mySet]

// ✅ 安全
const arr = Array.from(mySet)
```

---

### ⓫ React hooks 不能在條件式分支之後才呼叫

```typescript
// ❌ 違反 hooks 規則（條件在 hooks 之前）
function AskPage() {
  if (IS_OPENSOURCE) return <OpenSourceView />;
  const [state, setState] = useState(...);  // hooks 在 return 之後
}

// ✅ 外層 wrapper 判斷，hooks 放在 inner component
function AskPage() {
  return IS_OPENSOURCE ? <OpenSourceView /> : <AskPageInner />;
}
function AskPageInner() {
  const [state, setState] = useState(...);
}
```

---

## 部署架構

```
GitHub repo（同一份）
  ├─ Render               後端 FastAPI
  │    環境變數：GOOGLEAI_Studio_API_KEY
  └─ Vercel               前端
       環境變數：NEXT_PUBLIC_API_URL=<Render URL>
                NEXT_PUBLIC_MODE=private | opensource
```

Render 免費方案冷啟動約 30 秒，前端第一個 `/check/analyze` 呼叫可能 timeout，重試即可。
