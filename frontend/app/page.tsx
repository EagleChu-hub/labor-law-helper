import Link from "next/link";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";

const scenarios = [
  { q: "老闆叫我連上 7 天班，合法嗎？", href: "/ask?q=連上7天班合法嗎" },
  { q: "加班費怎麼計算？", href: "/ask?q=加班費計算方式" },
  { q: "年假有幾天？什麼時候可以請？", href: "/ask?q=年假天數與規定" },
  { q: "被要求假日出勤，有加班費嗎？", href: "/ask?q=假日出勤加班費" },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="bg-gradient-to-br from-teal-700 to-teal-900 text-white rounded-2xl px-6 py-10 text-center space-y-4">
        <h1 className="text-2xl md:text-3xl font-bold leading-snug">
          老闆有沒有少給你錢或假？
          <br />
          <span className="text-teal-200">填出勤、算金額、3 秒見真章</span>
        </h1>
        <p className="text-teal-100 text-sm md:text-base max-w-md mx-auto">
          台灣勞工免費權益試算工具。填一週出勤 + 時薪，立刻算出你可能少領多少加班費／假日工資。
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center mt-2">
          <Link
            href="/check"
            className="bg-white text-teal-800 font-semibold rounded-xl px-6 py-3 hover:bg-teal-50 transition-colors"
          >
            💰 算算我少拿多少
          </Link>
          <Link
            href="/ask"
            className="bg-teal-600 border border-teal-400 text-white font-semibold rounded-xl px-6 py-3 hover:bg-teal-500 transition-colors"
          >
            💬 問 AI 律師
          </Link>
        </div>
      </section>

      {/* Two entry method cards */}
      <section className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <div className="text-3xl">✅</div>
          <h2 className="font-bold text-gray-800">快速出勤判斷</h2>
          <p className="text-sm text-gray-600">
            輸入工作時間、加班紀錄、假日出勤等資料，系統自動比對勞基法規定，列出可能的違規項目。
          </p>
          <Link href="/check" className="inline-block text-sm text-teal-700 font-semibold hover:underline">
            開始判斷 →
          </Link>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <div className="text-3xl">💬</div>
          <h2 className="font-bold text-gray-800">情境式詢問</h2>
          <p className="text-sm text-gray-600">
            用自然語言描述你的工作情況或問題，AI 會根據勞基法條文給你具體的分析與建議。
          </p>
          <Link href="/ask" className="inline-block text-sm text-teal-700 font-semibold hover:underline">
            開始詢問 →
          </Link>
        </div>
      </section>

      {/* Common scenarios */}
      <section className="space-y-3">
        <h2 className="font-semibold text-gray-700">常見問題</h2>
        <div className="grid gap-2">
          {scenarios.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-700 hover:border-teal-400 hover:text-teal-700 transition-colors flex items-center justify-between"
            >
              {s.q}
              <span className="text-gray-400 ml-2">→</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Service guarantees */}
      <section className="grid grid-cols-3 gap-3 text-center text-xs text-gray-500">
        <div className="bg-white rounded-lg border p-3 space-y-1">
          <div className="text-xl">🔒</div>
          <div>不儲存個人資料</div>
        </div>
        <div className="bg-white rounded-lg border p-3 space-y-1">
          <div className="text-xl">⚡</div>
          <div>即時分析結果</div>
        </div>
        <div className="bg-white rounded-lg border p-3 space-y-1">
          <div className="text-xl">📚</div>
          <div>依據現行法條</div>
        </div>
      </section>

      <DisclaimerBanner />
    </div>
  );
}
