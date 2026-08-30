# 勞基法查詢小幫手 — 開發進度紀錄

> 最後更新：2026-08-24（含 PR15）

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

### PR11 — 2026/7/1 職安法「職場霸凌防治」新制整合 ✅

**動機**：2026 年 7 月 1 日《職業安全衛生法》新增「職場霸凌防治專章」（第二章之一，第 22-1~22-3 條）與兩部子法正式施行。原語料只有 GitHub 靜態 JSON 的舊版職安法（無霸凌章，含「霸凌」chunks = 0），勞工問霸凌問題時 AI 無法引用新法。

**查證結果**（常見誤解：這次不是《勞基法》修正）
| 法規 | pcode | 重點 |
|------|-------|------|
| 職業安全衛生法（114.12.19 修正） | N0060001 | 第 22-1 條定義（四要件＋情節重大單次即成立）、22-2 雇主調查義務、22-3 申訴管道 |
| 職場霸凌防治措施準則 | N0060085 | 10 人以上設申訴管道、30 人以上訂防治規範、調查小組外聘過半 |
| 地方主管機關受理最高負責人職場霸凌事件申訴處理辦法 | N0060086 | 老闆本人是行為人時的直訴程序 |

**修改**
- `backend/data/crawlers/statute_fetcher.py`：`LAWS` 新增上述 3 部法規（全部由 law.moj.gov.tw 直接爬取最新版）；每項加 `alias` 欄位並修正 text 前綴寫死「勞基法」的 bug（否則職安法條文會被誤標）
- `backend/data/crawlers/laws_for_rag_importer.py`：`_SKIP_LAWS` 加入職安法（排除 GitHub 舊版，避免新舊版重複）
- 重建語料：`raw_chunks_cache.json` 1727 → **1782 chunks**（職安法 55→61、準則 +29、申訴辦法 +20；其餘 16 部法規數量零變動）
- `backend/domain/rag/answer_generator.py` SYSTEM_PROMPT：服務範圍納入職場霸凌；新增第 7 條回答原則（22-1 定義含「情節重大單次即成立」但書、22-3 期限「行為終了起 3 年／離職起 1 年，以較長者為準」、已生效措辭）
- `frontend/lib/promptTemplate.ts`：開源版提示詞同步錨定新法（防止 ChatGPT 用舊知識回答）
- `frontend/app/ask/page.tsx`：範例問題新增職場霸凌；引用列表移除寫死「勞基法」前綴（改顯示 title，title 已含完整法規名）
- `frontend/app/law/page.tsx`：搜尋結果同樣移除寫死「勞基法」，並消除 title 重複顯示

**執行方式**：Sonnet 子代理實作 + 重建索引，Fable 最終審查（審查中修正了子代理 prompt 的兩個法律錯誤：22-1 漏「情節重大不以持續為必要」但書、22-3 期限起算點誤寫為「知悉後」）

**關鍵學習**
1. 法規名稱前綴不能寫死——多法規語料中 `text` 前綴須依 `law['alias']` 動態組合
2. 法律時效條款要抄原文：「自行為終了時起」與「自知悉時起」起算點差異重大，AI 提示詞寫錯會直接害勞工錯過申訴期限
3. 附帶發現並修復安全問題：`.env.example` 內含真實 Gemini API key（新舊各一把）——舊 key 已隨 repo 公開導致 Google 停用（先前 403 leaked 的根因），本次改回佔位符

---

### PR12 — BM25 口語同義詞擴充 + Render OOM 崩潰修復 ✅

**動機**：PR11 上線後兩個獨立問題浮現：(1) 勞工用口語描述霸凌（排擠、冷凍、欺負）時 BM25 查不到新法條文；(2) Render 後端在推送 PR11/12 commit 後開始對所有真實端點回傳 `503 hibernate-wake-error`，僅 `/docs` 與 CORS preflight 正常。

#### 12-1 BM25 口語同義詞擴充

**問題**：雲端（Render）沒有 ChromaDB，只能靠 BM25 逐字比對；「排擠」「冷凍」「欺負」等勞工口語與法條用詞（孤立、冷落、侮辱）不同字，實測 6 個口語問法中 0~1/5 命中霸凌相關 chunk。

**修法**（`backend/domain/retriever/hybrid_retriever.py`）：
- `_SYNONYMS` 新增 11 組口語→法律用語對照（霸凌、排擠、孤立、冷凍、羞辱、辱罵、欺負、穿小鞋、精神暴力、言語暴力、罵我）
- `_expand_query()` 改為累加所有命中的同義詞（去重保序），原本只取第一個命中就 return，多個口語詞同時出現時會漏掉其餘擴充詞
- 驗證：6 個口語測試問法全部從 0~1/5 提升到 5/5，且職安法 22-1 排名第一；不相關查詢（加班費怎麼算）不受影響

