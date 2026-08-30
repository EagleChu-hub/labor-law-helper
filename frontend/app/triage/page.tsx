"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  HandHeart, Compass, Coins, ShieldCheck, Scale, HelpCircle,
  Briefcase, LogOut, AlertTriangle, Phone, ArrowLeft,
  ClipboardCheck, MessageCircleQuestion,
} from "lucide-react";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { OptionCard } from "@/components/triage/OptionCard";
import { ScriptCard } from "@/components/triage/ScriptCard";
import {
  EVIDENCE_ITEMS, SCRIPT_1955, THEY_WILL_ASK, evidenceStateOf,
  type Lane, type TriageGoal, type EmploymentState,
} from "@/lib/triageTree";

/**
 * 分流導引。⛔ 可讀性硬規則（見 lib/triageTree.ts 檔頭）：
 * 表層文字不得出現「申訴／檢舉／調解／聲請／執行名義」等法律術語，
 * 一句話 ≤ 25 字，一題一屏。
 */
export default function TriagePage() {
  const router = useRouter();
  const [lane, setLane] = useState<Lane | null>(null);
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<TriageGoal | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [noneChecked, setNoneChecked] = useState(false);
  const [employment, setEmployment] = useState<EmploymentState | null>(null);

  function toggle(v: string) {
    setNoneChecked(false);
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(v)) next.delete(v);
      else next.add(v);
      return next;
    });
  }

  function submit() {
    if (!goal || !employment) return;
    const evidence = noneChecked ? "none" : evidenceStateOf(picked);
    router.push(`/triage/result?g=${goal}&e=${evidence}&s=${employment}`);
  }

  const Header = (
    <div>
      <h1 className="text-[26px] font-black text-ink leading-tight">我該怎麼辦？</h1>
      <p className="text-[16px] text-muted mt-1.5">回答幾個問題，告訴你明天可以做什麼</p>
    </div>
  );

  // ── Q0：分岔 ──────────────────────────────
  if (lane === null) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        {Header}
        <div className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-5">
          <h2 className="text-[20px] font-black text-ink">你想怎麼處理？</h2>
          <div className="grid gap-3">
            <OptionCard
              label="我想有人幫我"
              desc="有免費專線，24 小時都有人接，也有通譯"
              Icon={HandHeart}
              tone="gold"
              selected={false}
              onSelect={() => setLane("assisted")}
            />
            <OptionCard
              label="我想自己處理"
              desc="回答 3 個問題，告訴你該去哪裡、帶什麼"
              Icon={Compass}
              selected={false}
              onSelect={() => setLane("self")}
            />
          </div>
        </div>

        {/* ⛔ 這個工具本身不判斷違不違法，本頁的兩題都預設你已經覺得有問題。
            還不確定的人要先導去真的會判斷的兩個功能，不能讓他們硬答下去。 */}
        <div className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-4">
          <h2 className="text-[17px] font-black text-ink">還不確定老闆有沒有違法？</h2>
          <p className="text-[14.5px] text-muted -mt-2">這兩個工具會先幫你確認，這裡不會。</p>
          <div className="grid gap-3">
            <Link
              href="/check"
              className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-line bg-canvas hover:border-navy-600 transition"
            >
              <span className="w-11 h-11 rounded-xl bg-navy-50 flex items-center justify-center text-navy shrink-0">
                <ClipboardCheck size={22} strokeWidth={1.75} />
              </span>
              <span className="flex-1">
                <span className="block text-[15.5px] font-extrabold text-ink">先算算我的班表對不對</span>
                <span className="block text-[13.5px] text-muted mt-0.5">工時、加班費、排休——填一週紀錄自動檢查</span>
              </span>
            </Link>
            <Link
              href="/ask"
              className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-line bg-canvas hover:border-gold transition"
            >
              <span className="w-11 h-11 rounded-xl bg-gold-soft flex items-center justify-center text-gold-deep shrink-0">
                <MessageCircleQuestion size={22} strokeWidth={1.75} />
              </span>
              <span className="flex-1">
                <span className="block text-[15.5px] font-extrabold text-ink">用自己的話問問看</span>
                <span className="block text-[13.5px] text-muted mt-0.5">調職、被刁難、其他狀況——描述情況就好</span>
              </span>
            </Link>
          </div>
        </div>

        <DisclaimerBanner />
      </div>
    );
  }

  // ── 有人幫我：一屏給完 ─────────────────────
  if (lane === "assisted") {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        {Header}

        <div className="rounded-[20px] border-2 border-navy bg-navy-50 p-6 space-y-4 text-center">
          <p className="text-[16px] font-bold text-navy-700">打這支電話就對了</p>
          <a
            href="tel:1955"
            className="flex items-center justify-center gap-3 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-2xl py-5 text-[30px] font-black tracking-wider hover:brightness-110 transition"
          >
            <Phone size={28} strokeWidth={2.2} />
            1955
          </a>
          <p className="text-[15px] text-navy-700 leading-relaxed">
            免費 · 24 小時 · 假日也有人接
            <br />
            有印尼、越南、泰國、菲律賓語通譯
          </p>
        </div>

        <ScriptCard script={SCRIPT_1955} />

        <div className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-3">
          <h3 className="text-[17px] font-black text-ink">打之前，先把這些拍起來</h3>
          <ul className="space-y-2.5">
            {EVIDENCE_ITEMS.map((it) => (
              <li key={it.value} className="flex items-start gap-2.5 text-[16px] text-ink">
                <span className="text-navy font-black shrink-0">·</span>
                {it.label}
              </li>
            ))}
          </ul>
          <p className="text-[14px] text-muted pt-1">拍照或截圖，存到自己的手機就好。</p>
        </div>

        <div className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-3">
          <h3 className="text-[17px] font-black text-ink">他們可能會問你</h3>
          <ul className="space-y-2.5">
            {THEY_WILL_ASK.map((q) => (
              <li key={q} className="flex items-start gap-2.5 text-[16px] text-ink">
                <span className="text-navy font-black shrink-0">·</span>
                {q}
              </li>
            ))}
          </ul>
        </div>

        <button
          type="button"
          onClick={() => setLane("self")}
          className="w-full border border-line rounded-xl py-4 text-[15px] font-bold text-muted hover:bg-canvas transition"
        >
          想自己處理看看 →
        </button>

        <DisclaimerBanner />
      </div>
    );
  }

  // ── 自己處理：3 題 ────────────────────────
  const canNext = step === 0 ? !!goal : step === 1 ? picked.size > 0 || noneChecked : !!employment;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {Header}

      {/* 進度：三個點，不寫字（字多了反而看不懂） */}
      <div className="flex items-center gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={`h-2 flex-1 rounded-full ${i <= step ? "bg-navy" : "bg-line"}`}
          />
        ))}
      </div>

      <div className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-5">
        {step === 0 && (
          <>
            <h2 className="text-[20px] font-black text-ink">你最想要的是什麼？</h2>
            <div className="grid gap-3">
              <OptionCard label="我要拿回我的錢" desc="加班費、資遣費、被扣掉的薪水"
                Icon={Coins} selected={goal === "money"} onSelect={() => setGoal("money")} />
              <OptionCard label="我要公司被糾正" desc="讓公司以後不敢再這樣對人"
                Icon={ShieldCheck} selected={goal === "punish"} onSelect={() => setGoal("punish")} />
              <OptionCard label="兩個都要" desc="這兩件事要分開辦，但可以同時辦"
                Icon={Scale} selected={goal === "both"} onSelect={() => setGoal("both")} />
              <OptionCard label="我還不確定" desc="兩邊都先告訴你"
                Icon={HelpCircle} selected={goal === "unsure"} onSelect={() => setGoal("unsure")} />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h2 className="text-[20px] font-black text-ink">這些東西你手邊有嗎？</h2>
            <p className="text-[15px] text-muted -mt-2">有幾個就選幾個，可以複選</p>
            <div className="grid gap-3">
              {EVIDENCE_ITEMS.map((it) => (
                <OptionCard key={it.value} label={it.label} type="checkbox"
                  selected={picked.has(it.value)} onSelect={() => toggle(it.value)} />
              ))}
              <OptionCard label="都沒有" type="checkbox" selected={noneChecked}
                onSelect={() => { setNoneChecked(true); setPicked(new Set()); }} />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="text-[20px] font-black text-ink">你現在還在這家公司嗎？</h2>
            <div className="grid gap-3">
              <OptionCard label="還在上班" Icon={Briefcase}
                selected={employment === "in_job"} onSelect={() => setEmployment("in_job")} />
              <OptionCard label="已經離開了" Icon={LogOut}
                selected={employment === "left"} onSelect={() => setEmployment("left")} />
              <OptionCard label="快被趕走了" desc="公司在逼我走，或已經說要資遣我"
                Icon={AlertTriangle} selected={employment === "being_fired"}
                onSelect={() => setEmployment("being_fired")} />
            </div>
          </>
        )}
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => (step === 0 ? setLane(null) : setStep(step - 1))}
          className="flex items-center justify-center gap-1.5 border border-line rounded-xl px-5 py-4 text-[15px] font-bold text-muted hover:bg-canvas transition"
        >
          <ArrowLeft size={17} strokeWidth={2} />
          上一步
        </button>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => (step === 2 ? submit() : setStep(step + 1))}
          className="flex-1 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-xl py-4 text-[17px] font-black hover:brightness-110 disabled:opacity-40 transition"
        >
          {step === 2 ? "看我該怎麼做" : "下一步"}
        </button>
      </div>

      <p className="text-center">
        <button
          type="button"
          onClick={() => setLane("assisted")}
          className="text-[15px] text-muted underline"
        >
          太複雜了？直接打 1955 問
        </button>
      </p>

      <DisclaimerBanner />
    </div>
  );
}
