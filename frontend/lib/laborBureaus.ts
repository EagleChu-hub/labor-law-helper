/**
 * 各縣市勞工行政主管機關。
 *
 * 資料來源：勞動部勞工保險局「各縣市勞工行政主管機關」
 *   https://www.bli.gov.tw/0103340.html （2026-08-30 擷取）
 *
 * ⛔ 只放「機關名稱」與「官網」。電話僅查到四個機關，
 *    依本專案「只抄一半比完全沒寫危險」的紀律，**寧可全部不放**。
 *    需要電話請打 1955，或點該機關官網。
 *
 * ⚠️ 政府網址會改版失效。畫面上務必同時提供 DIRECTORY_URL 當退路，
 *    不要讓使用者在連結失效時無路可走。
 */
export const DIRECTORY_URL = "https://www.bli.gov.tw/0103340.html";

export interface LaborBureau {
  /** 縣市名（選單顯示用） */
  city: string;
  /** 機關全名 */
  name: string;
  url: string;
}

/** ⚠️ 部分縣市之勞工業務併於社會處，機關名稱不一定含「勞工局」——照官方名稱寫。 */
export const LABOR_BUREAUS: LaborBureau[] = [
  { city: "臺北市", name: "臺北市政府勞動局", url: "https://bola.gov.taipei/" },
  { city: "新北市", name: "新北市政府勞工局", url: "https://ilabor.ntpc.gov.tw/" },
  { city: "基隆市", name: "基隆市政府法制及勞動處", url: "https://www.klcg.gov.tw/tw/legallabor" },
  { city: "桃園市", name: "桃園市政府勞動局", url: "https://lhrb.tycg.gov.tw/" },
  { city: "新竹市", name: "新竹市政府勞工及青年處", url: "https://dep-labor.hccg.gov.tw/ch/index.jsp" },
  { city: "新竹縣", name: "新竹縣政府勞工處", url: "https://labor.hsinchu.gov.tw/" },
  { city: "苗栗縣", name: "苗栗縣政府勞工及青年發展處", url: "https://www.miaoli.gov.tw/labor_youth/Default.aspx" },
  { city: "臺中市", name: "臺中市政府勞工局", url: "https://www.labor.taichung.gov.tw/" },
  { city: "南投縣", name: "南投縣政府社會及勞動局", url: "https://welfare.nantou.gov.tw/" },
  { city: "彰化縣", name: "彰化縣政府勞工處", url: "https://labor.chcg.gov.tw/00home/index1.asp" },
  { city: "雲林縣", name: "雲林縣政府勞動暨青年事務發展處", url: "https://labor.yunlin.gov.tw/" },
  { city: "嘉義市", name: "嘉義市政府社會處", url: "https://social.chiayi.gov.tw/" },
  { city: "嘉義縣", name: "嘉義縣政府勞工暨青年發展處", url: "https://ly.cyhg.gov.tw/" },
  { city: "臺南市", name: "臺南市政府勞工局", url: "https://web.tainan.gov.tw/labor/" },
  { city: "高雄市", name: "高雄市政府勞工局", url: "https://labor.kcg.gov.tw/" },
  { city: "屏東縣", name: "屏東縣政府勞動暨青年發展處", url: "https://www.pthg.gov.tw/planlab/Default.aspx" },
  { city: "宜蘭縣", name: "宜蘭縣政府勞工處", url: "https://labor.e-land.gov.tw/Default.aspx" },
  { city: "花蓮縣", name: "花蓮縣政府社會處", url: "https://sa.hl.gov.tw/" },
  { city: "臺東縣", name: "臺東縣政府社會處", url: "https://taisoc.taitung.gov.tw/WebSite/Page/index.aspx" },
  { city: "澎湖縣", name: "澎湖縣政府社會處", url: "https://www.penghu.gov.tw/society/" },
  { city: "金門縣", name: "金門縣政府社會處", url: "https://social.kinmen.gov.tw/Default.aspx" },
  { city: "連江縣", name: "連江縣政府民政社會處", url: "https://www.matsu.gov.tw/Chhtml/Index/371030000A0001" },
];

/**
 * 調解申請書草稿。
 *
 * ⛔ 依勞資爭議處理法 10 條的三款應載明事項組出，**空格一律用底線**
 *    （與 ScriptCard 同一慣例：填示範文字會有人照抄）。
 * ⚠️ 這是**草稿**，不是正式表格——正式表格要從該縣市機關網站下載。
 */
export function buildMediationDraft(bureau: LaborBureau | null, method: MediationMethod): string {
  const to = bureau ? bureau.name : "＿＿＿＿＿政府勞工局";
  return [
    `受文機關：${to}`,
    "",
    "一、申請人（勞方）",
    "　　姓名：＿＿＿＿＿　　　性別：＿＿　　年齡：＿＿",
    "　　職業：＿＿＿＿＿",
    "　　住居所：＿＿＿＿＿＿＿＿＿＿",
    "　　電話：＿＿＿＿＿＿＿＿",
    "",
    "二、相對人（資方）",
    "　　公司名稱：＿＿＿＿＿＿＿＿",
    "　　代表人：＿＿＿＿＿",
    "　　營業所地址：＿＿＿＿＿＿＿＿＿＿",
    "",
    "三、請求調解事項",
    "　　（一）＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿",
    "　　（二）＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿",
    "　　　　※ 寫清楚你要什麼、大概多少錢。不確定金額可以寫「依法計算之金額」。",
    "",
    "四、調解方式",
    `　　${method === "mediator" ? "■ 指派調解人　　□ 組成勞資爭議調解委員會" : "□ 指派調解人　　■ 組成勞資爭議調解委員會"}`,
    "",
    "五、事實經過",
    "　　＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿",
    "　　＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿",
    "",
    "此　致",
    to,
    "",
    "申請人：＿＿＿＿＿（簽名或蓋章）",
    "中華民國　＿＿＿　年　＿＿　月　＿＿　日",
  ].join("\n");
}

export type MediationMethod = "mediator" | "committee";
