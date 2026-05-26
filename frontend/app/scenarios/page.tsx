import Link from "next/link";

const scenarios = [
  {
    category: "工時問題",
    items: [
      { title: "連續工作超過 6 天", desc: "老闆要求連上 7 天班，有違法嗎？", href: "/ask?q=連續工作超過6天是否違法" },
      { title: "每天工作超過 10 小時", desc: "長時間工作，加班費怎麼算？", href: "/ask?q=每天工作超過10小時加班費計算" },
    ],
  },
  {
    category: "假日出勤",
    items: [
      { title: "假日被要求上班", desc: "休息日或例假日出勤，應得到什麼補償？", href: "/ask?q=假日出勤補償規定" },
      { title: "國定假日上班", desc: "勞動節、春節等國定假日出勤怎麼算？", href: "/ask?q=國定假日出勤計算" },
    ],
  },
  {
    category: "薪資問題",
    items: [
      { title: "加班費未依法給付", desc: "老闆說加班只算補休，可以嗎？", href: "/ask?q=加班費用補休代替是否合法" },
      { title: "低於基本工資", desc: "懷疑薪資低於法定基本工資", href: "/ask?q=基本工資規定" },
    ],
  },
  {
    category: "休假制度",
    items: [
      { title: "年假被拒", desc: "申請特別休假被老闆拒絕怎麼辦？", href: "/ask?q=特別休假被拒絕怎麼辦" },
      { title: "年假天數不對", desc: "不清楚自己應有幾天年假", href: "/ask?q=特別休假天數計算方式" },
    ],
  },
  {
    category: "資遣與離職",
    items: [
      { title: "被資遣的權益", desc: "被資遣時應拿到哪些補償？", href: "/ask?q=被資遣可以拿到什麼補償" },
      { title: "離職預告期", desc: "想離職需要提前多久通知？", href: "/ask?q=離職預告期規定" },
    ],
  },
];

export default function ScenariosPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-800">常見情境</h1>
        <p className="text-sm text-gray-500 mt-1">選擇符合你的情況，直接進入詢問</p>
      </div>

      {scenarios.map((cat) => (
        <section key={cat.category} className="space-y-2">
          <h2 className="font-semibold text-gray-600 text-sm">{cat.category}</h2>
          <div className="grid gap-2">
            {cat.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="bg-white border border-gray-200 rounded-xl p-4 hover:border-teal-400 transition-colors flex items-start justify-between gap-3"
              >
                <div>
                  <div className="font-medium text-gray-800 text-sm">{item.title}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{item.desc}</div>
                </div>
                <span className="text-gray-400 flex-shrink-0 mt-0.5">→</span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
