/**
 * 分流導引（/triage）的內容與規則。純 TypeScript，無 React 相依。
 *
 * ⛔ 設計前提：本頁的使用者是**資訊能力最弱的一群**——只有手機、下班很累、
 *    看到「調解」「執行名義」就關掉。所以：
 *    - 表層文字（question / option.label / plainName / reason）**不得出現法律術語**
 *    - 法條原文、五路線比較一律收進「想知道為什麼？」展開層
 *
 * ⛔ 為什麼不是決策樹：核心論點是「公法路線（罰雇主）與私法路線（拿你的錢）**可以並行**」，
 *    最常見的使用者，正確答案是兩條同時走。樹只能走到一個葉子，會逼出假葉子。
 *    且「送件前先固定證據」對三條路線都成立，在樹裡會被複製多份然後各自漂移。
 *    → 內容用資料，分流用底下 deriveTriage 的明確分支（可回話「因為你選了 X，所以 Y」）。
 */

// ─────────────────────────────────────────────
// 法條：⛔ quote 一律逐字，永不改寫（見 CLAUDE.md 開頭鐵則）
// ─────────────────────────────────────────────
export interface StatuteRef {
  key: string;
  article_no: string;
  quote: string;
  source_url: string;
  /** false → 畫面標「待查證」，且**不得進入 AI 提示詞** */
  verified: boolean;
}

const moj = (pcode: string, flno: string) =>
  `https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=${pcode}&flno=${flno}`;

const LSA = "N0030001"; // 勞動基準法
const SDA = "N0020007"; // 勞資爭議處理法
const LIA = "B0010064"; // 勞動事件法
const EIA = "N0050021"; // 就業保險法

