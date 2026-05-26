# 勞基法小幫手 🏛️

> 幫助台灣勞工快速判斷出勤是否違反勞動基準法，並估算可能少領的加班費。

輸入一週出勤紀錄（上下班時間、休息分鐘），系統根據勞基法第 24、30、32、36、37、39 條等規則自動分析，並生成 AI 律師口吻的詢問提示詞，讓你直接貼到 ChatGPT 或 Gemini 獲得詳細建議。

---

## 功能特色

- 📅 **出勤快速判斷**：日曆勾選出勤日 + 設定上下班時間，3 秒得出分析結果
- 💰 **加班費試算**：依勞基法第 24、39 條倍率試算可能少領金額（需填時薪）
- 🤖 **AI 律師提示詞**：自動生成律師口吻的詢問指令，貼到 ChatGPT/Gemini 即可深度分析
- 📚 **法條搜尋**：全文搜尋 1,727 筆法條、施行細則、相關法規與函釋
- 🔒 **隱私保護**：出勤資料只在本機運算，不傳送給任何 AI 服務

---

## 雙模式架構

本專案支援兩種模式，透過同一份 GitHub repo 部署兩個 Vercel 專案：

| 模式 | 環境變數 | AI 功能 | 適合對象 |
|------|---------|---------|---------|
| `opensource`（開源版） | `NEXT_PUBLIC_MODE=opensource` | 複製提示詞 → 貼到 ChatGPT/Gemini | 公開分享給所有勞工 |
| `private`（完整版） | `NEXT_PUBLIC_MODE=private` | 直接在網站內 AI 對話（吃 Gemini quota） | 親友私下使用 |

---

## 部署指南（不需終端機，完成後永久運行）

### 第一步：部署後端到 Render（約 5 分鐘）

1. 前往 [render.com](https://render.com) 登入（可用 GitHub 帳號登入）
2. 點 **New** → **Web Service**
3. 選 **Connect a GitHub repository** → 選 `勞基法小幫手`
4. 填入以下設定：

   | 欄位 | 值 |
   |------|-----|
   | Name | `labor-law-backend`（可自訂） |
   | Root Directory | `backend` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | `Free` |

5. 點 **Advanced** → **Add Environment Variable**，新增：

   | Key | Value |
   |-----|-------|
   | `GOOGLEAI_Studio_API_KEY` | 你的 Gemini API Key（[免費申請](https://aistudio.google.com/app/apikey)） |
   | `GEMINI_MODEL` | `gemini-2.5-flash` |

6. 點 **Create Web Service** → 等待部署完成（約 3–5 分鐘）
7. 複製 Render 給的 URL，例如 `https://labor-law-backend-xxxx.onrender.com`

> ⚠️ Render 免費方案閒置 15 分鐘後會休眠，首次請求需等約 30 秒喚醒。網站前端已內建自動重試提示，勞工使用時不會感到困惑。

---

### 第二步：部署前端到 Vercel——開源公開版（約 3 分鐘）

1. 前往 [vercel.com](https://vercel.com) 登入（可用 GitHub 帳號登入）
2. 點 **Add New Project** → **Import Git Repository** → 選 `勞基法小幫手`
3. 設定：

   | 欄位 | 值 |
   |------|-----|
   | Framework Preset | `Next.js`（自動偵測） |
   | Root Directory | `frontend` |

4. 展開 **Environment Variables**，新增：

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | 第一步取得的 Render URL |
   | `NEXT_PUBLIC_MODE` | `opensource` |

5. 點 **Deploy** → 等待完成
6. 取得 `xxx.vercel.app` 網址 → **可公開分享給所有勞工**

---

### 第三步：部署前端到 Vercel——親友完整版（約 3 分鐘）

1. 在 Vercel 再建一個新專案，**Import 同一個 GitHub repo**
2. 設定相同，但 Environment Variables 改為：

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | 同 Render URL |
   | `NEXT_PUBLIC_MODE` | `private` |

3. Deploy → 取得另一個 `xxx.vercel.app` URL → **私下分享給親友**

---

## 本機開發

### 後端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # 填入 GOOGLEAI_Studio_API_KEY
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env.local     # 修改 NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## 技術架構

```
前端（Next.js 14 + Tailwind CSS）
  └── Vercel 部署

後端（FastAPI + Python）
  ├── 規則引擎：9 條勞基法規則，不吃 LLM quota
  ├── RAG 向量搜尋：ChromaDB + BM25，1,727 筆法條語料
  └── Gemini 2.5 Flash：律師口吻 AI 對話（僅 private 模式）
       └── Render 部署
```

| 層 | 技術 |
|---|---|
| 前端 | Next.js 14 + TypeScript + Tailwind CSS |
| 後端 | FastAPI (Python 3.12) |
| 搜尋 | BM25 (rank-bm25 + jieba) + ChromaDB 向量搜尋 |
| AI | Google Gemini 2.5 Flash |

### 語料來源
- **勞動基準法**（98 條）+ **施行細則**（70 條）：來自 [law.moj.gov.tw](https://law.moj.gov.tw)
- **相關法規**（最低工資法、性別平等工作法、勞工退休金條例等）：共 1,559 筆
- **勞動部函釋**（2020 年後）

---

## 環境變數一覽

### 後端（`backend/.env`）

| 變數名稱 | 必填 | 說明 |
|---------|------|------|
| `GOOGLEAI_Studio_API_KEY` | ✅ | Google AI Studio API Key |
| `GEMINI_MODEL` | 選填 | 預設 `gemini-2.5-flash` |

### 前端（`frontend/.env.local`）

| 變數名稱 | 必填 | 說明 |
|---------|------|------|
| `NEXT_PUBLIC_API_URL` | ✅ | 後端 API URL |
| `NEXT_PUBLIC_MODE` | 選填 | `opensource`（預設）或 `private` |

---

## 申訴資源

若確認雇主違法，可透過以下管道申訴：
- 📞 **勞工諮詢專線**：1955
- 🏛️ [台北市政府勞動局申訴](https://ap.bola.gov.taipei/LZ.aspx)
- 📧 [勞動部申訴信箱](https://romeodex.osha.gov.tw/PO/WriteMail)

---

## 免責聲明

本工具提供的分析為參考性質，不構成法律意見。實際情況請洽勞動局或專業律師確認。加班費試算依勞基法倍率公式計算，實際金額以勞動契約與雇主計算為準。

## 授權

MIT License