#### 12-2 Render OOM 崩潰迴圈修復（生產事故）

**症狀**：使用者提供的 Render 部署 log 顯示每隔數分鐘就有一次無 `==> Deploying...` 前綴、無 Python traceback 的靜默 `Running 'uvicorn main:app...'` 重啟；期間所有真實端點請求（`/api/v1/law/search`、`/api/v1/check/analyze`、`/api/v1/ask/chat`）持續逾時或 502/503，從未有一次成功回應被記錄——典型 SIGKILL OOM 特徵（免費方案 512MB 記憶體上限）。

**根因**：`backend/domain/retriever/vector_retriever.py` 的 `vector_search()` 呼叫順序錯誤——先呼叫 `_get_embed_model()`（載入 SentenceTransformer + torch，約 200-400MB）才呼叫 `_get_collection()`。但 Render 雲端**從未有** `chroma_db/`（`.gitignore` 排除，僅本機開發環境存在），`_get_collection()` 必定失敗，等於雲端每次向量搜尋都白白吃掉 200-400MB 記憶體後才 fallback，最終把 512MB 額度榨乾觸發 OOM。

**修法**：
- 對調檢查順序：先呼叫 `_get_collection()`，失敗就直接短路回傳 `[]`，完全不會走到 `_get_embed_model()`
- `sentence_transformers` 的 import 移進 `_get_embed_model()` 函數內（真正的延遲載入），雲端環境完全不會 `import torch`

**驗證**：
- 本機模擬雲端（`CHROMA_PATH` 指向不存在路徑）：確認 `'torch' not in sys.modules`，0.3 秒短路，回傳空陣列
- 本機真實環境（有 `chroma_db`）：正常回傳 5 筆結果，含職安法 22-1 條（score 0.723）
- 推送後（commit `bb94593`）連續 6 次打 `/api/v1/law/search?q=霸凌`，全數 200 OK，0-1 秒內回應（先前為多分鐘逾時）
- 端對端真實 Gemini 呼叫（口語問法「被主管冷凍排擠、當眾羞辱」）：30.1 秒回應，正確引用職安法 22-1、防治準則、申訴辦法，並附帶一筆真實法院判決

**關鍵學習**
1. 雲端與本機環境差異大時，「先檢查便宜的前置條件、再載入昂貴資源」的順序不是效能優化而是生存必要——反過來寫在資源受限環境會直接導致崩潰迴圈
2. Render 免費方案的 OOM 崩潰是 SIGKILL，Python 端完全無 traceback，只能從「無 Deploying 前綴的靜默重啟」+「從無成功請求記錄」這兩個 log 特徵反推，光看單次錯誤訊息看不出根因
3. 背景輪詢 curl 重試在崩潰迴圈期間會全部超時，必須拿到完整部署 log 才能定位——單純狂 retry 打不出根因

---

### PR13 — 網頁美學重新設計（深藍 + 金色）✅

**動機**：使用者請「Claude Design」（獨立設計 session）重新設計網頁美學，並提供了完整交接資料（`design-handoff/brief.md`）。設計稿完成後（`design-handoff/incoming/design_handoff_labor_law_redesign/`），依設計稿在既有 Next.js + Tailwind 架構下重新實作全站視覺，不動任何資訊架構、表單流程、判斷邏輯。

**設計方向**（使用者於交接階段確認）
- 整體氛圍：親切溫暖小幫手感（優化現況，非砍掉重練）
- 圖示：混合式——Hero／CTA／警語保留 emoji（⚖️💬⚠️），系統性 UI 全面換成 Lucide icons
- 主色：深藍（`#2c3c6b`）+ 金色（`#b8862f`，使用者於設計稿中確認的正式版金色，非預設 `#c69749`）

**修改**
- `frontend/tailwind.config.ts` + `frontend/app/globals.css`：新增設計 token（`navy`/`gold`/`danger`/`warn`/`ok`/`canvas`/`card`/`line`/`ink`/`muted`），全部透過 CSS variable 橋接（沿用專案既有 `var(--x)` 慣例）
- `frontend/app/layout.tsx`：透過 `next/font/google` 載入 Noto Sans TC（400/500/700/900）+ Sora（500/600/700，數字/金額專用）
- `package.json`：新增 `lucide-react`
- 全站共用元件重做樣式（props/state 介面不變）：`AppShell`（新版導覽列+品牌識別 Scale icon）、`RiskBadge`、`DisclaimerBanner`、`ChatThread`、`ViolationCard`（金色試算框、色條、狀態徽章）、`OpenSourceAiButtons`、`ErrorState`、`LoadingSkeleton`
- 5 個頁面全部重做視覺（首頁 Hero、`/check` 三步驟、`/check/result` 少領金額卡與詳細分析、`/ask` 聊天介面、`/law` 搜尋）——文案、欄位、計算邏輯逐行比對未變動

