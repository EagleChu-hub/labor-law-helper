export type RiskLevel = "low" | "medium" | "high";
export type EmploymentType = "monthly_salary" | "hourly" | "dispatch";
export type ScheduleType = "fixed" | "shift" | "rotating";
export type LeaveType = "annual" | "sick" | "personal" | "unpaid" | "other";
export type Confidence = "high" | "medium" | "low";
export type DocType = "statute" | "enforcement_rule" | "interpretation" | "judgment" | "arbitration";
export type ViolationStatus = "compliant" | "warning" | "suspected_violation";

export interface AttendanceRecord {
  date: string;
  clock_in: string;
  clock_out: string;
  break_minutes: number;
  overtime_minutes: number;
}

export interface LeaveRecord {
  date: string;
  leave_type: LeaveType;
  hours: number;
}

export interface SalaryInfo {
  base_salary: number;
  hourly_rate?: number;
  has_overtime_pay: boolean;
}

export interface CheckRequest {
  employment_type: EmploymentType;
  schedule_type: ScheduleType;
  attendance_records: AttendanceRecord[];
  leave_records: LeaveRecord[];
  salary_info?: SalaryInfo;
  /** 0=週一 … 6=週日，預設 6（週日）為例假日（fallback） */
  mandatory_day_off_weekday: number;
  /** 0=週一 … 6=週日，預設 5（週六）為休息日（fallback） */
  regular_day_off_weekday: number;
  /** 逐日標註的例假日（YYYY-MM-DD）；非空時取代 weekday 設定 */
  mandatory_rest_dates?: string[];
  /** 逐日標註的休息日（YYYY-MM-DD）；非空時取代 weekday 設定 */
  regular_rest_dates?: string[];
  /** 國定假日補休調整：{ 原節日: 補休日 } */
  holiday_compensation_overrides?: Record<string, string>;
  /** 平日時薪（選填） */
  hourly_wage_regular?: number;
  /** 假日時薪（選填） */
  hourly_wage_holiday?: number;
  /** 使用者明確標記「與雇主約定的休息日加班」日期 */
  agreed_rest_day_ot_dates?: string[];
}

export interface LawReference {
  article_no: string;
  title: string;
  snippet: string;
  doc_type?: DocType;
  source_url: string;
}

export interface ViolationItem {
  rule_id: string;
  status: ViolationStatus;
  title: string;
  explanation: string;
  confidence: Confidence;
  law_references: LawReference[];
  missing_facts: string[];
  estimated_shortfall_ntd?: number;
  shortfall_formula?: string;
}

export interface ComputedMetrics {
  total_work_minutes: number;
  total_overtime_minutes: number;
  max_consecutive_days: number;
  avg_daily_minutes: number;
}

export interface CheckResult {
  risk_level: RiskLevel;
  headline: string;
  disclaimer: string;
  violations: ViolationItem[];
  metrics: ComputedMetrics;
  next_actions: string[];
  total_shortfall_ntd?: number;
  has_wage_input?: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AskRequest {
  message: string;
  history: ChatMessage[];
}

export interface AskResponse {
  /** 新版主要欄位：律師口吻的 Markdown，前端用 react-markdown 渲染 */
  markdown?: string;
  headline: string;
  law_references: LawReference[];
  followup_questions: string[];
  /** 以下為向後相容欄位，新版可能為空字串 */
  summary?: string;
  reasoning?: string;
  missing_facts?: string[];
  suggestions?: string[];
}

export interface LawSearchResult {
  article_no: string;
  title: string;
  snippet: string;
  doc_type: DocType;
  source_url: string;
  relevance_score: number;
}

export interface LawSearchResponse {
  results: LawSearchResult[];
  total: number;
  query: string;
}
