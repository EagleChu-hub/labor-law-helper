# 交接文件 — 勞基法查詢小幫手

> 給下一位接手的 AI／開發者。讀完這份可以在 10 分鐘內知道專案長什麼樣、東西在哪、要改什麼動哪個檔。
> 最後更新：2026-08-24（PR15；PR14/15 尚未 commit）

---

## 0. 先讀哪幾份（順序很重要）

| 順序 | 檔案 | 為什麼 |
|------|------|--------|
| 1 | 本檔 `HANDOFF.md` | 全貌 + 常見任務對照表 |
| 2 | `CLAUDE.md` | **踩坑規則（14 條）**，不讀會重複踩雷，尤其 ❶❸❺⓬ |
| 3 | `progress.md` | PR1～PR13 完整開發史，含每次修法的根因與驗證方式 |
| 4 | `README.md` | 對外的部署說明（給 fork 的人看的） |

`design-handoff/` 是 PR13 的設計交接資料（brief + 設計稿 HTML + 截圖），已完成，僅供日後改視覺時對照。

---

## 1. 這個專案在做什麼

協助台灣勞工判斷出勤是否違反勞基法、估算可能少領的加班費、並以律師口吻回答情境問題。

**沒有**期貨、股票、金融資料邏輯——若看到相關描述那是別的專案，不要混入。

三條主要功能線：

| 功能 | 路由 | 吃不吃 LLM |
|------|------|-----------|
| 快速出勤判斷 | `POST /api/v1/check/analyze` | ❌ 純規則引擎 |
| 情境詢問（AI 律師） | `POST /api/v1/ask/chat` | ✅ Gemini 2.5 Flash |
| 法條搜尋 | `GET /api/v1/law/search` | ❌ BM25 +（本機才有）向量 |

---

## 2. 目前狀態

- **全部已上線且運作正常**，最近一次是 PR13（視覺重新設計），已 push 並確認兩個 Vercel 站台部署完成。
- 沒有進行中的未完成工作。工作區乾淨（只有幾個 untracked 的本機檔，見 §7）。

線上位置：

| 服務 | URL |
|------|-----|
| GitHub | https://github.com/EagleChu-hub/labor-law-helper |
| 後端 | https://labor-law-helper.onrender.com |
| 前端（開源公開版） | https://labor-law-helper.vercel.app |
| 前端（私人版，未公開） | 另有一個不對外公開的 Vercel 部署，網址不寫入本檔（本 repo 為 MIT 公開 repo）；需要時向專案維護者索取 |

**部署是全自動的**：push 到 `origin/master` → Render 與兩個 Vercel 專案自動重建，不需要開終端機做任何事。

---

## 3. 本機啟動

```bash
cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

- port 8000 被佔用（WinError 10013）→ 改 `--port 8001`。
- 後端要能跑 AI 問答需要 `backend/.env` 內的 `GOOGLEAI_Studio_API_KEY`（**絕不可 commit**）。
- `.claude/launch.json` 已設好 `frontend-dev`，用 preview 工具可直接起前端。

---

## 4. 常見任務 → 要改哪個檔

### 「新增／修正一條勞基法判斷規則」
1. `backend/domain/rule_engine/labor_rules.py` — 寫函數，加進 `ALL_RULES`
2. `backend/domain/rule_engine/wage_calculator.py` — `calc_shortfall_for_rule()` 加對應 `rule_id` 分支
3. 若是加班費類規則，要考慮 `OT_GROUP` 去重（**取最大值不是加總**，見 CLAUDE.md ❺）
4. `backend/tests/test_rule_engine.py` 補測試

現有 9 條規則對照表在 `CLAUDE.md`。

### 「新增／修改任何法條引用（`_ref()` / `_ref_rule()`）」
⛔ **改完一定要跑**：
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m tools.check_law_snippets
```
把每個 snippet 拿去跟 `raw_chunks_cache.json`（1782 chunks 法規原文）比對，
抓四件事：條號存在／逐字相符／**數字遺漏**／**但書遺漏**。
★ PR14、PR15 各靠它抓到一個上線中的錯（32 條漏但書、34 條引錯法規）。
⚠️ 報表不做 pass/fail（改寫恰不恰當要人判斷）；
但「條號不存在」與「漏抄但書」已鎖進 `pytest`，會直接失敗。

⛔ **最重要的一條**：引用法條**寧可逐字抄，不要改寫**。
「只抄一半」比「完全沒寫」危險——完全沒寫看得出來缺，抄一半的看起來是完整的。

### 「更新國定假日（每年底必做）」
兩個地方要**同步**改：
- `backend/domain/rule_engine/national_holidays.py`
- `frontend/app/check/page.tsx` 的 `TAIWAN_HOLIDAYS`

