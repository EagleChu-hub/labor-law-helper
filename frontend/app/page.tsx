import Link from "next/link";
import { MessageCircle, ShieldCheck, Zap, BookOpen, ClipboardCheck, Compass } from "lucide-react";
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
      <section className="relative overflow-hidden rounded-3xl bg-[radial-gradient(120%_130%_at_15%_0%,var(--navy-800),var(--navy-900)_62%)] text-white px-7 py-11 md:px-11 md:py-14">
        <div className="pointer-events-none absolute -right-16 -top-10 w-72 h-72 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--gold),transparent_78%),transparent_70%)]" />
        <div className="relative max-w-xl space-y-5">
          <span className="inline-flex items-center gap-1.5 text-xs font-bold bg-white/10 border border-white/15 px-3.5 py-1.5 rounded-full">
            ⚖️ 為委屈的你，站在你這邊
          </span>
          <h1 className="text-3xl md:text-[38px] font-black leading-[1.18] tracking-tight">
            老闆有沒有
            <br />
            少給你錢或假？
          </h1>
          <p className="text-[17px] leading-relaxed text-white/80 max-w-md">
            填一週出勤，3 秒幫你算可能短少的薪水與假日。白話說明、不留個資，像律師朋友一樣陪你確認。
          </p>
          <div className="flex flex-col sm:flex-row gap-3 pt-1">
            <Link
              href="/check"
              className="inline-flex items-center justify-center gap-2 bg-gradient-to-b from-gold to-gold-deep text-white font-bold text-[15px] rounded-[13px] px-6 py-3.5 shadow-[0_12px_26px_-12px_rgba(0,0,0,.35)] hover:brightness-110 transition"
            >
              <ClipboardCheck size={19} strokeWidth={1.9} />
              算算我少拿多少
            </Link>
            <Link
              href="/ask"
              className="inline-flex items-center justify-center gap-2 bg-white/10 border border-white/25 text-white font-bold text-[15px] rounded-[13px] px-6 py-3.5 hover:bg-white/15 transition"
            >
              問 AI 律師 💬
            </Link>
          </div>
          <div className="flex items-center gap-2 text-[13px] text-white/60 pt-1">
            <ShieldCheck size={15} strokeWidth={1.9} />
            不儲存個人資料 · 即時分析 · 依據現行勞基法
          </div>
        </div>
      </section>

      {/* 分流導引：擺在最前面，因為最多人卡在「我不知道該幹嘛」 */}
      <section>
        <Link
          href="/triage"
          className="group flex items-center gap-4 bg-card rounded-2xl border-2 border-navy-600 p-6 shadow-sm hover:shadow-[0_16px_34px_-22px_rgba(20,25,45,.4)] transition"
        >
          <span className="w-14 h-14 rounded-2xl bg-navy-50 flex items-center justify-center text-navy shrink-0">
            <Compass size={28} strokeWidth={1.75} />
          </span>
          <span className="flex-1">
            <h2 className="font-black text-xl text-ink">我該怎麼辦？</h2>
            <p className="text-[15px] text-muted leading-relaxed mt-1">
              不知道從哪裡開始？回答幾個問題，告訴你明天可以做什麼。
            </p>
          </span>
          <span className="text-navy-600 font-bold text-lg shrink-0">→</span>
        </Link>
      </section>

      {/* Two entry method cards */}
      <section className="grid md:grid-cols-2 gap-[18px]">
        <Link
          href="/check"
          className="group bg-card rounded-2xl border border-line p-6 space-y-3 shadow-sm hover:border-navy-600 hover:shadow-[0_16px_34px_-22px_rgba(20,25,45,.4)] transition"
        >
          <span className="w-11 h-11 rounded-[13px] bg-navy-50 flex items-center justify-center text-navy">
            <ClipboardCheck size={22} strokeWidth={1.75} />
          </span>
          <h2 className="font-black text-lg text-ink">快速出勤判斷</h2>
          <p className="text-sm text-muted leading-relaxed">
            填一週的上下班時間，系統依勞基法逐條檢查，並試算可能短少的加班費與假日工資。
          </p>
          <span className="inline-flex items-center gap-1.5 text-sm font-bold text-navy-600">開始判斷 →</span>
        </Link>
        <Link
          href="/ask"
          className="group bg-card rounded-2xl border border-line p-6 space-y-3 shadow-sm hover:border-gold hover:shadow-[0_16px_34px_-22px_rgba(20,25,45,.4)] transition"
        >
          <span className="w-11 h-11 rounded-[13px] bg-gold-soft flex items-center justify-center text-gold-deep">
            <MessageCircle size={22} strokeWidth={1.75} />
          </span>
          <h2 className="font-black text-lg text-ink">情境式詢問</h2>
          <p className="text-sm text-muted leading-relaxed">
            用你自己的話描述職場狀況，AI 律師以白話文回覆你可以主張什麼、對應哪一條法規。
          </p>
          <span className="inline-flex items-center gap-1.5 text-sm font-bold text-gold-deep">開始詢問 →</span>
        </Link>
      </section>

      {/* Common scenarios */}
      <section className="space-y-3">
        <h2 className="font-bold text-ink text-sm">常見問題</h2>
        <div className="grid gap-2">
          {scenarios.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className="bg-card border border-line rounded-xl px-4 py-3 text-sm text-ink hover:border-navy-600 hover:text-navy-700 transition-colors flex items-center justify-between"
            >
              {s.q}
              <span className="text-muted ml-2">→</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Service guarantees */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="flex items-center gap-2.5 bg-card border border-line rounded-2xl px-4 py-3.5">
          <ShieldCheck size={20} strokeWidth={1.75} className="text-ok shrink-0" />
          <span className="text-[13.5px] font-bold text-ink">不儲存個人資料</span>
        </div>
        <div className="flex items-center gap-2.5 bg-card border border-line rounded-2xl px-4 py-3.5">
          <Zap size={20} strokeWidth={1.75} className="text-navy shrink-0" />
          <span className="text-[13.5px] font-bold text-ink">即時分析</span>
        </div>
        <div className="flex items-center gap-2.5 bg-card border border-line rounded-2xl px-4 py-3.5">
          <BookOpen size={20} strokeWidth={1.75} className="text-gold-deep shrink-0" />
          <span className="text-[13.5px] font-bold text-ink">依據現行法條</span>
        </div>
      </section>

      <DisclaimerBanner />

      <p className="text-center">
        <Link href="/about" className="text-[14px] text-muted underline">
          這個網站為什麼在
        </Link>
      </p>
    </div>
  );
}