**踩坑**
- `next/font/google` 的 `Noto_Sans_TC` **不支援** `chinese-traditional` subset（build 直接失敗，錯誤訊息列出可用 subset 僅 `cyrillic`/`latin`/`latin-ext`/`vietnamese`）。next/font 對 CJK 字型只能子集化拉丁字元，中文字會 fallback 到系統字型——這是 next/font 已知限制，不是設定錯誤，改回 `subsets: ["latin"]` 即可正常 build。
- 自訂 CSS variable 顏色（如 `var(--gold-deep)`）**不支援** Tailwind 的透明度修飾語法（`text-gold-deep/90`）——Tailwind 只能對「build time 已知的固定色值」套用透明度轉換，`var()` 是執行期才解析，語法上不會報錯但顏色不會套用透明度。全面改用不帶透明度修飾的實色 class。

**驗證**：`npm run build` 通過（0 TypeScript 錯誤）；本機 `npm run dev` 逐頁點擊確認首頁／`/check` 三步驟／`/ask`／`/law` 皆正確渲染、無 console error。

---

### PR10 — 真實法院判決引用 ✅

**動機**：原本 RAG 語料只有法條文本，AI 回答只能引用條號。整合法律偵探 `tlr.dr-lawbot.com` 判決搜尋後，每次回答可附上真實法院案號與判決結果，大幅提升說服力。

**設計原則**：Real-time fetch（每次問題才抓 2 筆），不批次爬取，對外部服務友善；10 秒 timeout，失敗靜默降級，不影響現有功能。

**修改**
- **新增** `backend/domain/retriever/dr_lawbot_retriever.py`：POST `/v1/search`，回傳標準化 `dict`（`doc_type="judgment"`、`is_external=True`），解析 `snippet` 中的「勞動基準法§X」提取 `article_no`
- **修改** `backend/domain/rag/answer_generator.py`：
  - `generate_answer()`：`hybrid_search` 之後呼叫 `fetch_judgments(question, top_k=2)`，判決排在條文前面
  - `_build_context()`：上限 4→6 筆，`doc_type=judgment` 顯示「法院判決」badge
  - system prompt 第 4 條：新增判決引用格式指示「根據[法院名稱][案號]，[一句話說明]」
- **修改** `frontend/app/ask/page.tsx`：`law_references` 列表中，`doc_type === "judgment"` 顯示橘色「法院判決」徽章 + 連結至 dr-lawbot.com 原判決頁

**API 格式（`tlr.dr-lawbot.com`）**

```
POST /v1/search
{"query": "...", "max_results": 2}
→ results[].citation_text  # 案號（如「臺灣新竹地方法院 101 年度勞訴字第 29 號」）
→ results[].snippet        # 含案件摘要、判決結果、引用法條
→ results[].citation_url   # dr-lawbot.com 原始判決頁連結
→ results[].jdate          # 判決日期
```

**關鍵學習**：`requests` 打中文查詢時須 `json.dumps(ensure_ascii=False).encode("utf-8")` 並設 `Content-Type: application/json; charset=utf-8`；直接傳中文字串 API 會回 parse error。

---

### PR9 — GitHub 開源 + 公開部署（無需終端機）✅

#### 9-1 補假日 dict Bug 修正（後端 + 前端）

**問題**：`national_holidays.py` 和前端 `TAIWAN_HOLIDAYS` 同時收錄了 2026 年四個原始週末節日（02-28、04-04、04-05、10-10）和對應補假日，導致：
1. `rest_holiday_collisions` 對原始週末日虛假命中，產生「應協商補假」警示
2. 若勞工在那個週六/週日出勤，`national_holiday` 和 `saturday_pay`/`sunday_work` 雙重違規，金額重複計算

**修正**：移除原始週末日四個 entry，只保留補假日。建立維護規則：「遇週末的節日只加補假日（工作日），原始週末日不列入 dict」。

#### 9-2 OpenSourceAiButtons UX 改進

- **隱私聲明修正**：原「本網站不會把你的資料送出」→ 改為「你的出勤資料只用於本網站法規判斷，**不會傳送給 ChatGPT 或 Gemini**」（更精確，因為出勤資料確實會送後端規則引擎）
- **自動複製**：點 ChatGPT/Gemini 連結時，`onClick` fire-and-forget `navigator.clipboard.writeText()`，即使使用者跳過「複製提示詞」步驟，連結點下去時提示詞已在剪貼簿
- **按鈕文字**：加入「步驟 2：」前綴，視覺上引導操作順序