/** 全部於 2026-08-30 以語料庫或 taiwan-law MCP 逐字覆核 */
export const STATUTES: Record<string, StatuteRef> = {
  LSA74_1: {
    key: "LSA74_1",
    article_no: "勞動基準法第 74 條第 1 項",
    quote: "勞工發現事業單位違反本法及其他勞工法令規定時，得向雇主、主管機關或檢查機構申訴。",
    source_url: moj(LSA, "74"),
    verified: true,
  },
  LSA74_2: {
    key: "LSA74_2",
    article_no: "勞動基準法第 74 條第 2 項",
    quote:
      "雇主不得因勞工為前項申訴，而予以解僱、降調、減薪、損害其依法令、契約或習慣上所應享有之權益，或其他不利之處分。",
    source_url: moj(LSA, "74"),
    verified: true,
  },
  LSA74_3: {
    key: "LSA74_3",
    article_no: "勞動基準法第 74 條第 3 項",
    quote: "雇主為前項行為之一者，無效。",
    source_url: moj(LSA, "74"),
    verified: true,
  },
  LSA74_4: {
    key: "LSA74_4",
    article_no: "勞動基準法第 74 條第 4 項",
    quote:
      "主管機關或檢查機構於接獲第一項申訴後，應為必要之調查，並於六十日內將處理情形，以書面通知勞工。",
    source_url: moj(LSA, "74"),
    verified: true,
  },
  LSA74_5: {
    key: "LSA74_5",
    article_no: "勞動基準法第 74 條第 5 項",
    quote: "主管機關或檢查機構應對申訴人身分資料嚴守秘密，不得洩漏足以識別其身分之資訊。",
    source_url: moj(LSA, "74"),
    verified: true,
  },
  LSA30_6: {
    key: "LSA30_6",
    article_no: "勞動基準法第 30 條第 6 項",
    quote:
      "前項出勤紀錄，應逐日記載勞工出勤情形至分鐘為止。勞工向雇主申請其出勤紀錄副本或影本時，雇主不得拒絕。",
    source_url: moj(LSA, "30"),
    verified: true,
  },
  SDA8: {
    key: "SDA8",
    article_no: "勞資爭議處理法第 8 條",
    quote:
      "勞資爭議在調解、仲裁或裁決期間，資方不得因該勞資爭議事件而歇業、停工、終止勞動契約或為其他不利於勞工之行為；勞方不得因該勞資爭議事件而罷工或為其他爭議行為。",
    source_url: moj(SDA, "8"),
    verified: true,
  },
  SDA23: {
    key: "SDA23",
    article_no: "勞資爭議處理法第 23 條",
    quote:
      "勞資爭議經調解成立者，視為爭議雙方當事人間之契約；當事人一方為工會時，視為當事人間之團體協約。",
    source_url: moj(SDA, "23"),
    verified: true,
  },
  SDA59: {
    key: "SDA59",
    article_no: "勞資爭議處理法第 59 條",
    quote:
      "勞資爭議經調解成立或仲裁者，依其內容當事人一方負私法上給付之義務，而不履行其義務時，他方當事人得向該管法院聲請裁定強制執行並暫免繳裁判費；於聲請強制執行時，並暫免繳執行費。前項聲請事件，法院應於七日內裁定之。",
    source_url: moj(SDA, "59"),
    verified: true,
  },
  SDA61: {
    key: "SDA61",
    article_no: "勞資爭議處理法第 61 條",
    quote:
      "依本法成立之調解，經法院裁定駁回強制執行聲請者，視為調解不成立。但依前條第二款規定駁回，或除去經駁回強制執行之部分亦得成立者，不適用之。",
    source_url: moj(SDA, "61"),
    verified: true,
  },
  LIA26: {
    key: "LIA26",
    article_no: "勞動事件法第 26 條",
    quote: "勞動調解，經當事人合意，並記載於調解筆錄時成立。前項調解成立，與確定判決有同一之效力。",
    source_url: moj(LIA, "26"),
    verified: true,
  },
  LIA16: {
    key: "LIA16",
    article_no: "勞動事件法第 16 條",
    quote:
      "勞動事件，除有下列情形之一者外，於起訴前，應經法院行勞動調解程序：一、有民事訴訟法第四百零六條第一項第二款、第四款、第五款所定情形之一。二、因性別平等工作法第十二條所生爭議。前項事件當事人逕向法院起訴者，視為調解之聲請。",
    source_url: moj(LIA, "16"),
    verified: true,
  },
  LIA12: {
    key: "LIA12",
    article_no: "勞動事件法第 12 條第 1 項",
    quote:
      "因確認僱傭關係或給付工資、退休金或資遣費涉訟，勞工或工會起訴或上訴，暫免徵收裁判費三分之二。",
    source_url: moj(LIA, "12"),
    verified: true,
  },
  LIA38: {
    key: "LIA38",
    article_no: "勞動事件法第 38 條",
    quote: "出勤紀錄內記載之勞工出勤時間，推定勞工於該時間內經雇主同意而執行職務。",
    source_url: moj(LIA, "38"),
    verified: true,
  },
  // ⛔ 十日不變期間——整個流程裡最貴的一個坑：不動作＝答應
  LIA29: {
    key: "LIA29",
    article_no: "勞動事件法第 29 條第 2、3 項",
    quote:
      "當事人或參加調解之利害關係人，對於前項方案，得於送達或受告知日後十日之不變期間內，提出異議。於前項期間內合法提出異議者，視為調解不成立，法院並應告知或通知當事人及參加調解之利害關係人；未於前項期間內合法提出異議者，視為已依該方案成立調解。",
    source_url: moj(LIA, "29"),
    verified: true,
  },
  // 申請調解的三條：管轄／應載明事項／調解方式
  SDA9: {
    key: "SDA9",
    article_no: "勞資爭議處理法第 9 條第 1 項",
    quote:
      "勞資爭議當事人一方申請調解時，應向勞方當事人勞務提供地之直轄市或縣（市）主管機關提出調解申請書。",
    source_url: moj(SDA, "9"),
    verified: true,
  },
  SDA10: {
    key: "SDA10",
    article_no: "勞資爭議處理法第 10 條",
    quote:
      "調解之申請，應提出調解申請書，並載明下列事項：一、當事人姓名、性別、年齡、職業及住所或居所；如為法人、雇主團體或工會時，其名稱、代表人及事務所或營業所；有代理人者，其姓名、名稱及住居所或事務所。二、請求調解事項。三、依第十一條第一項選定之調解方式。",
    source_url: moj(SDA, "10"),
    verified: true,
  },
  SDA11: {
    key: "SDA11",
    article_no: "勞資爭議處理法第 11 條第 1 項",
    quote:
      "直轄市或縣（市）主管機關受理調解之申請，應依申請人之請求，以下列方式之一進行調解：一、指派調解人。二、組成勞資爭議調解委員會（以下簡稱調解委員會）。",
    source_url: moj(SDA, "11"),
    verified: true,
  },
  // 非自願離職證明的逃生門
  EIA25_3: {
    key: "EIA25_3",
    article_no: "就業保險法第 25 條第 3 項",
    quote:
      "第一項離職證明文件，指由投保單位或直轄市、縣（市）主管機關發給之證明；其取得有困難者，得經公立就業服務機構之同意，以書面釋明理由代替之。",
    source_url: moj(EIA, "25"),
    verified: true,
  },
  LSA19: {
    key: "LSA19",
    article_no: "勞動基準法第 19 條",
    quote: "勞動契約終止時，勞工如請求發給服務證明書，雇主或其代理人不得拒絕。",
    source_url: moj(LSA, "19"),
    verified: true,
  },
};

