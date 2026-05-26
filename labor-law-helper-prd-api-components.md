# 勞基法查詢小幫手：可交給 Claude Code 開工的 PRD + API 規格 + 前端元件清單

本文件目標是讓 Claude Code、前端工程師、後端工程師可以直接進入實作。內容分成三塊：
1. **PRD（產品需求文件）**
2. **API 規格草案**
3. **前端元件清單與狀態規格**

---

# 1. PRD

## 1.1 產品名稱
勞基法查詢小幫手（Labor Law Helper）

## 1.2 產品目標
打造一個可在手機與電腦上使用的網站，讓勞工能以兩種方式取得幫助：
- **結構化輸入**：輸入出勤、加班、休假、薪資等資料，讓系統初步判斷是否可能違反《勞動基準法》。
- **自然語言詢問**：輸入職場情境問題，由系統提供法條依據、風險提示與下一步建議。

## 1.3 背景
參考專案顯示，現有系統多半只做「勞基法問答」或「RAG 聊天機器人」，但一般勞工常見需求其實是：
- 我最近這週/這月的班表有沒有問題？
- 公司這種排班方式合理嗎？
- 這樣算不算加班？
- 我該保留哪些證據？

因此本產品不是單純法條查詢，而是結合：
- 規則判斷引擎
- 法條 RAG 問答
- 情境分析
- 結果摘要與下一步建議

## 1.4 目標使用者

### 核心使用者
- 一般受僱勞工
- 排班制、輪班制、服務業、零售業、餐飲業工作者
- 對勞基法不熟，但懷疑自己被違法對待的人

### 次要使用者
- 工會或勞權倡議者
- 協助朋友檢查班表的人
- 對勞基法主題有初步查詢需求的人

## 1.5 使用情境

### 情境 A：班表違規檢查
使用者想知道自己最近一週是否連續上班過久、是否工時過長、是否休息日不足。

### 情境 B：加班費疑問
使用者想知道自己這種情況是否應有加班費，或公司說法是否合理。

### 情境 C：自然語言追問
使用者先拿到判斷結果後，繼續問：「如果公司說這是責任制怎麼辦？」

### 情境 D：法條直接查詢
使用者只想查工時、休假、加班相關法條與摘要。

## 1.6 核心價值主張
- 用生活語言也能問。
- 輸入班表就能做初步判斷。
- 每個結論都盡量附法條依據。
- 不是只有答案，還有「下一步怎麼做」。

## 1.7 MVP 範圍

### 需要做
1. 首頁
2. 快速判斷流程（基本資料、出勤輸入、休假/加班輸入、結果頁）
3. 情境詢問頁（聊天式）
4. 法條查詢頁
5. 勞基法單一法源檢索
6. 工時/加班/休假 三大主題規則判斷
7. 法條引用顯示
8. 缺少資料提醒
9. 免責聲明與資料來源頁

### 先不做
1. 使用者登入
2. 永久儲存個人案件
3. 多法規整合
4. PDF 正式報告匯出
5. 語音輸入
6. 多語系
7. 真正法律意見或律師媒合

## 1.8 成功指標（MVP）
- 使用者能在 3 分鐘內完成一次快速判斷。
- 使用者能看懂結果頁的風險摘要與法條依據。
- 使用者在結果頁後願意繼續追問，代表規則判斷與聊天功能有串起來。
- 問答結果至少附一個可追溯的法條來源。

## 1.9 產品頁面
- `/` 首頁
- `/check` 快速判斷入口
- `/check/result` 判斷結果
- `/ask` 情境詢問
- `/law` 法條查詢
- `/guide` 使用說明
- `/disclaimer` 免責聲明
- `/sources` 資料來源

## 1.10 功能需求

### F1. 首頁導流
- 顯示兩個主要入口：開始輸入出勤、直接問問題。
- 顯示常見情境捷徑。

### F2. 快速判斷
- 可輸入工作型態、出勤時間、休息時間、休假資訊、加班資訊。
- 系統可計算每日工時、每週工時、連續上班天數、疑似休息日不足。
- 結果要顯示風險等級與法條引用。

### F3. 情境詢問
- 支援單輪與多輪對話。
- 回答需分段顯示：初步判斷、法條依據、還缺什麼資訊、建議下一步。
- 若問題可被結構化處理，系統要引導去快速判斷頁。