#### 9-3 新增 `frontend/.env.example`

補齊部署所需環境變數範本，讓其他開發者 fork 後知道要填什麼。含 `NEXT_PUBLIC_API_URL` 和 `NEXT_PUBLIC_MODE`。

#### 9-4 README.md 全面改寫

從簡短介紹改寫為完整部署指南：
- 雙模式架構說明（表格對比）
- Render 後端部署步驟（含截圖標示）
- Vercel 前端部署步驟（開源版 + 私人版分開說明）
- 本機開發啟動指令
- 語料來源說明
- 環境變數一覽表

#### 9-5 GitHub 開源 + 推送

- **repo**：`https://github.com/EagleChu-hub/labor-law-helper`（公開）
- **86 個檔案**，首次提交，包含 `backend/data/raw_chunks_cache.json`（1,727 筆語料快取，Render 部署必需）
- **已排除**：`backend/.env`（API key）、`frontend/.env.local`、`backend/chroma_db/`（向量索引由 Render 冷啟動重建）
- **技術注意**：Next.js 建立時會在 `frontend/` 內自動 `git init`，推送父 repo 前需先刪除 `frontend/.git`（隱藏目錄）

#### 9-6 部署完成（無需終端機）

| 服務 | 說明 |
|------|------|
| Render 後端 | 連接 GitHub repo，設定 `GOOGLEAI_Studio_API_KEY` 與 `GEMINI_MODEL` |
| Vercel 開源版 | `NEXT_PUBLIC_MODE=opensource`，公開分享給所有勞工 |
| Vercel 親友版 | `NEXT_PUBLIC_MODE=private`，私下分享給親友，含完整 AI 對話 |

部署完成後兩個版本永久上線，無需再開終端機。

---

### PR14 — 修正月加班規則漏抄 32 條 2 項但書（假陽性）✅

**動機**：稽核既有 9 條規則的法條引用時發現，`rule_monthly_overtime` 把「月加班 > 46 小時」
一律判為 `suspected_violation`，而其引用的條文 snippet 只寫「每月延長工時不得超過四十六小時。」
——**漏掉同項但書**。

勞基法 32 條 2 項完整原文（2026-08-24 以法務部全國法規資料庫覆核）：
> 「延長之工作時間，一個月不得超過四十六小時，**但雇主經工會同意，如事業單位無工會者，
> 經勞資會議同意後，延長之工作時間，一個月不得超過五十四小時，每三個月不得超過一百三十八小時。**」

⛔ **後果是假陽性**：對已依但書取得同意並報備（30 人以上）之事業單位，
46～54 小時之間**並不違法**，但系統會告訴勞工「你老闆疑似違法」。
本專案的服務對象是不熟法律的勞工，**錯誤指控雇主違法比少報一項違規更傷使用者**。

⚠️ 同一檔案的 `rule_daily_hours` 在 `missing_facts` **有**問「是否有工會或勞資會議書面同意？」，
可見不是不知道要問，是這一條漏了——**局部知識沒有擴散到同類規則**。

**修改**
- `backend/domain/rule_engine/labor_rules.py`
  - 新增常數 `_OT_LIMIT_BASE`（46h，本文）與 `_OT_LIMIT_AGREED`（54h，但書）
  - 引用 snippet 改為 `_OT_SNIPPET`，**連但書一起抄完整**
  - 改為三段式判斷：
    | 推估月加班 | status | 理由 |
    |---|---|---|
    | ≤ 46h | `compliant` | 未達本文上限 |
    | 46 ~ 54h | **`warning`** | 是否違法取決於有無工會／勞資會議同意，**不逕判違規** |
    | > 54h | `suspected_violation` | 縱經同意亦逾但書上限 |
  - `missing_facts` 補上「是否已經工會或勞資會議同意（30 人以上並報備）」
    與「每三個月是否超過 138 小時」
- `backend/domain/rule_engine/wage_calculator.py`
  - `calc_shortfall_for_rule("monthly_overtime")` 的門檻由寫死的 `46 * 60`
    改為 **import 規則端的 `_OT_LIMIT_AGREED`**，兩邊同源
  - ⚠️ 這使金額變保守（46～54h 之間不再認列少領）——
    規則端既然說「可能合法」，金額端就不該認列，**寧可少估，不可對雇主含血噴人**
- `backend/tests/test_rule_engine.py` 新增 `TestMonthlyOvertimeProviso`（5 個測試）

**踩坑**
1. ⛔ **「只抄一半」比「完全沒寫」危險**——完全沒寫看得出來缺，
   只抄前半句的引用**看起來是完整的**，而且會一路被信任下去。
   本次同時在別處（記憶檔的勞基法 14 條 2 項）發現同一種錯法，**是通病不是偶發**。