// ─────────────────────────────────────────────
// 五條路線
// ─────────────────────────────────────────────
export type PathId = "internal" | "agency" | "admin_mediation" | "court_mediation" | "litigation";
/** 公法＝罰雇主；私法＝拿你的錢。把產品論點寫進型別。 */
export type Track = "public" | "private";

export interface ProcedurePath {
  id: PathId;
  track: Track;
  /** 正式名稱，只在展開層出現 */
  name: string;
  /** ★ 表層用的白話名，不得有法律術語 */
  plainName: string;
  where: string;
  effect: string;
  /** ← 負空間才是本頁的價值：講清楚這條路「不能」幫你做什麼 */
  cannotDo?: string;
  /** ⛔ 不寫金額數字（民訴 77-20 級距本次查不到原文） */
  cost: string;
  prerequisites?: PathId[];
  statutes: string[];
}

export const PATHS: Record<PathId, ProcedurePath> = {
  internal: {
    id: "internal",
    track: "public",
    name: "向雇主申訴",
    plainName: "直接跟公司反映",
    where: "公司內部（主管、人資、意見信箱）",
    effect: "留下日期紀錄，證明你有先講過",
    cannotDo: "公司可以不理你。這一步幾乎沒有強制力。",
    cost: "免費",
    statutes: ["LSA74_1", "LSA74_2", "LSA74_3"],
  },
  agency: {
    id: "agency",
    track: "public",
    name: "向勞工局申訴／申請勞動檢查",
    plainName: "請政府去查公司",
    where: "你上班所在地的縣市政府勞工局（勞動局）",
    effect: "政府會派人去查，查到違法會開罰單給公司",
    cannotDo: "⛔ 罰單的錢是繳給國庫的，不會變成你的錢。要拿錢要另外走下面那條。",
    cost: "免費",
    statutes: ["LSA74_1", "LSA74_4", "LSA74_5"],
  },
  admin_mediation: {
    id: "admin_mediation",
    track: "private",
    name: "勞資爭議調解",
    plainName: "請政府找雙方坐下來談",
    where: "你上班所在地的縣市政府勞工局",
    effect: "談成了雙方都要照做。對方賴帳，可以請法院出面強制他付",
    cannotDo: "談不成就結束，不會有人幫你判誰對誰錯。",
    cost: "多數縣市不收費，實際請洽當地勞工局",
    statutes: ["SDA23", "SDA59", "SDA61", "SDA8"],
  },
  court_mediation: {
    id: "court_mediation",
    track: "private",
    name: "法院勞動調解",
    plainName: "請法院找雙方坐下來談",
    where: "地方法院勞動法庭",
    effect: "★ 談成了跟法院判決一樣有力，對方不付錢可以直接請法院扣他的錢",
    cannotDo: "要跑法院一趟，流程比在勞工局談正式一些。",
    cost: "聲請費用依標的金額而定，以法院公告為準",
    statutes: ["LIA26", "LIA38"],
  },
  litigation: {
    id: "litigation",
    track: "private",
    name: "訴訟",
    plainName: "打官司",
    where: "地方法院勞動法庭",
    effect: "法官判決",
    cannotDo: "⛔ 不能直接打。法律規定起訴前要先經過法院的調解程序。",
    cost: "部分費用可暫時不用先繳，但不是全免（詳見下方法條）",
    prerequisites: ["court_mediation"],
    statutes: ["LIA16", "LIA12"],
  },
};

