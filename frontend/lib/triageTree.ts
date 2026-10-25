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
const CIV = "B0000001"; // 民法（請求權時效）

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
  // ★ 保密不是空話：洩漏是有後果的。只寫「不能洩漏」而不寫後果，承諾會顯得廉價
  LSA74_6: {
    key: "LSA74_6",
    article_no: "勞動基準法第 74 條第 6 項",
    quote:
      "違反前項規定者，除公務員應依法追究刑事與行政責任外，對因此受有損害之勞工，應負損害賠償責任。",
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
  // ⛔ 第二個十日陷阱，方向相反：提了異議之後**不是就沒事了**，
  //    若不再於十日內表示反對續行，案件會自動變成訴訟（且回溯到聲請調解時起訴）。
  LIA29_4: {
    key: "LIA29_4",
    article_no: "勞動事件法第 29 條第 4 項",
    quote:
      "依前項規定調解不成立者，除調解聲請人於受告知或通知後十日之不變期間內，向法院為反對續行訴訟程序之意思外，應續行訴訟程序，並視為自調解聲請時，已經起訴；其於第一項適當方案送達前起訴者，亦同。",
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
  // ⚠️ 期限與應載明事項在第 1、4 項，不在第 3 項。
  //    原本散文寫了「兩年內」「要載明姓名公司離職原因」，卻只引第 3 項
  //    ——畫面上的引文撐不住那兩句話，勞工看不到依據。
  EIA25_1: {
    key: "EIA25_1",
    article_no: "就業保險法第 25 條第 1 項",
    quote:
      "被保險人於離職退保後二年內，應檢附離職或定期契約證明文件及國民身分證或其他足資證明身分之證件，親自向公立就業服務機構辦理求職登記、申請失業認定及接受就業諮詢，並填寫失業認定、失業給付申請書及給付收據。",
    source_url: moj(EIA, "25"),
    verified: true,
  },
  EIA25_4: {
    key: "EIA25_4",
    article_no: "就業保險法第 25 條第 4 項",
    quote: "前項文件或書面，應載明申請人姓名、投保單位名稱及離職原因。",
    source_url: moj(EIA, "25"),
    verified: true,
  },
  // ⛔ 又一個不作為就失權的期限：文件沒齊，七日內沒補就當你沒申請過
  EIA25_5: {
    key: "EIA25_5",
    article_no: "就業保險法第 25 條第 5 項",
    quote: "申請人未檢齊第一項規定文件者，應於七日內補正；屆期未補正者，視為未申請。",
    source_url: moj(EIA, "25"),
    verified: true,
  },
  // ★★ 本條是「拿不到離職證明」這個死結的真正出口：
  //    因離職事由在吵架，**仍然可以先請領**失業給付。
  //    ⚠️ 但附帶一個對勞工自己的義務：爭議結果不利時，十五日內要還。
  EIA23: {
    key: "EIA23",
    article_no: "就業保險法第 23 條",
    quote:
      "申請人與原雇主間因離職事由發生勞資爭議者，仍得請領失業給付。前項爭議結果，確定申請人不符失業給付請領規定時，應於確定之日起十五日內，將已領之失業給付返還。屆期未返還者，依法移送強制執行。",
    source_url: moj(EIA, "23"),
    verified: true,
  },
  // ⛔ 這條的對象是「國家」，不是雇主——本站唯一會讓使用者惹上刑責的風險點
  EIA36: {
    key: "EIA36",
    article_no: "就業保險法第 36 條",
    quote:
      "以詐欺或其他不正當行為領取保險給付或為虛偽之證明、報告、陳述者，除按其領取之保險給付處以二倍罰鍰外，並應依民法請求損害賠償；其涉及刑責者，移送司法機關辦理。",
    source_url: moj(EIA, "36"),
    verified: true,
  },
  LSA19: {
    key: "LSA19",
    article_no: "勞動基準法第 19 條",
    quote: "勞動契約終止時，勞工如請求發給服務證明書，雇主或其代理人不得拒絕。",
    source_url: moj(LSA, "19"),
    verified: true,
  },
  // ── 請求權時效（PR21）──────────────────────────────────
  // ⚠️ PR16 起連續掛了五個 PR 的待辦。先前整段只寫「本工具沒有幫你算，去打 1955」
  //    ——那正是全域指引說的「籠統的建議諮詢專業人士是雜訊」。
  // ★ 分界要講清楚：**期間長度**是法條明文（他自己查得到），
  //   **某筆錢屬於哪一種請求權**才是真的需要專業判斷的地方。
  CIV125: {
    key: "CIV125",
    article_no: "民法第 125 條",
    quote: "請求權，因十五年間不行使而消滅。但法律所定期間較短者，依其規定。",
    source_url: moj(CIV, "125"),
    verified: true,
  },
  // ★ 工資／加班費按月給付，屬「一年或不及一年之定期給付債權」→ 五年
  CIV126: {
    key: "CIV126",
    article_no: "民法第 126 條",
    quote:
      "利息、紅利、租金、贍養費、退職金及其他一年或不及一年之定期給付債權，其各期給付請求權，因五年間不行使而消滅。",
    source_url: moj(CIV, "126"),
    verified: true,
  },
  CIV128: {
    key: "CIV128",
    article_no: "民法第 128 條",
    quote: "消滅時效，自請求權可行使時起算。",
    source_url: moj(CIV, "128"),
    verified: true,
  },
  // ★★ 這一條是整段最有用的：聲請調解「與起訴有同一效力」→ 會中斷時效。
  //    而本站主推的就是申請調解——等於把「我來不來得及」變成「現在就去做這件事」。
  CIV129: {
    key: "CIV129",
    article_no: "民法第 129 條",
    quote:
      "消滅時效，因左列事由而中斷：一、請求。二、承認。三、起訴。左列事項，與起訴有同一效力：一、依督促程序，聲請發支付命令。二、聲請調解或提付仲裁。三、申報和解債權或破產債權。四、告知訴訟。五、開始執行行為或聲請強制執行。",
    source_url: moj(CIV, "129"),
    verified: true,
  },
  // ⛔ 陷阱：只寄存證信函（「請求」）只買到六個月，六個月內沒起訴就當作沒中斷過
  CIV130: {
    key: "CIV130",
    article_no: "民法第 130 條",
    quote: "時效因請求而中斷者，若於請求後六個月內不起訴，視為不中斷。",
    source_url: moj(CIV, "130"),
    verified: true,
  },
  // ★ 時效完成 ≠ 權利消失，是對方「得拒絕給付」。所以超過了也不是完全不能談
  CIV144: {
    key: "CIV144",
    article_no: "民法第 144 條",
    quote: "時效完成後，債務人得拒絕給付。",
    source_url: moj(CIV, "144"),
    verified: true,
  },
  LSA58: {
    key: "LSA58",
    article_no: "勞動基準法第 58 條第 1 項",
    quote: "勞工請領退休金之權利，自退休之次月起，因五年間不行使而消滅。",
    source_url: moj(LSA, "58"),
    verified: true,
  },
  LSA61: {
    key: "LSA61",
    article_no: "勞動基準法第 61 條第 1 項",
    quote: "第五十九條之受領補償權，自得受領之日起，因二年間不行使而消滅。",
    source_url: moj(LSA, "61"),
    verified: true,
  },
  EIA24: {
    key: "EIA24",
    article_no: "就業保險法第 24 條",
    quote: "領取保險給付之請求權，自得請領之日起，因二年間不行使而消滅。",
    source_url: moj(EIA, "24"),
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
    // ⛔ PR22 修正：原本只寫「幾乎沒有強制力」，等於告訴勞工這步沒用。
    //    但勞基法第 74 條第 2、3 項的報復保護，正是「為前項申訴」才啟動的
    //    ——向雇主申訴就是第 1 項的申訴之一。這步拿不到錢，卻會打開你最硬的那面盾。
    effect: "留下日期紀錄，證明你有先講過；而且申訴本身就會啟動法律保護——之後公司若因此解僱、降調、減薪或其他不利處分，那個處分無效",
    cannotDo: "公司可以不理你，這一步本身要不到錢。但別跳過：要主張「處分無效」，你得先有申訴這個動作。",
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
    // ⛔ PR22：SDA61 原本掛著卻沒講，SDA8 只講了管公司那一半（漏掉也管勞方）
    cannotDo: "談不成就結束，不會有人幫你判誰對誰錯。⚠️ 就算談成了，若法院後來裁定駁回強制執行的聲請，這個調解會被視為不成立。⚠️ 調解期間勞方也不得因為這個爭議而罷工或為其他爭議行為。",
    cost: "多數縣市不收費，實際請洽當地勞工局",
    statutes: ["SDA23", "SDA59", "SDA61", "SDA8"],
  },
  court_mediation: {
    id: "court_mediation",
    track: "private",
    name: "法院勞動調解",
    plainName: "請法院找雙方坐下來談",
    where: "地方法院勞動法庭",
    // ⛔ PR22：LIA38 原本掛著卻沒講——出勤紀錄的推定效力是選這條路的實質理由之一
    effect: "★ 談成了跟法院判決一樣有力，對方不付錢可以直接請法院扣他的錢。而且走法院程序時，出勤紀錄裡記載的時間會被推定為「經雇主同意而執行職務」，舉證壓力轉到公司那邊",
    cannotDo: "要跑法院一趟，流程比在勞工局談正式一些。⛔ 收到法院提出的方案後有十天的不變期間要表示意見，不動作就視為成立（見下方提醒）。",
    cost: "聲請費用依標的金額而定，以法院公告為準",
    // ⚠️ cannotDo 提到十日不變期間，就得把 LIA29 一起宣告
    //    （PR22 漏了，被 check_frontend_statutes 的「引用不足」檢查抓出來）
    statutes: ["LIA26", "LIA38", "LIA29"],
  },
  litigation: {
    id: "litigation",
    track: "private",
    name: "訴訟",
    plainName: "打官司",
    where: "地方法院勞動法庭",
    effect: "法官判決",
    // ⛔ PR22 修正：原本寫「不能直接打」，但勞動事件法第 16 條第 2 項明定
    //    「前項事件當事人逕向法院起訴者，**視為調解之聲請**」——不是不受理，
    //    是自動轉成調解。寫成「不能」會讓勞工以為送件會被退，是過度絕對的敘述。
    cannotDo: "起訴前原則上要先經過法院的勞動調解程序（少數例外除外）。就算你直接遞起訴狀，法院也會把它視為聲請調解——不是退件，而是先走調解。",
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
      "法律規定承辦人員應對你的身分資料嚴守秘密，不得洩漏足以識別你身分的資訊。",
      "萬一真的洩漏，公務員要被追究刑事與行政責任，而且對因此受損害的勞工應負損害賠償責任。",
      "但如果全公司只有你被那樣排班，公司還是猜得到。",
      "所以重點不是能不能匿名，是被知道之後你站不站得住。",
    ],
    statutes: ["LSA74_5", "LSA74_6"],
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
      // ⛔ 同一條也課勞方義務。只講雇主那一半，等於讓勞工自己踩進去。
      "⚠️ 同一條也管你這邊：調解期間，勞方不得因為這個爭議而罷工或為其他爭議行為。",
      "意思是這段期間你照常上班、照常留證據就好，不要自己先做出可以被反過來指責的事。",
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
      "你收到之後有十天可以說「我不同意」（法律上叫「提出異議」）。",
      "十天內沒有動作，法律上就當作你已經依照那個方案成立調解了，效力跟確定判決一樣。",
      "這十天是「不變期間」，不能延長。收到任何法院文件，先看日期。",
      // ⛔ 第二個十日，方向相反——PR19 查 29 條 4 項時才發現，原本完全沒寫
      // ⚠️ body 的每個元素各自渲染成一個 <p>，而且是純文字（不吃 markdown）。
      //    一句話不要拆成兩個元素，也不要寫 **粗體**——會原樣顯示（CLAUDE.md ⓭ 已記過一次）。
      "⛔ 而且提了異議不等於就沒事了：調解視為不成立之後，除非你再於收到通知後十天內向法院表明「反對續行訴訟程序」，案件就會自動進入訴訟，而且回溯當作你在聲請調解時就已經起訴。",
      "所以這裡其實有兩個十天：第一個決定你要不要接受方案，第二個決定你要不要打官司。",
    ],
    statutes: ["LIA29", "LIA26", "LIA29_4"],
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
      // ★★ PR19 新增：這條把「拿不到證明」從死路變成活路，原本完全沒寫
      "④ 最重要的一點：如果你跟公司正在吵「到底為什麼離職」，法律明文規定你仍然可以先請領失業給付，不必等吵完。",
      "⚠️ 但這一條也有對你自己的要求：如果爭議結果確定你不符請領規定，要在確定之日起十五日內把領到的錢還回去，逾期會被移送強制執行。",
      "期限：要在離職退保後二年內，親自向公立就業服務機構辦理求職登記、申請失業認定。",
      "文件上要載明你的姓名、投保單位名稱及離職原因。",
      "⚠️ 文件沒帶齊也別乾等：應於七日內補正，屆期沒補就「視為未申請」，要重跑一次。",
      "另外：「服務證明書」是另一張紙，只要你開口要，公司就不能拒絕。",
      "⛔ 但如果你已經找到新工作，就不能拿這張紙去領失業給付。",
      "失業給付的前提是你還在找工作。已經就業還去領，會被追回兩倍罰鍰，嚴重的還會移送。",
      "這張紙在那種情況下的用途，是把「非自願離職」這件事確定下來，不是拿去請領。",
    ],
    statutes: ["EIA25_3", "EIA25_1", "EIA25_4", "EIA25_5", "EIA23", "LSA19", "EIA36"],
  },
  // ⛔ PR21 改寫。原本整段只有「本工具沒有幫你算，去打 1955」——
  //    那是雜訊：期限長度是法條明文，勞工自己查得到，沒理由不告訴他。
  //    ★ 要分清楚哪一部分他查得到、哪一部分才真的需要專業意見。
  no_limitation_check: {
    id: "no_limitation_check",
    severity: "warn",
    kind: "legal",
    title: "「還來不來得及」——先看這幾個數字，再決定要不要急",
    body: [
      "本工具沒有幫你算你自己的期限（要算得準，得知道每一筆錢是哪一天可以請求的）。",
      "但期限有多長是法律寫死的，你自己看得懂：",
      "・工資、加班費：按月給付，屬於民法第 126 條的「一年或不及一年之定期給付債權」，各期請求權五年。",
      "・退休金：自退休之次月起算五年（勞基法第 58 條第 1 項）。",
      "・職業災害補償：自得受領之日起算二年（勞基法第 61 條第 1 項）。",
      "・失業給付等保險給付：自得請領之日起算二年（就業保險法第 24 條）。",
      "・沒有特別規定的，回到民法第 125 條的十五年。",
      "期限從哪天開始算？民法第 128 條：自請求權可行使時起算（也就是那筆錢本來該給你的那天）。",
      "⛔ 真正需要問專業的不是「幾年」，而是「我這筆錢算哪一種」——例如資遣費、特休未休工資怎麼歸類會影響年限。拿不準就打 1955 或問律師，問的時候直接說「我想確認這筆是不是適用民法第 126 條的五年」。",
      "★ 但先別急著算。更有用的是：時效是可以「中斷」的，中斷之後重新起算。",
      "民法第 129 條規定，請求、承認、起訴都會中斷時效；而且「聲請調解或提付仲裁」與起訴有同一效力。",
      "也就是說——你去申請勞資爭議調解，這個動作本身就會讓時效重新開始算。這是你現在就能做的事。",
      "⚠️ 但只寄存證信函（法律上叫「請求」）不夠：民法第 130 條規定，請求後六個月內沒有起訴，就視為沒有中斷過。寄信只買到六個月。",
      "⚠️ 最後一點，不要因為「好像超過了」就放棄：民法第 144 條說時效完成後是「債務人得拒絕給付」——是對方可以拒絕，不是你的權利自動消失。對方沒拒絕、或願意談，照樣可以拿回來。",
    ],
    statutes: [
      "CIV126", "LSA58", "LSA61", "EIA24", "CIV125",
      "CIV128", "CIV129", "CIV130", "CIV144",
    ],
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