2. 改動時依 `CLAUDE.md` 鐵則 grep 全部 `46`，才發現 `wage_calculator.py` 也寫死同一個數字。
   **只改規則端會造成規則說「可能合法」、金額卻照算少領的矛盾。**
3. 前端不必改：`ViolationStatus` 型別與 `ViolationCard` 的 `statusConfig`
   **早已支援 `warning`**（黃色「需注意」卡），新狀態直接沿用。

**驗證**
- `pytest tests/ -v` → **13 passed**（原 8 + 新 5）
- 邊界實測：40h→compliant、46h→compliant、47h→warning、54h→warning、
  55h→suspected_violation、60h→suspected_violation
- 新增測試含**迴歸鎖**：`test_引用條文必須含但書` 會在 snippet 少掉
  「五十四小時」或「一百三十八小時」時失敗；
  `test_金額端門檻須與規則端一致` 以 `inspect.getsource` 確認金額端有引用規則端常數，
  **防止日後有人把數字寫死回去**

**⚠️ 尚未處理（下一步）**
其餘 8 條規則的 `law_references` snippet **均為手寫**，未與 `raw_chunks_cache.json`
（1782 chunks 法條原文）比對過，可能有同類的「抄一半」問題。
建議做一支檢核，把所有 snippet 拿去跟語料庫原文自動比對。

---

### PR15 — 引用條文 vs 法規原文自動比對（`tools/check_law_snippets.py`）✅

**動機**：PR14 靠人工發現 32 條 2 項漏抄但書。同樣的錯**不可能靠人工複查抓乾淨**——
讀的人不會每次都回去翻原文，而且「只抄一半」的引用**看起來是完整的**。
★ 但本專案手上就有 ground truth：`data/raw_chunks_cache.json`（1782 chunks 法規原文）。

**新增 `backend/tools/check_law_snippets.py`**（四項檢查，輸出報表）
以 AST 靜態取出 `labor_rules.py` 中每一個 `_ref()` / `_ref_rule()`（含所有分支，
跑規則抓不到冷門分支），與語料庫原文比對：

| | 檢查 | 抓什麼 |
|---|---|---|
| A | 條號存在 | 語料庫查無該條 → 條號或法規引錯（客觀，已寫成 pytest） |
| B | 逐字相符 | snippet 是否為原文逐字片段 |
| C | 數字遺漏 | snippet 所對應「項」中的數字有沒有漏（抓「抄一半」主力） |
| D | 但書遺漏 | 該項含但書而 snippet 未涵蓋其內容 |

**首跑抓到兩個真問題**

1. 🔴 **`rule_min_rest_hours` 引錯法規**：原引「**施行細則**第 34 條」，
   但「更換班次時至少應有連續十一小時之休息時間」在**勞動基準法第 34 條第 2 項**，
   施行細則並無此條 → **給使用者的 `source_url` 指向錯誤的法規**。
   ⚠️ 且該項同樣有但書：經中央目的事業主管機關商請中央主管機關公告者，
   得縮短為**不少於連續八小時**。故一併比照 PR14 改為三段式：
   ≥11h 合規／8～11h `warning`／<8h `suspected_violation`。
2. ⛔ **`rule_daily_hours` 的 32 條 snippet 是非法定文字**：
   「雇主延長勞工工作時間，每日不得超過4小時。」——條文實際寫的是
   「延長勞工之工作時間**連同正常工作時間，一日不得超過十二小時**」。
   改為引用完整的 32 條 2 項原文（`_OT_SNIPPET`，PR14 已建立）。
3. ⚠️ 另修正 **37 條引用的是 105 年修法前的舊條文**，已更新為現行文字。

**踩坑：報表會狼來了**
首版報表 21 筆中 12 筆 PROBLEM，但**大半是假警報**，修掉兩類才可用：
- **條號交叉引用被當成實質數字**：「第三十六條所定休息日」的「三十六」被報成漏抄
  → 比對數字前先用 `_XREF_RE` 剝掉「第○條／項／款」
- **但書被改寫但未使用「但」字**：40 條的 snippet 其實已把但書內容寫進去
  → 檢查 D 改看**但書實質內容的字元涵蓋率**（< 60% 才報），不看有沒有「但」字

★ 這一步很重要：**一份會亂叫的報表，等於沒有報表**——人會開始略過它。

**驗證**
- `pytest tests/ -v` → **15 passed**（PR14 的 13 + 新增 2 個硬性檢查）
- `python -m tools.check_law_snippets` → **OK 12（逐字）／WARN 8（改寫）／PROBLEM 0／ERROR 0**
- 新增兩個迴歸鎖（`TestLawReferenceIntegrity`）：
  - `test_所有引用的條號都存在於法規語料庫` — 防止再引錯法規
  - `test_沒有引用漏抄但書或關鍵數字` — 防止再抄一半