// ─────────────────────────────────────────────
// 提醒（Job B：入口自保）
// ─────────────────────────────────────────────
export type AdvisoryId =
  | "freeze_evidence"
  | "anonymity_limits"
  | "retaliation_void"
  | "sixty_day_notice"
  | "mediation_shield"
  | "ten_day_trap"
  | "separation_certificate"
  | "no_limitation_check";

export interface TriageAdvisory {
  id: AdvisoryId;
  severity: "stop" | "warn" | "info";
  /**
   * ★ 載重欄位：legal＝有法條撐；practice＝實務判斷。
   * ⛔ kind === "practice" 時 statutes 必須是空陣列——
   *    這樣「會露餡的情境」這種經驗談，在型別上就不可能掛上法條，
   *    也就不會被敵意讀者抓來反打。
   */
  kind: "legal" | "practice";
  title: string;
  body: string[];
  statutes: string[];
}

export const ADVISORIES: Record<AdvisoryId, TriageAdvisory> = {
  freeze_evidence: {
    id: "freeze_evidence",
    severity: "stop",
    kind: "practice",
    title: "先把資料存下來，再去送件",
    body: [
      "送出去之後，公司就知道有人在查了。",
      "紀錄可能被改、班表可能被重編、你的系統帳號可能被關掉。",
      "先把手邊有的東西拍照或截圖，存到自己的手機或雲端。",
    ],
    statutes: [],
  },
  anonymity_limits: {
    id: "anonymity_limits",
    severity: "warn",
    kind: "legal",
    title: "「匿名」保護的是政府不能說，不是公司猜不到",
    body: [
      "法律規定承辦人員不能洩漏你的身分。",
      "但如果全公司只有你被那樣排班，公司還是猜得到。",
      "所以重點不是能不能匿名，是被知道之後你站不站得住。",
    ],
    statutes: ["LSA74_5"],
  },
  retaliation_void: {
    id: "retaliation_void",
    severity: "warn",
    kind: "legal",
    title: "公司因為這件事整你，那個處分是無效的",
    body: [
      "不是「公司會被罰」而已——那個減薪、那個降職，法律上自始不生效力。",
      "意思是你可以主張：原本的條件還在，請照原本的給。",
    ],
    statutes: ["LSA74_2", "LSA74_3"],
  },
  sixty_day_notice: {
    id: "sixty_day_notice",
    severity: "info",
    kind: "legal",
    title: "政府有六十天的期限要書面回覆你",
    body: [
      "很多人抱怨「申訴好幾個月都沒消息」。",
      "法律規定機關要在六十天內用書面通知你處理情形。",
      "超過了，你可以拿這一條去催。",
    ],
    statutes: ["LSA74_4"],
  },
  mediation_shield: {
    id: "mediation_shield",
    severity: "info",
    kind: "legal",
    title: "談的期間，公司不能趁機動你",
    body: [
      "在調解進行的期間，公司不可以因為這件事就把你解僱或做其他對你不利的事。",
      "這是跟前面那條不一樣的另一道保護，兩個可以一起用。",
    ],
    statutes: ["SDA8"],
  },
  // ⛔ 整個流程裡最貴的一個坑。只適用「法院」勞動調解，不適用勞工局的行政調解
  //    （後者依勞資爭議處理法 23 條需雙方合意，沒有這種自動成立機制）。
  ten_day_trap: {
    id: "ten_day_trap",
    severity: "stop",
    kind: "legal",
    title: "⛔ 收到法院的方案後，十天內不講話就等於答應",
    body: [
      "法院調解如果雙方談不攏，法官那邊會直接提出一個方案給你。",
      "你收到之後有十天可以說「我不同意」。",
      "十天內沒有動作，法律上就當作你已經同意了，效力跟判決一樣。",
      "這十天不能延長，過了也沒有補救。收到任何法院文件，先看日期。",
    ],
    statutes: ["LIA29"],
  },
  // ★ 8/26 曾因查不到原文而擱置，本次於語料庫查得就業保險法 25 條 3 項
  separation_certificate: {
    id: "separation_certificate",
    severity: "warn",
    kind: "legal",
    title: "公司不給非自願離職證明，還有兩條路",
    body: [
      "這張紙關係到你能不能領失業給付，很多人卡在這裡。",
      "① 先跟公司要。",
      "② 公司不給——縣市政府勞工局也可以發給你，不是只有公司能發。",
      "③ 還是拿不到——經公立就業服務機構同意，可以用書面寫明理由代替。",
      "要在離職退保後兩年內辦；文件上要有你的姓名、公司名稱、離職原因。",
      "另外：「服務證明書」是另一張紙，只要你開口要，公司就不能拒絕。",
    ],
    statutes: ["EIA25_3", "LSA19"],
  },
  no_limitation_check: {
    id: "no_limitation_check",
    severity: "warn",
    kind: "practice",
    title: "這個工具沒有幫你算「還來不來得及」",
    body: [
      "有些權利拖久了就不能主張了，而且每一種的期限不一樣。",
      "時間拖越久對你越不利。",
      "這件事請務必另外打 1955 或問律師確認。",
    ],
    statutes: [],
  },
};

