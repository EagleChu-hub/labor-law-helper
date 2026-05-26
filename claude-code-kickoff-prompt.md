# 勞基法查詢小幫手 — Claude Code Kickoff Prompt

你是一位全端工程師，請根據以下規格，從零開始建立一個手機與桌機皆可用的「勞基法查詢小幫手」網站 MVP。

---

## 產品目標
讓台灣勞工可以：
1. 輸入出勤、加班、休假資料，由系統初步判斷是否疑似違反《勞動基準法》。
2. 用自然語言詢問職場情境，系統回覆法條依據、風險提示與下一步建議。

---

## 技術規格

### Frontend
- Next.js 14（App Router）
- TypeScript
- Tailwind CSS
- Lucide React（icon）
- 響應式設計：手機優先，桌機支援雙欄版型

### Backend
- FastAPI（Python）
- 暫時以 mock data 回應（真實 RAG 之後再接）
- 依照下方 API 規格建立 endpoint

### 資料夾結構
```
/
├── frontend/          # Next.js app
│   ├── app/
│   │   ├── page.tsx                    # 首頁
│   │   ├── check/
│   │   │   ├── page.tsx                # 快速判斷表單
│   │   │   └── result/page.tsx         # 判斷結果頁
│   │   ├── ask/page.tsx                # 情境詢問（聊天）頁
│   │   └── law/page.tsx                # 法條查詢頁
│   ├── components/
│   │   ├── layout/
│   │   ├── check/
│   │   ├── ask/
│   │   ├── law/
│   │   └── shared/
│   ├── types/index.ts
│   └── lib/api.ts                      # API 呼叫函式
│
└── backend/           # FastAPI app
    ├── main.py
    ├── routers/
    │   ├── check.py
    │   ├── ask.py
    │   └── law.py
    └── mock_data/
        ├── check_result.json
        ├── ask_response.json
        └── law_articles.json
```

---

## 頁面規格

### 1. 首頁 `/`
- Hero 標題：「勞基法查詢小幫手」+ 副標說明
- 2 個主 CTA：「開始輸入出勤」→ /check、「直接問問題」→ /ask
- 常見情境捷徑：最少 4 個按鈕，點擊後帶問題進入 /ask
- Footer：免責聲明一行

### 2. 快速判斷頁 `/check`
- 多步驟表單，共 3 步驟：
  - Step 1：選擇工作型態（月薪/時薪/排班制/其他）
  - Step 2：輸入本週出勤（最多 7 天，每天上下班時間、休息分鐘數、是否加班）
  - Step 3：確認並送出
- 桌機版：左側表單、右側即時摘要
- 手機版：單步驟顯示，進度條
- 送出後導向 `/check/result`

### 3. 判斷結果頁 `/check/result`
- 風險等級卡（低/中/高）+ 標題
- 疑似違規項目列表（每項含說明 + 法條引用）
- 缺少資料提醒
- 下一步 CTA：「繼續追問」→ /ask、「查法條」→ /law
- 法律免責聲明 banner

### 4. 情境詢問頁 `/ask`
- 左側：推薦題庫（桌機版顯示，手機版隱藏）
- 右側：聊天介面，使用者問題與系統回答
- 系統回答結構：初步判斷 / 法條引用卡 / 缺少資料 / 建議下一步
- 追問快捷鈕
- 底部輸入框

### 5. 法條查詢頁 `/law`
- 搜尋列
- 主題分類 tab：工時、加班、休假、工資、離職
- 搜尋結果：條號、摘要、「拿去問」按鈕
- 點擊條文後顯示全文 + 「用這條問問題」按鈕

---

## API 規格（後端需實作，前端先用 mock）

### POST /api/v1/check/analyze
Request:
```json
{
  "employment_type": "monthly_salary",
  "attendance_records": [
    {
      "date": "2026-05-18",
      "clock_in": "09:00",
      "clock_out": "21:00",
      "break_minutes": 60,
      "is_rest_day": false,
      "overtime_minutes": 120
    }
  ]
}
```
Response:
```json
{
  "summary": {
    "risk_level": "high",
    "headline": "有 2 項疑似違規風險",
    "disclaimer": "此為初步判斷，非正式法律意見"
  },
  "violations": [
    {
      "rule_id": "weekly_hours_limit",
      "status": "suspected_violation",
      "title": "每週工時可能過高",
      "explanation": "本週累計工時超過一般正常工時門檻。",
      "law_references": [
        {
          "law_name": "勞動基準法",
          "article_no": "第30條",
          "snippet": "勞工正常工作時間，每日不得超過八小時，每週不得超過四十小時。"
        }
      ],
      "missing_facts": ["是否適用變形工時制度"]
    }
  ],
  "next_actions": ["保留出勤紀錄", "可進一步詢問情境"]
}
```

### POST /api/v1/ask/chat
Request:
```json
{
  "thread_id": "thread_001",
  "message": "公司說責任制不用給加班費，這樣對嗎？"
}
```
Response:
```json
{
  "thread_id": "thread_001",
  "answer": {
    "headline": "責任制並非免除加班費的理由。",
    "summary": "勞基法第84條之1規定的責任制必須經過主管機關核定，且仍有工時保護上限。",
    "reasoning": [
      "一般所謂「責任制」若未依第84條之1核定，並不合法。",
      "即使核定，也不代表完全無工時上限。"
    ],
    "missing_facts": ["你的職務是否在84條之1核定名單內"],
    "next_suggestions": ["可查詢自己職務是否在核定名單", "可保留出勤紀錄作為後續依據"],
    "law_references": [
      {
        "law_name": "勞動基準法",
        "article_no": "第84條之1",
        "snippet": "經中央主管機關核定公告之工作者...",
        "source_url": "https://law.moj.gov.tw/"
      }
    ]
  }
}
```