**⚠️ 尚未處理**
- 8 筆 WARN 屬「改寫但未偵測到遺漏」，語意是否精確仍需人工判讀（報表已列出）
- 本檔目前只掃 `labor_rules.py`。**`answer_generator.py` 的 `SYSTEM_PROMPT`
  與 `frontend/lib/promptTemplate.ts` 裡也有大量法律敘述，尚未納入比對**
  （已人工核對職安法 22-1～22-3 該段無誤）

---

### PR16 — 分流導引頁 `/triage`：給「還不知道自己要幹嘛」的人 ✅

**動機**

現有三條功能線（出勤判斷／AI 問答／法條查詢）**都是給已經知道自己要什麼的人用的**。
但去搜尋網路上勞工的實際抱怨（Dcard 工作板等）後發現，擋住最多人的不是法律見解，而是
「我不敢」「我不知道申訴跟調解差在哪」「聽說勞工局沒用」。

⛔ **設計前提**：會被雇主坑的勞工，往往也是資訊能力較弱的一群——有辦法的人自己就找得到辦法。
所以本頁的成功標準**不是「資訊完整」**，而是「一個很累、不太讀得動字的人，
能在三分鐘內知道明天要做什麼，而且知道**要怎麼開口**」。

★ 第一題刻意是「你想自己處理，還是想有人幫我」的分岔：
1955 是免付費、24 小時、有印尼／越南／泰國／菲律賓語通譯，**本身就受理申訴並轉介**——
線的另一頭有真人會做分流。但**由使用者自己選**，不預設他沒能力。

**修改**

- `frontend/lib/triageTree.ts`（新）— 內容與規則。⛔ **不是決策樹**：
  核心論點是「公法（罰雇主）與私法（拿回錢）**可以並行**」，樹只能走到一個葉子，會逼出假葉子；
  且「送件前先固定證據」對三條路線都成立，在樹裡會被複製多份然後各自漂移。
  → 內容用資料，分流用 `deriveTriage` 的明確分支（可回話「因為你選了 X，所以 Y」）。
  - `StatuteRef.verified` — false 者畫面標「待查證」，且**不得逐字進 AI 提示詞**
  - `TriageAdvisory.kind: "legal" | "practice"` — ★ 載重欄位：
    `practice` 時 `statutes` 必為空，讓「會露餡的情境」這種經驗談**在型別上就不可能掛法條**
- `frontend/app/triage/page.tsx`、`app/triage/result/page.tsx`（新）
- `frontend/components/triage/{OptionCard,ScriptCard}.tsx`（新）
- `frontend/lib/promptTemplate.ts` — 拆成 `SYSTEM_ROLE` / `OUTPUT_FORMAT_CHECK` /
  `OUTPUT_FORMAT_TRIAGE`；新增 `buildTriagePrompt()`
- `AppShell.tsx` 導覽列加第 5 項、`app/page.tsx` 首頁加主入口卡
- `backend/tools/check_frontend_statutes.py`（新）— 補上 PR15 列的缺口之一

**⛔ 先修了三個法條錯誤才動手（都在 skill 的 `01-程序路線.md`，方向全部對勞工不利）**

1. 「勞動事件法 12 條有暫免徵之規定」→ 實際是**暫免徵收裁判費三分之二**。
   ★ 又是**只抄一半**——只抄「暫免徵」漏掉「三分之二」，等於承諾了一場免費官司。
2. 行政調解被寫成「只有契約效力」→ 實際 **勞資爭議處理法 59 條**可聲請法院裁定強制執行、
   暫免繳裁判費、法院應於七日內裁定。原寫法會**把勞工推離免費路線**。
3. 訴訟被當成平行選項 → **勞動事件法 16 條**：起訴前應先經法院勞動調解。

順手補上 **勞資爭議處理法 8 條**（調解期間資方不得為不利行為，與勞基法 74 條 2 項
時點要件不同、可併用）與 **57 條**（暫免二分之一，⚠️ 與勞動事件法 12 條的三分之二不可混用）。

**踩坑**

1. ⛔ **Tailwind class 必須是完整字面字串**。第一版 `OptionCard` 寫了
   `` border-${accent} ``，build 時會被 purge 掉（掃描器看不到組出來的字串），
   而且 `gold-50` 根本不在 token 裡。改用 `Record<Tone, {...}>` 存整段 class。
2. ⛔ **腳本必須跟路線一致**。第一版不論走哪條都給「我要申請勞資爭議調解」，
   但走檢舉的人拿這句去窗口是錯的。已改 `scriptFor(goal)` 分流。