⚠️ 遇週末的節日**只加補假日，原始週末日不要加**——兩個都加會同時觸發虛假補假警示 + 金額重複計算。完整規則見 `CLAUDE.md` ⓬。資料來源：行政院人事行政總處「政府機關行事曆」。

### 「改 AI 回答的內容／口吻」
- 私人版（走後端 Gemini）：`backend/domain/rag/answer_generator.py` 的 `SYSTEM_PROMPT`
- 開源版（複製提示詞給 ChatGPT/Gemini）：`frontend/lib/promptTemplate.ts` 的 `SYSTEM_INSTRUCTION`

**兩邊要一起改**，否則兩個版本回答不一致。

⚠️ Gemini 設定必須保留 `thinking_budget=0`，拿掉回答會截斷在 ~120 字（CLAUDE.md ❷）。

### 「新增法規到語料庫」
1. `backend/data/crawlers/statute_fetcher.py` 的 `LAWS` list 加一項（要有 `pcode` 和 `alias`）
2. 若 GitHub 靜態來源已有舊版，在 `laws_for_rag_importer.py` 的 `_SKIP_LAWS` 排除，避免新舊重複
3. 重建索引：`cd backend && python -m data.build_index`
4. **驗證 `raw_chunks_cache.json` 總數只增不減**（目前 1782 chunks），若變少代表某來源爬取失敗，要 `git checkout` 還原
5. **一定要 commit `backend/data/raw_chunks_cache.json`** — 雲端沒有 ChromaDB，BM25 直接讀這個檔，不 commit 等於雲端沒有新法條

### 「勞工用口語問但查不到法條」
`backend/domain/retriever/hybrid_retriever.py` 的 `_SYNONYMS` 加口語→法律用語對照（如 排擠→孤立）。雲端只有 BM25 逐字比對，同義詞擴充是唯一補救手段。

### 「改視覺／樣式」
- 色票：`frontend/app/globals.css` 的 `:root`（CSS variable，固定 hex）
- Tailwind token 橋接：`frontend/tailwind.config.ts`（`navy`/`gold`/`danger`/`warn`/`ok`/`canvas`/`card`/`line`/`ink`/`muted`）
- 字型：`frontend/app/layout.tsx`（Noto Sans TC + Sora）
- 設計稿原件：`design-handoff/incoming/design_handoff_labor_law_redesign/labor-law-redesign.dc.html`

⚠️ **自訂 token 不能用 Tailwind 透明度語法**（`text-gold-deep/90` 無效），因為值是 `var()`，build 時解析不出來。要半透明就在 CSS variable 直接定義一個新的固定 hex。

### 「改前端表單／日曆流程」
`frontend/app/check/page.tsx`（約 930 行，全站最複雜的檔）。裡面有：
- `detectRestDates()` — 7 天滾動視窗偵測例假／休息日
- `toLocalDateStr()` — **所有日期轉換都要走這個**，用 `toISOString()` 會在台灣晚上 8 點後偏移一天（CLAUDE.md ❶）
- 逐日班次覆寫、約定休息日加班標記、時薪輸入

改這個檔請用 **Edit 就地修改，不要整份重寫**——邏輯密度高，重寫很容易靜默破壞判斷。

---

## 5. 架構速覽

### 後端 `backend/`
```
main.py                     FastAPI 進入點，三個 router prefix /api/v1/*
routers/{check,ask,law}.py  HTTP 層，薄
schemas/                    Pydantic 型別（前後端契約）
domain/rule_engine/         ← 判斷邏輯核心
  evaluator.py                主入口
  attendance_parser.py        原始紀錄 → ParsedAttendance
  labor_rules.py              9 條規則
  wage_calculator.py          金額試算 + 去重
  national_holidays.py        靜態 dict（刻意不呼叫外部 API，理由見 CLAUDE.md）
domain/retriever/           BM25 / 向量 / 混合 / 判決外部抓取
domain/rag/answer_generator.py  Gemini 呼叫 + Markdown 防護三層
data/                       爬蟲 + build_index + raw_chunks_cache.json
```

### 前端 `frontend/`
```
app/page.tsx                首頁
app/check/page.tsx          三步驟表單（最複雜）
app/check/result/page.tsx   結果頁（少領金額卡 + 違規卡 + 試算機）
app/ask/page.tsx            AI 聊天
app/law/page.tsx            法條搜尋
lib/mode.ts                 IS_OPENSOURCE / IS_PRIVATE
lib/api.ts                  API 封裝（含 65 秒 timeout + 冷啟動重試）
lib/promptTemplate.ts       開源版提示詞
types/index.ts              TypeScript 型別
components/shared/          AppShell / RiskBadge / DisclaimerBanner / OpenSourceAiButtons ...
```