### F4. 法條查詢
- 支援條號查詢。
- 支援關鍵字搜尋。
- 支援主題分類瀏覽。

### F5. 結果延伸操作
- 在結果頁可點擊「繼續追問」。
- 在法條卡可點擊「拿這條去問」。

## 1.11 非功能需求
- 手機優先、桌機可用。
- 頁面載入快，避免大而重的 UI 框架。
- 回答應可追溯來源。
- 對高風險法律判斷採保守策略。
- 若資料不足，需回傳 missing facts，不做武斷結論。

## 1.12 約束條件
- MVP 不使用帳號系統。
- 儲存狀態以 session/in-memory 為主。
- 法條資料需可更新。
- 不得把回答表述成正式法律意見。

## 1.13 驗收標準

### 快速判斷驗收
- 可輸入至少 7 天班表資料。
- 能回傳風險等級。
- 能列出至少 1 個對應法條。
- 能列出至少 1 個缺少資料提醒（若資料不足）。

### 問答驗收
- 問題送出後可收到含法條引用的回答。
- 多輪追問可保留前文上下文。
- 無關勞動法問題要做禮貌拒答。

### 法條查詢驗收
- 搜尋關鍵字能回傳條號、摘要與全文入口。
- 點法條可帶入問答模式。

---

# 2. API 規格

Base URL:
```text
/api/v1
```

資料格式：
- Request: `application/json`
- Response: `application/json`

