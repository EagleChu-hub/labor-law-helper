# CLAUDE.md

> ★ **法律內容的作業紀律，另見兩個 skill**（`~/.claude/skills/`）：
> `tw-labor-dispute`（勞資爭議的程序、法條、算式）與
> `adversarial-docs`（有敵意讀者的文書紀律）。
> 三條與本專案直接相關的：
> ⛔ **引用法條寧可逐字抄，不要改寫**——「只抄一半」比「完全沒寫」危險，
>    因為抄一半的看起來是完整的（PR14、PR15 各栽在這上面一次）。
> ⛔ **查不到原文就不要引**，改列「待查證」。
> ⛔ **含血噴人比證據不足更致命**——本專案的使用者是勞工，
>    錯誤指控雇主違法（假陽性）比少報一項違規更傷人。
>
> ⚠️ 反向亦然：本專案的 `raw_chunks_cache.json` 是那兩個 skill **唯一的**法規
> ground truth，skill 的 `scripts/verify_quotes.py` 會讀它。**動語料庫要想到這件事。**

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

#### ⛔ 已發生過一次外洩，且**永遠無法從歷史中移除**

**初始提交（`7e3ceac`, 2026-05-26）的 `.env.example` 裡放的是「真實金鑰」而非佔位符**，
於 `87c1db6`（2026-07-12）移除。但這是**公開 repo**——
⛔ **移除只是讓它從當前檔案消失，任何人 `git log -p -- .env.example` 仍可取得該值。**
Google 已偵測到公開外洩並自動停用該金鑰（見 `progress.md` PR 紀錄）。

**⚠️ 待辦**：若尚未親自到 Google Cloud console 確認該金鑰已撤銷，**請去確認一次**
——不要只依賴「自動停用」的通知。

★ **教訓（比這個 key 本身重要）**：
1. **`.env.example` 是要 commit 的檔案**，裡面**只能放佔位符**
   （`GOOGLEAI_Studio_API_KEY=your-api-key-here`），一個真實字元都不能有。
2. **secret 一旦推上公開 repo 就當作永久外洩**——刪掉、改掉、force push 都不算數，
   ⛔ **唯一有效的處置是「撤銷並換新」**。
3. 新增任何 `*.example`、README 範例、截圖前，先確認裡面沒有真值。

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

### ⓬ 國定假日靜態 dict 的補假日維護規則（只加補假日，不加原始週末節日）

當某年國定假日落在週六或週日，法律效力完全轉移到補假日（工作日）。維護 `national_holidays.py` 和前端 `TAIWAN_HOLIDAYS`（`frontend/app/check/page.tsx`）時：

```python
# ❌ 錯誤：同時放原始節日（週末）和補假日
"2026-04-04": "兒童節",          # 週六，法律效力已轉移，不該在此
"2026-04-03": "兒童節（補假）",  # 週五

# ✅ 正確：只放補假日，移除原始週末日
"2026-04-03": "兒童節（補假）",  # 週五 ← 唯一入口
```

**若兩個都放，會同時觸發兩個 bug：**
1. `rest_holiday_collisions` 掃描器對原始週末日（同時是例假/休息日 + 國定假日）命中，產生虛假的「應協商補假」警示
2. 若勞工恰好在那個週六出勤，`national_holiday` 規則與 `sunday_work`/`saturday_pay` 規則同時 fire，金額重複計算

**每年底新增隔年假日時的 checklist：**
- 查行政院人事行政總處「政府機關行事曆」確認哪些節日遇週末
- 遇週末的節日：**只加補假日**（週五或週一），原始週末日不加入 dict
- comment 標明對應關係（如 `# 4/4 週六 → 補假移至 4/3 週五`）
- 同步更新兩個地方：`backend/domain/rule_engine/national_holidays.py` 和前端 `TAIWAN_HOLIDAYS`

> 這個維護規則的設計原則等同「台指期結算日」的處理思路：當一個日期的「法律效力」被挪移到另一天，原始日期就不再具有任何特殊身份，不應留在 dict 中。

---

### ⓭ `frontend/` 目錄有獨立 `.git`，推送父 repo 前必須刪除

Next.js `create-next-app` 執行時會自動在 `frontend/` 內 `git init`，形成巢狀 git repo。從父層執行 `git add .` 時 git 視之為 submodule 並報錯：

```
error: 'frontend/' does not have a commit checked out
fatal: adding files failed
```

**修法**：推送前刪除 `frontend/.git`（隱藏資料夾，需在 Windows 檔案總管開啟「顯示隱藏的項目」才看得到）。

> ⚠️ 方向務必正確：刪 `frontend/.git`（子目錄的），**不是** 根目錄的 `.git`（根目錄的 `.git` 是整個專案的 git 歷史，刪了就什麼都沒了）。

---

### ⓮ `OpenSourceAiButtons`：點 AI 連結時應自動複製提示詞（fire-and-forget）

使用者常直接點「開啟 ChatGPT」而跳過「複製提示詞」，到了 ChatGPT 才發現沒東西貼。

**修法**：在 `<a>` 的 `onClick` 裡 fire-and-forget 複製，不阻擋 `href` 導覽：

```tsx
function handleAiLinkClick() {
  navigator.clipboard.writeText(prompt).catch(() => {}); // 不 await
  setCopied(true);
  setTimeout(() => setCopied(false), 3000);
}
<a href={AI_LINKS.chatgpt} target="_blank" onClick={handleAiLinkClick}>
  🤖 步驟 2：ChatGPT
</a>
```

**不能** `await clipboard.writeText()` 後再 `window.open()`——async 結束後呼叫 `window.open()` 可能被瀏覽器 popup blocker 攔截。`<a href>` 不受此限制。

---

## 部署架構

```
GitHub repo（同一份）
  https://github.com/EagleChu-hub/labor-law-helper
  │
  ├─ Render                後端 FastAPI
  │    環境變數：GOOGLEAI_Studio_API_KEY
  │             GEMINI_MODEL=gemini-2.5-flash
  │
  ├─ Vercel A（開源公開版）前端
  │    環境變數：NEXT_PUBLIC_API_URL=<Render URL>
  │             NEXT_PUBLIC_MODE=opensource
  │
  └─ Vercel B（親友私人版）前端
       環境變數：NEXT_PUBLIC_API_URL=<Render URL>
                NEXT_PUBLIC_MODE=private
```

- Render 免費方案閒置 15 分鐘後休眠，冷啟動約 30 秒。前端已內建 65 秒 timeout + 最多 2 次自動重試 + 琥珀色提示橫幅。
- 開源版不打後端 LLM API，但 `/check/analyze` 和 `/law/search` 仍送至 Render（不吃 LLM quota）。
- 兩個 Vercel 專案指向同一 GitHub repo，只差環境變數，程式碼完全相同。