3. ⚠️ **費用數字一律不寫**。民訴 77-20 的級距本次 MCP 查不到原文，
   依「查不到就不引」全部寫「以法院公告為準」。
4. ⚠️ `useSearchParams()` 需 `<Suspense>` 邊界，否則 build 出 CSR-bailout 錯誤。
5. ⚠️ Windows + OneDrive 下 `.next` 會出 `EINVAL readlink`，
   dev server 沒關就重 build 必失敗；要先停 server 再刪 `.next`。

**驗證**

- `npm run build` 兩種模式皆 **0 TypeScript 錯誤**，`/triage`、`/triage/result` 均靜態產生
- **`buildResultPrompt` 輸出與拆分前逐字相同**（以腳本比對舊版 `SYSTEM_INSTRUCTION`
  與新組合字串，長度 717 = 717，`True`）← 這是本次最重要的回歸基準
- `python -m tools.check_frontend_statutes` → **OK 10／PROBLEM 0**／SKIP 4
  （SKIP 為語料庫未收錄的勞動事件法，已另以 taiwan-law MCP 逐條覆核）
- `pytest tests/ -q` → **15 passed**；`check_law_snippets` → PROBLEM 0
- 375px 實機寬度：底部 5 個 tab 不擠壓；四種答案組合與**錯誤參數**皆正確渲染
- 分享連結測試：直接開 `?g=&e=&s=` 網址即可還原結果（不依賴 sessionStorage）

**⚠️ 尚未處理**
- `promptTemplate.ts` 的 `SYSTEM_INSTRUCTION` 散文與後端 `SYSTEM_PROMPT` 仍未納入自動比對
  （本次只拆格式、未動共用角色文字，故後端不需同步）
- 請求權時效未查證，頁面上以 advisory 明說「本工具沒有幫你算」，並導向 1955

---

### PR17 — 補完網友的困難、縣市選單＋申請書草稿、誕生故事 ✅

**動機**

`/triage` 上線後回頭稽核「先前搜尋到的網友抱怨是否都解決了」，答案是**沒有**：

| 網友的抱怨 | 稽核前 |
|---|---|
| 調解現場的十日陷阱 | ⛔ **完全沒有** |
| 非自願離職證明拿不到 | ⛔ **完全沒有** |
| 怕被認出來／怕報復 | ⚠️ 只在 `/triage/result`，且已離職者看不到 |
| 申訴沒用／60 日 | ⚠️ 選「我要拿回錢」的人看不到 |

★★ **最嚴重的是結構性問題**：`/check/result` 是多數人實際會走到的頁面，
它直接給「向主管機關申訴」的連結，**卻沒有任何證據保存提醒、沒有報復風險提醒**
——等於叫人去檢舉卻不告訴他要先存證據。所有保護性內容都被關在 `/triage/result`，
而那要先答完三題才看得到。

另：全站只有台北市一個申訴連結，高雄的使用者被告知「去你當地的勞工局」然後拿到台北的網址。

**修改**

- `lib/triageTree.ts`
  - 新增 3 個 advisory：`ten_day_trap`（⛔ severity stop）、`separation_certificate`、
    並把 advisories 依 severity 排序（十日陷阱這種東西不能排到最後才看到）
  - 新增 6 條法條：勞動事件法 29 條、勞資爭議處理法 9/10/11 條、
    就業保險法 25 條 3 項、勞基法 19 條
  - **修 bug①** `retaliation_void` 改為一律顯示——已離職者同樣需要
    （若當初的解僱本身即屬報復，74 條 3 項的「無效」正是他最強的主張）
  - **修 bug②** `goal=money` 時把 `agency` 加入 `alsoConsider`，
    `sixty_day_notice` 觸發條件改為 primary **或** alsoConsider 含 agency
  - **修 bug③** `alsoConsider` 原本算出來卻**從來沒被顯示過**，已列入行動清單
- `components/triage/AdvisoryCard.tsx`（新）— 自 `triage/result` 抽出供 `/check/result` 共用
- `app/check/result/page.tsx` — ★ 申訴連結**之上**插入證據／報復提醒；
  加「不在台北市？」與「先幫我分流」兩個出口
- `lib/laborBureaus.ts`（新）— 22 縣市主管機關＋官方名冊退路＋申請書草稿產生器
- `app/apply/page.tsx`（新）— 管轄提醒／縣市選單／調解方式選擇／申請書草稿
- `app/about/page.tsx`（新）— 誕生故事
- `backend/tools/check_frontend_statutes.py` — 見踩坑 1

**踩坑**

