# 勞基法查詢小幫手 — 開發進度紀錄

> 最後更新：2026-05-26（含 PR8）

---

## 專案簡介

協助台灣勞工快速判斷出勤是否符合勞基法、估算可能少領的薪資，並以 AI 律師口吻提供情境詢問。

- **後端**：FastAPI + Google Gemini 2.5 Flash + BM25/ChromaDB 混合搜尋
- **前端**：Next.js 14 App Router + Tailwind CSS
- **部署**：Render（後端）+ Vercel（前端）

---

## 第一版（初始上線）

### 已實作功能
- `/check/analyze`：出勤資料輸入 → 勞基法規則引擎比對 → 回傳違規清單
- `/api/v1/ask/chat`：情境詢問，串接 Gemini RAG 回答
- `/law/search`：勞基法條文 BM25 全文搜尋
- 基本規則引擎：連續工作日、每日工時上限、最短休息時間、國定假日、加班費等

### 已知問題（第二輪修正前）
1. 情境詢問回答出現 ` ```json { "headline": ... ` 原始碼，句子被截斷
2. AI 只列法條號，未解釋法條對勞工的意義
3. 例假日偵測用「最少出現的 weekday」邏輯，時薪制排班會誤判
4. 沒有加班費試算，勞工不知道少領多少錢
5. UI 以「查法規」為框架，非「我有沒有被坑」
6. 無開源版架構，LLM quota 全部由作者承擔

---

## 第二輪迭代（2026-05）

### PR1 — AI 回答格式修正 ✅

**問題根因**
- Gemini 2.5 Flash 的 thinking tokens 消耗 output budget，導致回答在 ~120 字被截斷
- system prompt 同時要求 JSON 與 Markdown，模型混合輸出

**修法**
- `answer_generator.py`：`thinking_config=ThinkingConfig(thinking_budget=0)`，`max_output_tokens=8192`
- 新增 `_strip_code_fences()`：regex 移除殘留 ` ```json ` 包裝
- 新增 `_json_to_markdown()`：若模型仍輸出 JSON，fallback 轉換成可讀 Markdown
- 前端 `ask/page.tsx`：改用 `react-markdown` 渲染回答

**關鍵學習**：Gemini 2.5 Flash 預設 thinking 模式，`thinking_budget=0` 才能讓 output token 上限完整留給回答。

---

### PR2 — 律師口吻 Prompt 改寫 ✅

**修法**
- 改寫 `backend/domain/rag/prompts/system_prompt.txt`
- 角色設定：台灣勞動法專業律師，對象是不熟悉法律的勞工
- 固定四段輸出結構：
  1. `## 老闆可能違法的地方`（行為 + 法條）
  2. `## 你可以主張的權益`（具體金額或補假要求）
  3. `## 建議保留的證據`（打卡紀錄、薪資單等）
  4. `## 申訴管道`（1955、勞動局、前端 hardcode）
- 禁止輸出 JSON、英文 key、code block
- 結尾才加「高風險建議撥 1955」，不以「請諮詢律師」當主要結論

---

### PR3 — 例假日邏輯重構 ✅

#### 3-1 七天滾動視窗偵測（前端）

**問題**：原本用「七天內未出勤天數最多的 weekday」推算例假，時薪制不規則排班完全誤判。

**修法**：`frontend/app/check/page.tsx` 新增 `detectRestDates()`
- 輸入：使用者勾選的出勤日期集合
- 邏輯：7 天滾動視窗，找出符合「每 7 天至少 1 例假、至少 1 休息日」的逐日標記
- 即時顏色回饋（`liveRest` useMemo）：橘 = 自動偵測例假、紅 = 休息日

#### 3-2 逐日標記傳後端（取代 weekday 設定）

- `CheckRequest` 新增：`mandatory_rest_dates: list[str]`、`regular_rest_dates: list[str]`
- `attendance_parser.py`：若提供逐日清單，完全取代 weekday 判斷

#### 3-3 國定假日撞例假偵測（後端）

**問題**：若例假日當天恰好是國定假日但勞工未出勤，原本不會被偵測到。

**修法**：`attendance_parser.py` 掃描出勤紀錄首尾各延伸 1 天，對每個未出勤日判斷是否「例假日 + 國定假日」重疊。回傳 `rest_holiday_collisions` 清單。

- `labor_rules.py` `rule_national_holiday`：若 collisions 非空，輸出「應協商補假」警示
- `CheckRequest` 新增：`holiday_compensation_overrides: dict[str, str]`（原節日 → 補休日映射）

#### 3-4 台灣 UTC+8 日期 Bug 修正

**問題**：`toISOString()` 回傳 UTC 時間，晚上 8 點後點日曆會偏移一天。

**修法**：所有日期轉換改用 `toLocalDateStr(d)`（`getFullYear/getMonth/getDate`），不使用 `toISOString()`。

---

### PR4 — 加班費試算 + UI 重構 ✅

#### 4-1 後端 wage_calculator.py（新增）

依勞基法第 24、39 條倍率：

| 情境 | 倍率 |
|------|------|
| 平日延長前 2 小時 | ×1.34 |
| 平日延長 2 小時後 | ×1.67 |
| 休息日前 2 小時 | ×1.34 |
| 休息日 2–8 小時 | ×1.67 |
| 休息日 8 小時後 | ×2.67 |
| 例假日出勤 | 加發 1 日工資 + 加成 |
| 國定假日出勤 | ×2.0（加倍） |

- `calc_shortfall_for_rule(rule_id, att, hourly)`：每條規則估算短少金額
- `calc_total_shortfall()`：去重邏輯，OT 類規則取最大值，假日類獨立加總

#### 4-2 前端「少領多少」卡片

- `check/result/page.tsx` 頂部：紅色漸層大字「你這期間可能少領 NT$ X,XXX」
- 未填時薪：改顯示「有 N 個班可能涉及加班費，建議輸入時薪以查看金額」
- 每張 ViolationCard：顯示 `💰 試算短少：NT$ XXX`

#### 4-3 前端 OvertimeCalculator 元件（純前端試算機）

- 使用者可選情境（平日加班 / 休息日 / 例假日 / 國定假日）
- 輸入時薪、加班時數 → 即時計算應得金額
- 不打 API，純 JS 計算

#### 4-4 步驟 0 新增時薪輸入欄位

- `CheckRequest` 新增：`hourly_wage_regular`、`hourly_wage_holiday`
- 前端步驟 0 加「平日時薪」選填欄位

---

### PR5 — 雙模組架構（開源版 / 私人版）✅

**動機**：開源後 Gemini quota 可能被大量使用，需隔離 LLM 消耗。

**機制**：`NEXT_PUBLIC_MODE` 環境變數切換，同一份 GitHub repo 部署兩個 Vercel 專案。

| 模式 | AI 按鈕行為 |
|------|------------|
| `private`（預設） | 呼叫後端 `/api/v1/ask/chat`，使用 Gemini |
| `opensource` | 顯示「複製提示詞 → 跳轉 ChatGPT/Gemini」三個按鈕 |

**新增檔案**
- `frontend/lib/mode.ts`：`IS_OPENSOURCE` / `IS_PRIVATE` 常數
- `frontend/lib/promptTemplate.ts`：`buildResultPrompt()` / `buildAskPrompt()`，含律師口吻 system instruction + 違規清單
- `frontend/components/shared/OpenSourceAiButtons.tsx`：複製提示詞 + ChatGPT / Gemini 連結

**後端不變**：開源版不打 LLM API，`/check/analyze` 與 `/law/search` 仍正常運作。

---

### PR6 — 約定休息日加班標記 ✅

**背景**：勞基法第 36 條，勞工若與雇主約定休息日出勤，應以「休息日加班」倍率計算。使用者需能明確標記哪幾天是「約定的休息日加班」，以區別一般工作日。

**後端**
- `CheckRequest` 新增：`agreed_rest_day_ot_dates: list[str]`
- `DayWork` 新增：`is_agreed_rest_day_ot: bool`
- `rule_saturday_pay`：若日期在 `agreed_rest_day_ot_dates`，改輸出「已確認為約定休息日加班，請確認薪資倍率是否正確」（正向確認口吻，而非警示）

**前端 UX 三個入口**
1. **智慧提示卡（主要）**：偵測到「使用者勾選的休息日有出勤」時，自動彈出提示：「系統偵測到你在休息日有出勤紀錄，這天是否為與雇主約定的加班？」→ 勾選後加入 `agreedOtDates`
2. **日曆視覺標記**：`agreedOtDates` 的日期在日曆顯示橘色 + "OT" 徽章
3. **步驟 2 確認區塊**：送出前顯示橘色摘要「已標記 X 天為約定休息日加班」

---

---

### PR7 — 2026 假日資料修正 + 日曆顏色對比改善 ✅

#### 7-1 2026 國定假日更正（後端 + 前端）

**問題**：`national_holidays.py` 和前端 `TAIWAN_HOLIDAYS` 的 2026 資料有三個錯誤：

| 欄位 | 錯誤值 | 正確值 | 原因 |
|------|--------|--------|------|
| 清明節 | `2026-04-04`（和兒童節合併） | `2026-04-05`（週日） | 2026 清明節為 4/5，非 4/4 |
| 兒童節 | `"兒童節暨清明節"` | `"兒童節"`（獨立） | 2025 兩節同日，2026 各自獨立 |
| 中秋節 | `2026-10-01` | `2026-09-25`（週四） | 農曆 8/15 落在 9/25 |

**新增補假日**（假日落在週六日時，勞工可主張的補休日）：

| 補假日 | 對應假日 |
|--------|---------|
| `2026-02-27`（週五） | 和平紀念日（2/28 週六） |
| `2026-04-03`（週五） | 兒童節（4/4 週六） |
| `2026-04-06`（週一） | 清明節（4/5 週日） |
| `2026-10-09`（週五） | 國慶日（10/10 週六） |

**資料來源**：行政院人事行政總處「115年政府行政機關辦公日曆表」官方 CSV。

#### 7-2 日曆顏色對比改善

**問題**：`bg-red-50` 和 `bg-orange-50` 兩種顏色都是極淺暖色（幾乎看不出差異）。

**修法**：

| 狀態 | 舊顏色 | 新顏色 |
|------|--------|--------|
| 偵測例假日 | `bg-red-50 ring-red-200` | `bg-rose-100 ring-2 ring-rose-400`（較深玫瑰紅） |
| 偵測休息日 | `bg-orange-50 ring-orange-200` | `bg-sky-100 ring-sky-400`（天藍，截然不同） |

圖例（legend）色塊同步更新，確保視覺一致。

#### 7-3 快選按鈕新增「週一至週六」

**動機**：六天工作制（週一～週六）在台灣零售、餐飲業相當普遍，沒有快選按鈕讓使用者需一格一格點。

新增第三個快選按鈕 `selectWeekdays([1,2,3,4,5,6])`，與「週一至週五」、「週二至週六」並排。

---

---

### PR8 — 法規語料擴充 + 補假日邏輯修正 + UX 五項改進 ✅

#### 8-1 法規語料擴充（168 → 1,727 筆）

- **新增** `backend/data/crawlers/laws_for_rag_importer.py`：下載 jojostarking/law-rag-chatbot 的 `laws_for_rag.json`，排除已有更完整版本的勞基法/施行細則，引入最低工資法、性別平等工作法、勞工請假規則、就業服務法、勞工退休金條例等 1,559 筆
- **修改** `backend/data/build_index.py`：加入 step 4（相關法規）、step 5（函釋爬蟲，失敗時安靜略過）
- **重建索引**：執行後 `raw_chunks_cache.json` 從 168 → 1,727 筆；Render 冷啟動直接讀快取，不需重新爬蟲

#### 8-2 補假日工時計算修正（`wage_calculator.py`）

- 原本：`national_holiday` 固定用 `8 * h` 計算短少金額（工時不足 8h 高估，超過 8h 低估）
- 修正：`max(actual_hours, 8.0) * h`，使用實際工時但保障最低 1 日工資

#### 8-3 補假日說明文字強化（`labor_rules.py`）

- 補假日（如「兒童節（補假）」）出勤時，說明文字加入「國定假日因遇週末挪移，法律性質等同原節日」
- 強調「時薪制勞工不論工作時數長短，每小時均以雙倍計算」

#### 8-4 前端 UX 五項改進

| 項目 | 說明 |
|------|------|
| C-1 觸控目標 | 日曆格子 `w-9 h-9` → `w-10 h-10`（40px，達 Apple HIG 建議最小值） |
| C-2 Loading Spinner | 送出按鈕顯示 SVG `animate-spin` 圓圈動畫，取代純文字「分析中...」 |
| C-3 冷啟動提示 | `api.ts` 加 65 秒 timeout；超時拋出 `COLD_START_TIMEOUT`；`result/page.tsx` 最多自動重試 2 次並顯示琥珀色說明橫幅 |
| C-4 時薪制休息預設 | 切換至「時薪制」時，`useEffect` 自動把預設班次休息時間改為 30 分鐘；切回月薪制恢復 60 分鐘 |
| C-5 總工時預覽 | 步驟 2 確認頁新增「合計工時」列（useMemo 計算），顯示總時數與平均每天時數 |

---

## 技術決策記錄

| 決策 | 選擇 | 原因 |
|------|------|------|
| LLM | Gemini 2.5 Flash | 免費額度足夠初期使用，中文理解能力佳 |
| thinking_budget | 0 | 避免 thinking tokens 消耗 output budget 導致截斷 |
| 例假偵測 | 逐日標記（非 weekday） | 時薪制、輪班制排班不規則，weekday 推算不準確 |
| 日期處理 | `getFullYear/Month/Date` | `toISOString()` 回傳 UTC，台灣時區（UTC+8）晚上會偏移一天 |
| OT 金額去重 | 取 OT 類最大值 | 每日/每週/每月加班費是同一筆錢的不同計算方式，不能加總 |
| 開源隔離 | 環境變數 + 前端 prompt copy | 後端不改，只有 LLM 那一條 API 被替換 |

---

## 已知限制 / 未來可做

- [ ] 加班費試算僅支援月薪制，時薪制（非固定工時）倍率計算尚未完整
- [ ] 沒有登入機制，所有資料存在 sessionStorage，重新整理後消失
- [ ] 情境詢問沒有對話記憶（每次送出都是全新對話）
- [ ] 後端部署在 Render 免費方案，冷啟動需等待約 30 秒
- [ ] 開源版後端仍吃 Render 免費額度（非 LLM 部分），大量使用需自架後端

---

## 部署架構

```
GitHub repo (同一份)
    ├── Render            後端 FastAPI（需設定環境變數 GOOGLEAI_Studio_API_KEY）
    ├── Vercel A          前端私人版（NEXT_PUBLIC_MODE=private + NEXT_PUBLIC_API_URL=<Render URL>）
    └── Vercel B（未來）  前端開源版（NEXT_PUBLIC_MODE=opensource）
```

**重要安全注意事項**
- `backend/.env` 含真實 Gemini API key，已加入 `.gitignore`，絕不能 commit
- API key 需在 Render Dashboard 的 Environment 設定 `GOOGLEAI_Studio_API_KEY`