// ─────────────────────────────────────────────
// 問題
// ─────────────────────────────────────────────
export type Lane = "assisted" | "self";
export type TriageGoal = "money" | "punish" | "both" | "unsure";
export type EvidenceState = "secured" | "partial" | "none";
export type EmploymentState = "in_job" | "left" | "being_fired";

/** Q2 的複選項目——刻意用「具體物件」而非抽象的「證據是否充分」 */
export const EVIDENCE_ITEMS = [
  { value: "punch", label: "打卡紀錄、出勤表" },
  { value: "roster", label: "班表" },
  { value: "payslip", label: "薪水單、匯款紀錄" },
  { value: "chat", label: "跟主管的 LINE 對話" },
] as const;
export type EvidenceItem = (typeof EVIDENCE_ITEMS)[number]["value"];

export interface TriageAnswers {
  goal: TriageGoal;
  evidence: EvidenceState;
  employment: EmploymentState;
}

/** 由勾選數量推導。⚠️ 勾選這個動作本身就在教他該存什麼。 */
export function evidenceStateOf(picked: ReadonlySet<string>): EvidenceState {
  if (picked.size === 0) return "none";
  if (picked.size >= 3) return "secured";
  return "partial";
}

// ─────────────────────────────────────────────
// 結果
// ─────────────────────────────────────────────
export interface TriageAction {
  label: string;
  detail?: string;
  when: "before" | "now";
}