### 雙模式（很重要，改前端一定會遇到）
同一份程式碼，靠 `NEXT_PUBLIC_MODE` 環境變數分岔：
- `private` → AI 按鈕打後端 Gemini
- `opensource` → AI 按鈕改成「複製提示詞 + 跳轉 ChatGPT/Gemini」，不打 LLM API

**任何跟 AI 有關的 UI 改動，兩種模式都要驗。**

---

## 6. 環境差異陷阱（吃過大虧）

| 項目 | 本機 | Render 雲端 |
|------|------|-------------|
| ChromaDB 向量索引 | ✅ 有 | ❌ **完全沒有**（`.gitignore` 排除，也不重建） |
| 檢索方式 | BM25 + 向量 | **只有 BM25**，讀 committed 的 `raw_chunks_cache.json` |
| 記憶體 | 充足 | 512MB 上限，超過直接 SIGKILL（無 traceback） |

PR12 的生產事故就是因為向量檢索先載入 torch 才檢查索引存在，雲端每次查詢白吃 200-400MB → OOM 崩潰迴圈。**任何昂貴資源載入，都要先檢查便宜的前置條件再載入**（`vector_retriever.py` 目前是正確順序，別改回去）。

---

## 7. Git / 工作區現況

工作區有幾個 untracked 檔案，**都是刻意不 commit 的**：

| 檔案 | 處置 |
|------|------|
| `.claude/` | 本機工具設定（launch.json），不進 git |
| `Brief 文件讀取.zip`、`design-handoff-for-claude-design.zip` | 設計交接的壓縮檔，內容已解壓進 `design-handoff/`，冗餘 |
| `backend/__no_such_dir__/` | PR12 測試 OOM 情境時留下的殘檔，可刪（先前刪除指令被權限攔下，還沒清） |

commit 前務必確認 `backend/.env` 沒被加進去。另外 `frontend/` 若出現獨立的 `.git` 目錄要刪掉（Next.js 建立時會自動 git init），否則父 repo `git add` 會失敗——**刪 `frontend/.git`，不是根目錄的 `.git`**。

---

## 8. 驗證清單（改完東西該怎麼確認）

**後端規則改動**
```bash
cd backend && pytest tests/ -v
```
若動到 `law_references`，另跑：
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m tools.check_law_snippets
```
加上手動打 API：`POST /api/v1/check/analyze` 帶一組真實出勤資料，確認金額與違規清單合理。

**語料／檢索改動**
- `GET /api/v1/law/search?q=<關鍵字>` 確認新法條有回來
- 檢查 `raw_chunks_cache.json` 總數沒變少

**AI 回答改動**
- 真的打一次 `/api/v1/ask/chat`，看回答是 Markdown 不是 JSON、沒截斷、有引用法條
- 開源版：複製提示詞貼到 ChatGPT 看回答品質

**前端改動**
```bash
cd frontend && npm run build
```
必須 0 TypeScript 錯誤。再 `npm run dev` 逐頁點過首頁／check 三步驟／result／ask／law，看 console 無錯誤。

**上線**：commit → push 到 `master` → Render 與 Vercel 自動部署。Render 冷啟動約 30 秒，第一次打會慢。

---

## 9. 已知限制（可能是下一步工作）

- 加班費試算僅完整支援月薪制，時薪制非固定工時的倍率尚未完備
- 無登入機制，資料存 sessionStorage，重新整理即消失
- 情境詢問沒有對話記憶，每次都是全新對話
- 判決引用只顯示案號，未展開摘要
- Render 免費方案冷啟動 30 秒；開源版雖不吃 LLM quota 但仍吃 Render 額度

---

## 10. 給下一位 AI 的工作建議

1. **動手前先讀 `CLAUDE.md` 的踩坑規則**，那 14 條每一條都是實際踩過的坑，不是理論。
2. **大檔用 Edit 就地改，不要整份重輸出**（尤其 `check/page.tsx`）。
3. **保留既有的中文命名、註解與輸出格式**，不要自行重構或翻譯。
4. **法律內容要抄法條原文**，時效起算點（「自行為終了時起」vs「自知悉時起」）寫錯會直接害使用者錯過申訴期限。PR11 就抓到過這種錯。
5. **改完要更新 `progress.md`**，格式照既有 PR 段落：動機 → 修改 → 踩坑 → 驗證。
6. 回覆使用者用**繁體中文（台灣用語）**。