1. ⛔ **檢查工具自己漏檢，而且不會報錯**。新增就業保險法時，
   `check_frontend_statutes.py` 的正則寫死 `(LSA|SDA|LIA)`，EIA 那筆被**靜默略過**
   ——報表少一筆卻一切正常，是靠人工數數（14+6 應為 20，報表卻只有 19）才發現。
   ★ **檢查工具的「涵蓋範圍」本身也要被檢查**。已改為不列舉常數名，
   並加上涵蓋率自檢：宣告筆數 ≠ 解析筆數即 `sys.exit` 報錯。
2. ⚠️ **十日陷阱只適用法院勞動調解**（勞動事件法 29 條），
   **不適用勞工局的行政調解**（依勞資爭議處理法 23 條需雙方合意，沒有自動成立機制）。
   ⛔ 為求「提醒愈多愈好」而全部顯示，就是製造假警報。已限定觸發條件並實測負向案例。
3. ⚠️ JSX 裡寫 markdown 的 `**粗體**` 會原樣顯示，要用 `<strong>`。
4. ⚠️ 政府網址 `labor.yunlin.gov.tw` 對 curl 回 403（擋 bot），瀏覽器正常
   ——**不能只憑 curl 狀態碼判定連結失效**。

**驗證**

- `npm run build` **兩種模式**皆 0 TypeScript 錯誤，14 條路由全部靜態產生
- `python -m tools.check_frontend_statutes` → **OK 15／PROBLEM 0**／SKIP 5
  （20 筆全數解析，涵蓋率自檢通過；SKIP 為語料庫未收錄之勞動事件法，另以 MCP 逐字覆核）
- `pytest tests/ -q` → **15 passed**；`check_law_snippets` → PROBLEM 0
- **22 個縣市連結逐一實測**：21 個 HTTP 200，雲林以瀏覽器確認正常 → **22/22 有效**
- 條件正確性實測：`g=punish` 路線**不出現**十日陷阱與非自願離職證明（無假陽性）；
  `g=money&s=left` 三者皆正確出現
- `/check/result` 確認提醒（302-304 行）在申訴連結（311 行）**之上**
- 375px 手機寬度；縣市選單連動申請書草稿正常
- skill 側 `verify_quotes.py` → 四條新引文 ✅ 逐字，OK 18 → 22

**⚠️ 尚未處理**
- `promptTemplate.ts` 與後端 `SYSTEM_PROMPT` 的散文法律敘述仍未納入自動比對
- 請求權時效未查證，頁面上以 advisory 明說「本工具沒有幫你算」並導向 1955
- ⛔ `/about` 的故事目前採 B 版；使用者需核對**實際簽署**之保密協議第五條，
  若被對方改寬（多出「存在」「爭議事實」「不利陳述」等字），改回 A 版只需換一個常數

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
| 判決抓取方式 | Real-time fetch（非批次爬取） | 每次查詢才抓 2 筆，對外部服務友善；失敗靜默降級不影響主流程 |
| TLR 請求編碼 | `json.dumps(ensure_ascii=False).encode("utf-8")` + charset header | 直接傳中文字串 API 會回 parse error，需手動指定 UTF-8 |

---

## 已知限制 / 未來可做

- [ ] 加班費試算僅支援月薪制，時薪制（非固定工時）倍率計算尚未完整
- [ ] 沒有登入機制，所有資料存在 sessionStorage，重新整理後消失
- [ ] 情境詢問沒有對話記憶（每次送出都是全新對話）
- [ ] 後端部署在 Render 免費方案，冷啟動需等待約 30 秒
- [ ] 開源版後端仍吃 Render 免費額度（非 LLM 部分），大量使用需自架後端
- [ ] 判決引用目前只顯示案號，未展開判決摘要供使用者直接閱讀
- [ ] `tlr.dr-lawbot.com` 查詢語言為中文時回應較慢（約 3–8 秒），可考慮 async 並行抓取

---

## 部署架構（PR12 後，已上線）

```
GitHub repo（同一份）
  https://github.com/EagleChu-hub/labor-law-helper
  │
  ├── Render              後端 FastAPI
  │     GOOGLEAI_Studio_API_KEY=<key>
  │     GEMINI_MODEL=gemini-2.5-flash
  │
  ├── Vercel A（開源公開版）
  │     NEXT_PUBLIC_API_URL=<Render URL>
  │     NEXT_PUBLIC_MODE=opensource
  │
  └── Vercel B（親友私人版）
        NEXT_PUBLIC_API_URL=<Render URL>
        NEXT_PUBLIC_MODE=private
```

**重要安全注意事項**
- `backend/.env` 含真實 Gemini API key，已加入 `.gitignore`，絕不能 commit
- API key 需在 Render Dashboard 的 Environment 設定 `GOOGLEAI_Studio_API_KEY`
- `frontend/.env.local` 亦在 `.gitignore`，本機開發用，不上傳 GitHub