export interface TriageResult {
  answers: TriageAnswers;
  /** 一句話結論，白話動詞，不得有法律術語 */
  headline: string;
  primary: PathId[];
  alsoConsider: PathId[];
  blocked: { path: PathId; reason: string }[];
  /** 「因為你說⋯」——引用使用者自己的選擇 */
  reasons: string[];
  advisories: AdvisoryId[];
  actions: TriageAction[];
  gate?: { headline: string; body: string };
}

const GOAL_REASON: Record<TriageGoal, string> = {
  money: "因為你說你要拿回你的錢",
  punish: "因為你說你要公司被糾正",
  both: "因為你說兩個都要",
  unsure: "因為你還不確定要什麼，所以兩邊都先告訴你",
};

export function deriveTriage(a: TriageAnswers): TriageResult {
  const reasons = [GOAL_REASON[a.goal]];
  const advisories: AdvisoryId[] = [];
  const actions: TriageAction[] = [];
  let primary: PathId[] = [];
  const alsoConsider: PathId[] = [];
  let headline = "";

  // ── 主線：目標決定走公法、私法、還是兩條 ──
  if (a.goal === "punish") {
    primary = ["agency"];
    headline = "去勞工局檢舉，請他們來查公司";
    reasons.push("罰金是繳給國庫的，不會變成你的錢");
  } else if (a.goal === "money") {
    primary = ["admin_mediation", "court_mediation"];
    headline = "去勞工局申請跟公司談，談不成再請法院談";
    reasons.push("你要的是拿回錢，這條路的終點才有強制力");
    // ★ 修正：原本選「要拿回錢」的人完全看不到公法那條線的存在，
    //   等於本頁最核心的「兩條線可以並行」對他消失了。
    alsoConsider.push("agency");
    reasons.push("你也可以同時請政府去查。那條線不會給你錢，但會留下對你有利的認定");
  } else {
    primary = ["agency", "admin_mediation"];
    headline = "兩件事分開辦，而且可以同時辦";
    reasons.push("查公司跟拿回錢是兩條不同的路，不必二選一");
  }

  // ── 訴訟永遠是被擋住的，不是平行選項 ──
  const blocked = [
    { path: "litigation" as PathId, reason: "法律規定起訴前要先經過法院的調解程序" },
  ];

  // ── 證據：不改變路線，改變「順序」 ──
  let gate: TriageResult["gate"];
  if (a.evidence !== "secured") {
    advisories.push("freeze_evidence");
    gate = {
      headline: "先等一下——先把資料存下來",
      body:
        a.evidence === "none"
          ? "你說你手邊幾乎沒有東西。送件之後公司就知道了，那時候再要就難了。"
          : "你手邊只有一部分。剩下的趁現在還拿得到，先存起來。",
    };
    actions.push({
      when: "before",
      label: "把手邊有的先拍照、截圖存起來",
      detail: "存到自己的手機或雲端，不要只留在公司的系統裡。",
    });
    actions.push({
      when: "before",
      label: "跟公司要一份你的出勤紀錄",
      detail: "這是法律規定公司不能拒絕的。用寫的（訊息或 email）留下紀錄，不要只用講的。",
    });
  }

  // ★ 方向很重要：沒有證據時，「先跟公司講」要降級而不是升級——
  //   手上什麼都沒有就先去講，是最差的一格：打草驚蛇又證明不了任何事。
  if (a.evidence === "secured" && a.employment === "in_job") {
    alsoConsider.push("internal");
    reasons.push("你資料齊、人還在職，先跟公司講會留下日期紀錄");
  }

  // ── 處境 ──
  // ★ 修正：原本只對在職／被逼退者顯示。但已離職者同樣需要——
  //   若當初的解僱本身就是報復，74 條 3 項的「無效」正是他最強的主張。
  advisories.push("retaliation_void");

  if (a.employment === "being_fired") {
    actions.push({
      when: "now",
      label: "先不要簽任何東西",
      detail: "尤其是「自願離職」「同意書」。簽了之後事實會被改寫，你的證據要繞路。",
    });
  }
  if (a.employment === "left" || a.employment === "being_fired") {
    advisories.push("separation_certificate");
  }

  advisories.push("anonymity_limits");
  const goesToAgency = primary.includes("agency") || alsoConsider.includes("agency");
  if (goesToAgency) advisories.push("sixty_day_notice");
  if (primary.includes("admin_mediation")) advisories.push("mediation_shield");
  // ⛔ 只有法院勞動調解有「不異議即成立」的機制，行政調解沒有
  if (primary.includes("court_mediation") || alsoConsider.includes("court_mediation")) {
    advisories.push("ten_day_trap");
  }
  advisories.push("no_limitation_check");

  // ── 每條路線的第一步 ──
  for (const id of primary) {
    const p = PATHS[id];
    actions.push({
      when: "now",
      label: `${p.plainName}：${p.where}`,
      detail: p.effect,
    });
  }
  // ★ alsoConsider 原本算出來卻從來沒被顯示過（等於白算）。一併列出，標明是可選的。
  for (const id of alsoConsider) {
    const p = PATHS[id];
    actions.push({
      when: "now",
      label: `（可同時做）${p.plainName}：${p.where}`,
      detail: p.effect,
    });
  }
  actions.push({
    when: "now",
    label: "不確定的話，先打 1955 問",
    detail: "免費、24 小時、有印尼／越南／泰國／菲律賓語通譯。",
  });

  // 嚴重的排前面——⛔ 十日陷阱這種東西不能被排到最後才看到
  const RANK = { stop: 0, warn: 1, info: 2 } as const;
  advisories.sort((x, y) => RANK[ADVISORIES[x].severity] - RANK[ADVISORIES[y].severity]);

  return { answers: a, headline, primary, alsoConsider, blocked, reasons, advisories, actions, gate };
}