### GET /api/v1/law/search?q=加班費&topic=overtime
Response:
```json
{
  "items": [
    {
      "id": "labor_act_24",
      "law_name": "勞動基準法",
      "article_no": "第24條",
      "snippet": "雇主延長勞工工作時間者，其延長工作時間之工資...",
      "source_url": "https://law.moj.gov.tw/"
    }
  ]
}
```

---

## TypeScript 型別

```ts
export type RiskLevel = 'low' | 'medium' | 'high';

export type AttendanceRecord = {
  date: string;
  clockIn: string;
  clockOut: string;
  breakMinutes: number;
  isRestDay: boolean;
  overtimeMinutes: number;
};

export type LawReference = {
  lawName: string;
  articleNo: string;
  snippet: string;
  sourceUrl?: string;
};

export type ViolationItem = {
  ruleId: string;
  status: 'compliant' | 'warning' | 'suspected_violation';
  title: string;
  explanation: string;
  references: LawReference[];
  missingFacts: string[];
};

export type CheckResult = {
  summary: {
    riskLevel: RiskLevel;
    headline: string;
    disclaimer: string;
  };
  violations: ViolationItem[];
  nextActions: string[];
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  answer?: AssistantAnswer;
};

export type AssistantAnswer = {
  headline: string;
  summary: string;
  reasoning: string[];
  missingFacts: string[];
  nextSuggestions: string[];
  references: LawReference[];
};
```

---

## 元件清單（請依此拆分）

### shared/
- `AppShell` — header + main + footer + mobile bottom nav
- `HeaderNav` — 桌機頂部導航
- `MobileBottomNav` — 手機底部導航
- `LegalDisclaimerBanner` — 免責聲明
- `LawReferenceCard` — 法條引用卡，含條號、摘要、來源、「拿去問」按鈕
- `RiskBadge` — 風險等級標籤（low/medium/high）
- `LoadingSkeleton` — variant: card | list | chat
- `EmptyState`
- `ErrorState`

### check/
- `CheckStepper` — 步驟進度條
- `EmploymentTypeSelector` — 工作型態選擇卡
- `AttendanceRecordForm` — 單日出勤輸入
- `AttendanceWeekTable` — 桌機整週表格
- `CheckLiveSummaryPanel` — 右側即時摘要
- `RiskOverviewCard` — 結果頁總覽卡
- `ViolationItemCard` — 疑似違規項目卡
- `MissingFactsCard` — 缺少資料提醒
- `NextActionCard` — 下一步建議

### ask/
- `ChatThread` — 聊天紀錄容器
- `ChatBubble` — 使用者泡泡
- `AssistantAnswerBlock` — 系統回答結構化顯示
- `FollowupSuggestionChips` — 追問快捷鈕
- `ChatInputBox` — 輸入框 + 送出
- `ExampleQuestionPanel` — 推薦題庫

### law/
- `LawSearchBar`
- `TopicFilterTabs`
- `LawSearchResultList`
- `LawArticleDetail`

---

## 視覺設計要求

- Tailwind 為主，顏色系統：
  - Primary: `teal-700`
  - Background: `slate-50`
  - Surface: white
  - Risk High: `red-600`
  - Risk Medium: `amber-500`
  - Risk Low: `green-600`
  - Border: `slate-200`
- 圓角：`rounded-2xl`（卡片）、`rounded-lg`（按鈕）
- 陰影：`shadow-sm` 正常卡片，`shadow-md` 強調卡片
- 字體：系統字體即可
- 法條引用卡：左側有 `teal-700` 色條 border
- 風險卡背景：低→`green-50`、中→`amber-50`、高→`red-50`

---

## 手機版規則

- `<768px`：隱藏左側面板、底部固定輸入框、step form 單步驟顯示
- `>=1024px`：啟用雙欄版型（判斷頁左右欄、問答頁左右欄）

---

## 重要限制

1. 每個回答都必須顯示法條來源，不得只有文字結論。
2. 若資料不足，要顯示 `MissingFactsCard`，不直接下定論。
3. 所有結果頁、問答頁必須顯示 `LegalDisclaimerBanner`。
4. `AssistantAnswerBlock` 必須分段顯示：初步判斷 / 法條依據 / 缺少資料 / 建議下一步。
5. 問答頁結果要有「繼續追問」與「看法條」CTA，形成產品閉環。

---

## 開工順序

1. 建立 Next.js 專案、Tailwind 設定、型別定義、API 呼叫層
2. AppShell、HeaderNav、MobileBottomNav
3. 首頁
4. 快速判斷表單頁（含 mock 送出）
5. 判斷結果頁（含 mock 資料）
6. 情境詢問頁（含 mock API）
7. 法條查詢頁
8. FastAPI backend mock endpoints
9. 串接前後端
10. 手機版 UX 修正

請從第 1 步開始，完成後回報，等待繼續指示。