錯誤格式統一：
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "attendance records are required",
    "details": {}
  }
}
```

---

## 2.1 Health Check

### GET `/health`

#### Response 200
```json
{
  "status": "ok",
  "service": "labor-law-helper-api",
  "version": "0.1.0"
}
```

---

## 2.2 快速判斷 API

### POST `/check/analyze`
根據使用者輸入的出勤、休假、加班資料，回傳初步風險判斷。

#### Request Body
```json
{
  "employment_type": "monthly_salary",
  "schedule_type": "shift",
  "timezone": "Asia/Taipei",
  "attendance_records": [
    {
      "date": "2026-05-18",
      "clock_in": "09:00",
      "clock_out": "19:30",
      "break_minutes": 60,
      "is_holiday": false,
      "is_rest_day": false,
      "overtime_minutes": 90,
      "notes": "門市盤點"
    }
  ],
  "leave_records": [
    {
      "date": "2026-05-20",
      "type": "annual_leave",
      "hours": 8
    }
  ],
  "salary_info": {
    "base_salary": 32000,
    "hourly_rate": null,
    "has_overtime_pay": true,
    "payroll_notes": "公司說責任制"
  },
  "context": {
    "industry": "retail",
    "company_size": "small",
    "flexible_working_hours": false
  }
}
```

#### Response 200
```json
{
  "summary": {
    "risk_level": "high",
    "headline": "有 3 項疑似違規風險",
    "disclaimer": "此為初步判斷，非正式法律意見"
  },
  "violations": [
    {
      "rule_id": "weekly_hours_limit",
      "status": "suspected_violation",
      "title": "每週工時可能過高",
      "explanation": "本週累計工時 52 小時，已高於一般正常工時判斷門檻。",
      "confidence": 0.82,
      "law_references": [
        {
          "law_name": "勞動基準法",
          "article_no": "第30條",
          "snippet": "勞工正常工作時間..."
        }
      ],
      "missing_facts": [
        "是否適用變形工時制度"
      ]
    }
  ],
  "computed_metrics": {
    "total_work_minutes": 3120,
    "total_overtime_minutes": 420,
    "consecutive_work_days": 7
  },
  "next_actions": [
    "確認公司是否有合法變形工時制度",
    "保留打卡紀錄與班表截圖",
    "可改到情境詢問頁進一步追問"
  ]
}
```

#### Validation Rules
- `attendance_records` 至少 1 筆。
- `clock_in`、`clock_out` 必須是 `HH:mm`。
- `break_minutes` 不得小於 0。
- `employment_type` enum: `monthly_salary | hourly | dispatch | other`
- `schedule_type` enum: `fixed | shift | rotating | other`

---

## 2.3 問答 API

### POST `/ask/chat`
送出情境問題，取得法律問答回覆。

#### Request Body
```json
{
  "thread_id": "thread_001",
  "message": "公司要求我下班後回主管訊息，這樣算工時嗎？",
  "context": {
    "source": "direct_ask",
    "check_result_id": null
  }
}
```

#### Response 200
```json
{
  "thread_id": "thread_001",
  "answer": {
    "category": "working_hours",
    "headline": "下班後是否算工時，要看是否仍受雇主指揮監督。",
    "summary": "若公司要求持續待命、即時回覆工作訊息，可能涉及工時認定問題。",
    "reasoning": [
      "是否算工時，通常與是否仍受雇主指揮監督有關。",
      "若回訊息是工作必要且持續發生，應進一步檢視是否屬勞務提供的一部分。"
    ],
    "missing_facts": [
      "是否有明確規定必須即時回覆",
      "是否影響休息時間"
    ],
    "next_suggestions": [
      "你可以補充公司是否要求限時回覆",
      "你也可以改用快速判斷模式整理最近一週的加班情況"
    ],
    "law_references": [
      {
        "law_name": "勞動基準法",
        "article_no": "第30條",
        "snippet": "勞工正常工作時間...",
        "source_url": "https://law.moj.gov.tw/..."
      }
    ]
  },
  "routing": {
    "is_labor_related": true,
    "intent": "working_hours_question"
  }
}
```

### POST `/ask/examples`
回傳推薦題庫。

#### Response 200
```json
{
  "examples": [
    {
      "id": "ex_001",
      "category": "overtime",
      "question": "公司叫我提早到店準備，但不算上班時間，這樣可以嗎？"
    },
    {
      "id": "ex_002",
      "category": "leave",
      "question": "特休沒休完，公司可以直接歸零嗎？"
    }
  ]
}
```

---

## 2.4 法條查詢 API

### GET `/law/search?q=加班費&topic=overtime&page=1&page_size=10`

#### Response 200
```json
{
  "query": "加班費",
  "topic": "overtime",
  "page": 1,
  "page_size": 10,
  "total": 2,
  "items": [
    {
      "id": "labor_act_24",
      "law_name": "勞動基準法",
      "article_no": "第24條",
      "title": "延長工作時間工資",
      "snippet": "雇主延長勞工工作時間者...",
      "source_url": "https://law.moj.gov.tw/..."
    }
  ]
}
```

### GET `/law/articles/{id}`

#### Response 200
```json
{
  "id": "labor_act_24",
  "law_name": "勞動基準法",
  "article_no": "第24條",
  "title": "延長工作時間工資",
  "content": "雇主延長勞工工作時間者，其延長工作時間之工資依下列標準加給之...",
  "topic_tags": ["overtime", "wages"],
  "updated_at": "2026-01-01",
  "source_url": "https://law.moj.gov.tw/..."
}
```

### GET `/law/topics`

#### Response 200
```json
{
  "topics": [
    { "id": "working_hours", "label": "工時" },
    { "id": "overtime", "label": "加班" },
    { "id": "leave", "label": "休假" },
    { "id": "wages", "label": "工資" },
    { "id": "termination", "label": "離職與資遣" }
  ]
}
```

---

## 2.5 前端輔助 API

### GET `/config/bootstrap`
提供前端初始化需要的設定。

#### Response 200
```json
{
  "app_name": "勞基法查詢小幫手",
  "supported_topics": ["working_hours", "overtime", "leave"],
  "risk_levels": ["low", "medium", "high"],
  "legal_disclaimer": "本工具提供初步資訊整理與法條查詢，不構成正式法律意見。"
}
```

---

# 3. 前端元件清單

本區塊目標是讓 Claude Code 可以直接依元件拆分開始建立前端結構。

---

## 3.1 Layout 類元件

### `AppShell`
全站外框，負責 header、main、footer、mobile nav。

**Props**
```ts
{
  children: ReactNode;
  currentRoute: string;
}
```

### `HeaderNav`
頂部導覽列。

**Props**
```ts
{
  currentRoute: string;
  onNavigate: (route: string) => void;
}
```

### `MobileBottomNav`
手機版底部導航。

**Props**
```ts
{
  currentRoute: string;
  onNavigate: (route: string) => void;
}
```

---

## 3.2 首頁元件

### `HeroEntryCard`
首頁兩張大卡之一，用於導流。

**Props**
```ts
{
  title: string;
  description: string;
  icon: string;
  ctaLabel: string;
  onClick: () => void;
}
```

### `ScenarioShortcutList`
常見問題捷徑列表。

**Props**
```ts
{
  items: { id: string; label: string; onClick: () => void }[];
}
```

---

## 3.3 快速判斷元件

### `CheckStepper`
多步驟表單的步驟列。

**Props**
```ts
{
  currentStep: number;
  steps: { key: string; label: string }[];
}
```

### `EmploymentTypeSelector`
選擇工作型態。

**Props**
```ts
{
  value: string | null;
  onChange: (value: string) => void;
}
```

### `AttendanceRecordForm`
輸入單日班表。

**Props**
```ts
{
  record: AttendanceRecord;
  onChange: (record: AttendanceRecord) => void;
  onRemove?: () => void;
}
```

### `AttendanceWeekTable`
桌機版一週班表輸入表格。

**Props**
```ts
{
  records: AttendanceRecord[];
  onChange: (records: AttendanceRecord[]) => void;
}
```

### `SalaryInfoForm`
薪資與加班資訊輸入區。

**Props**
```ts
{
  value: SalaryInfo;
  onChange: (value: SalaryInfo) => void;
}
```

### `LeaveRecordForm`
休假資訊輸入。

**Props**
```ts
{
  items: LeaveRecord[];
  onChange: (items: LeaveRecord[]) => void;
}
```

### `CheckLiveSummaryPanel`
快速判斷頁右側即時摘要。

**Props**
```ts
{
  summary: {
    riskLevel?: 'low' | 'medium' | 'high';
    hints: string[];
    missingFacts: string[];
  };
  onPreviewResult?: () => void;
}
```

---

## 3.4 結果頁元件

### `RiskOverviewCard`
顯示總體風險結果。

**Props**
```ts
{
  riskLevel: 'low' | 'medium' | 'high';
  headline: string;
  disclaimer: string;
}
```

### `ViolationItemCard`
單一疑似違規項目卡。

**Props**
```ts
{
  title: string;
  status: 'compliant' | 'warning' | 'suspected_violation';
  explanation: string;
  confidence: number;
  references: LawReference[];
  missingFacts: string[];
}
```

### `LawReferenceCard`
顯示法條引用。

**Props**
```ts
{
  lawName: string;
  articleNo: string;
  snippet: string;
  sourceUrl?: string;
  onAskWithThisLaw?: () => void;
}
```

### `ComputedMetricsPanel`
顯示工時計算摘要。

**Props**
```ts
{
  metrics: {
    totalWorkMinutes?: number;
    totalOvertimeMinutes?: number;
    consecutiveWorkDays?: number;
  };
}
```

### `MissingFactsCard`
資料不足提醒。

**Props**
```ts
{
  items: string[];
}
```

### `NextActionCard`
下一步建議與 CTA。

**Props**
```ts
{
  actions: string[];
  onAskFollowup?: () => void;
  onGoLawSearch?: () => void;
}
```

---

## 3.5 問答頁元件

### `ChatThread`
整個聊天紀錄區塊。

**Props**
```ts
{
  messages: ChatMessage[];
  isLoading: boolean;
}
```

### `ChatBubble`
單一對話泡泡。

**Props**
```ts
{
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}
```

### `AssistantAnswerBlock`
系統回答的結構化顯示元件。

**Props**
```ts
{
  headline: string;
  summary: string;
  reasoning: string[];
  missingFacts: string[];
  nextSuggestions: string[];
  references: LawReference[];
}
```

### `FollowupSuggestionChips`
追問捷徑。

**Props**
```ts
{
  items: string[];
  onSelect: (value: string) => void;
}
```

### `ChatInputBox`
輸入框。

**Props**
```ts
{
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}
```

### `ExampleQuestionPanel`
推薦題庫。

**Props**
```ts
{
  items: { id: string; category: string; question: string }[];
  onSelect: (question: string) => void;
}
```

---

## 3.6 法條查詢頁元件

### `LawSearchBar`
搜尋列。

**Props**
```ts
{
  query: string;
  onChange: (value: string) => void;
  onSearch: () => void;
}
```

### `TopicFilterTabs`
主題切換 tab。

**Props**
```ts
{
  topics: { id: string; label: string }[];
  selected: string | null;
  onChange: (topicId: string | null) => void;
}
```

### `LawSearchResultList`
搜尋結果列表。

**Props**
```ts
{
  items: LawSearchItem[];
  onSelectItem: (id: string) => void;
}
```

### `LawArticleDetail`
條文詳情。

**Props**
```ts
{
  article: LawArticle | null;
  onAskWithThisLaw?: (article: LawArticle) => void;
}
```

---

## 3.7 通用狀態元件

### `LoadingSkeleton`
所有頁面通用的 loading UI。

**Props**
```ts
{
  variant: 'card' | 'list' | 'chat' | 'form';
}
```

### `EmptyState`
空狀態。

**Props**
```ts
{
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}
```

### `ErrorState`
錯誤狀態。

**Props**
```ts
{
  title: string;
  message: string;
  onRetry?: () => void;
}
```

### `LegalDisclaimerBanner`
法律免責聲明。

**Props**
```ts
{
  text: string;
  compact?: boolean;
}
```

---

# 4. TypeScript 型別草案

```ts
export type RiskLevel = 'low' | 'medium' | 'high';