// ─────────────────────────────────────────────
// 「你可以這樣說」——本頁最重要的東西
// ⚠️ 空格一律用底線，不要填示範文字（避免使用者照著唸出示範內容）
// ─────────────────────────────────────────────
export const SCRIPT_1955 =
  "你好，我要問勞資爭議的問題。\n" +
  "我姓＿＿，在＿＿＿＿＿上班，做到＿年＿月。\n" +
  "我遇到的問題是＿＿＿＿＿＿＿＿。\n" +
  "我想知道我可以怎麼辦。";

/** 要「拿回錢」時用：申請調解 */
export const SCRIPT_MEDIATION =
  "你好，我要申請勞資爭議調解。\n" +
  "我姓＿＿，公司名稱是＿＿＿＿＿，公司地址在＿＿＿＿＿。\n" +
  "我要爭取的是＿＿＿＿＿＿＿＿。\n" +
  "請問我要準備什麼、怎麼送件？";

/** 要「公司被查」時用：申訴／檢舉 */
export const SCRIPT_COMPLAINT =
  "你好，我要申訴我的公司違反勞基法。\n" +
  "我姓＿＿，公司名稱是＿＿＿＿＿，公司地址在＿＿＿＿＿。\n" +
  "公司的問題是＿＿＿＿＿＿＿＿。\n" +
  "請問我要準備什麼？處理結果會怎麼通知我？";

/**
 * ⛔ 腳本必須跟走的路線一致——拿著「我要申請調解」去檢舉窗口，
 *    對一個本來就緊張的人是額外的挫折。
 */
export function scriptFor(goal: TriageGoal): { script: string; title: string } {
  if (goal === "punish") {
    return { script: SCRIPT_COMPLAINT, title: "到了現場，你可以這樣說" };
  }
  return { script: SCRIPT_MEDIATION, title: "到了現場，你可以這樣說" };
}

/** 他們可能會反問你的事 */
export const THEY_WILL_ASK = [
  "公司的全名跟地址",
  "你什麼時候到職、什麼時候離職（或還在職）",
  "這件事什麼時候開始的",
  "你手上有什麼資料",
];