export type AttendanceRecord = {
  date: string;
  clockIn: string;
  clockOut: string;
  breakMinutes: number;
  isHoliday: boolean;
  isRestDay: boolean;
  overtimeMinutes: number;
  notes?: string;
};

export type LeaveRecord = {
  date: string;
  type: string;
  hours: number;
};

export type SalaryInfo = {
  baseSalary: number | null;
  hourlyRate: number | null;
  hasOvertimePay: boolean | null;
  payrollNotes?: string;
};

export type LawReference = {
  lawName: string;
  articleNo: string;
  snippet: string;
  sourceUrl?: string;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt?: string;
};

export type LawSearchItem = {
  id: string;
  lawName: string;
  articleNo: string;
  title: string;
  snippet: string;
  sourceUrl?: string;
};

export type LawArticle = {
  id: string;
  lawName: string;
  articleNo: string;
  title: string;
  content: string;
  topicTags: string[];
  updatedAt?: string;
  sourceUrl?: string;
};
```

---

# 5. 建議給 Claude Code 的開工順序

## Phase 1: 前端骨架
1. 建立 app shell
2. 建立首頁
3. 建立快速判斷表單頁
4. 建立結果頁靜態版
5. 建立情境詢問頁靜態版
6. 建立法條查詢頁靜態版

## Phase 2: Mock API 串接
1. 建立 mock json
2. 串接 `/check/analyze`
3. 串接 `/ask/chat`
4. 串接 `/law/search` 與 `/law/articles/{id}`

## Phase 3: 後端功能
1. 實作法條資料 schema
2. 實作 search API
3. 實作 ask API
4. 實作 rule engine analyze API

## Phase 4: UX 打磨
1. loading / error / empty state
2. mobile UX
3. results-to-chat flow
4. law-to-chat flow

---

# 6. 可直接貼給 Claude Code 的任務說明

```text
請根據這份 PRD + API spec + component inventory，建立一個手機與桌機皆可用的勞基法查詢小幫手網站 MVP。

技術方向：
- Frontend: Next.js / React + TypeScript + Tailwind
- Backend: FastAPI
- 先用 mock data 完成前端流程，再逐步串接真實 API

請先完成：
1. App shell 與路由
2. 首頁
3. 快速判斷頁（多步驟表單）
4. 判斷結果頁
5. 情境詢問頁
6. 法條查詢頁
7. 共用元件：RiskOverviewCard、LawReferenceCard、ChatInputBox、LoadingSkeleton、LegalDisclaimerBanner

要求：
- 手機優先
- 所有重要結果都要保留法條引用區塊
- 結果頁需能導到問答頁
- 法條查詢頁需能導到問答頁
- 高風險結果要有清楚視覺層級
- 不要把內容寫成正式法律意見
```

---

# 7. 最後交付說明
這份文件可直接作為：
- Claude Code 開工規格
- 前端與後端切分依據
- sprint planning 初版文件
- 設計與工程對齊文件
