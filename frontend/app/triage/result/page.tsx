"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle, Phone, Share2, Printer, Copy, Check, ArrowLeft, Ban,
} from "lucide-react";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { OpenSourceAiButtons } from "@/components/shared/OpenSourceAiButtons";
import { ScriptCard } from "@/components/triage/ScriptCard";
import { IS_OPENSOURCE } from "@/lib/mode";
import { buildTriagePrompt } from "@/lib/promptTemplate";
import {
  ADVISORIES, PATHS, STATUTES, deriveTriage, scriptFor,
  type EmploymentState, type EvidenceState, type TriageGoal, type TriageResult,
} from "@/lib/triageTree";

const GOALS = ["money", "punish", "both", "unsure"];
const EVIDENCES = ["secured", "partial", "none"];
const EMPLOYMENTS = ["in_job", "left", "being_fired"];

/** 把結果攤成純文字，給複製／分享用 */
function toPlainText(r: TriageResult): string {
  const lines = [
    "【我該怎麼辦】",
    r.headline,
    "",
    "為什麼：",
    ...r.reasons.map((x) => `· ${x}`),
    "",
    "可以做的事：",
    ...r.actions.map((a, i) => `${i + 1}. ${a.label}${a.detail ? `\n   ${a.detail}` : ""}`),
    "",
    "要注意：",
    ...r.advisories.map((id) => `· ${ADVISORIES[id].title}`),
    "",
    "不確定就打 1955（免費、24 小時）。",
    "",
    "本資訊僅供參考，不構成法律意見。",
  ];
  return lines.join("\n");
}

function TriageResultInner() {
  const sp = useSearchParams();
  const [copied, setCopied] = useState(false);

  const g = sp.get("g");
  const e = sp.get("e");
  const s = sp.get("s");

  const valid =
    g && e && s && GOALS.includes(g) && EVIDENCES.includes(e) && EMPLOYMENTS.includes(s);

  // ⛔ CLAUDE.md ⓫：hooks 全部在前，條件式 return 放最後
  if (!valid) {
    return (
      <div className="max-w-2xl mx-auto space-y-5">
        <p className="text-[17px] text-ink">找不到你的答案，請重新回答一次。</p>
        <Link
          href="/triage"
          className="inline-flex items-center gap-2 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-xl px-6 py-3.5 font-bold"
        >
          <ArrowLeft size={18} strokeWidth={2} />
          回去重新回答
        </Link>
      </div>
    );
  }

  const result = deriveTriage({
    goal: g as TriageGoal,
    evidence: e as EvidenceState,
    employment: s as EmploymentState,
  });

  const plain = toPlainText(result);

  function copyAll() {
    navigator.clipboard.writeText(plain).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  function share() {
    const data = { title: "我該怎麼辦", text: plain, url: window.location.href };
    if (typeof navigator.share === "function") {
      navigator.share(data).catch(() => {});
    } else {
      copyAll();
    }
  }

  const before = result.actions.filter((a) => a.when === "before");
  const now = result.actions.filter((a) => a.when === "now");

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* ⛔ 證據關卡放最上面——不能只有捲動才看得到 */}
      {result.gate && (
        <div className="rounded-[20px] border-2 border-danger-border bg-danger-soft p-6 space-y-2.5 print:break-inside-avoid">
          <h2 className="flex items-center gap-2 text-[19px] font-black text-danger-deep">
            <AlertTriangle size={22} strokeWidth={2.1} />
            {result.gate.headline}
          </h2>
          <p className="text-[16px] text-ink leading-relaxed">{result.gate.body}</p>
        </div>
      )}

      {/* 一句話結論 */}
      <div className="space-y-2.5">
        <p className="text-[15px] font-bold text-muted">你可以這樣做</p>
        <h1 className="text-[27px] font-black text-ink leading-[1.35]">{result.headline}</h1>
        <ul className="space-y-1.5 pt-1">
          {result.reasons.map((r) => (
            <li key={r} className="text-[15.5px] text-muted leading-relaxed">— {r}</li>
          ))}
        </ul>
      </div>

      {/* 先做這些 */}
      {before.length > 0 && (
        <section className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-4">
          <h2 className="text-[18px] font-black text-ink">先做這些，再去送件</h2>
          <ol className="space-y-4">
            {before.map((a, i) => (
              <li key={a.label} className="flex gap-3.5">
                <span className="w-8 h-8 rounded-full bg-danger-soft text-danger-deep font-black flex items-center justify-center shrink-0 font-sora">
                  {i + 1}
                </span>
                <span>
                  <span className="block text-[17px] font-extrabold text-ink leading-snug">{a.label}</span>
                  {a.detail && <span className="block text-[15px] text-muted mt-1 leading-relaxed">{a.detail}</span>}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* 然後做這些 */}
      <section className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-4">
        <h2 className="text-[18px] font-black text-ink">
          {before.length > 0 ? "然後，做這些" : "你可以做的事"}
        </h2>
        <ol className="space-y-4">
          {now.map((a, i) => (
            <li key={a.label} className="flex gap-3.5">
              <span className="w-8 h-8 rounded-full bg-navy-50 text-navy font-black flex items-center justify-center shrink-0 font-sora">
                {i + 1}
              </span>
              <span>
                <span className="block text-[17px] font-extrabold text-ink leading-snug">{a.label}</span>
                {a.detail && <span className="block text-[15px] text-muted mt-1 leading-relaxed">{a.detail}</span>}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <ScriptCard {...scriptFor(result.answers.goal)} />

      {/* 提醒 */}
      <section className="space-y-3">
        <h2 className="text-[18px] font-black text-ink">要注意的事</h2>
        {result.advisories.map((id) => {
          const ad = ADVISORIES[id];
          const tone =
            ad.severity === "stop"
              ? "border-danger-border bg-danger-soft"
              : ad.severity === "warn"
              ? "border-warn-border bg-warn-soft"
              : "border-line bg-card";
          return (
            <div key={id} className={`rounded-2xl border p-5 space-y-2 ${tone}`}>
              <h3 className="text-[16.5px] font-black text-ink leading-snug">{ad.title}</h3>
              {ad.body.map((b) => (
                <p key={b} className="text-[15.5px] text-ink leading-relaxed">{b}</p>
              ))}
              {ad.kind === "practice" && (
                <p className="text-[13px] text-muted pt-0.5">※ 這是經驗提醒，不是法律規定。</p>
              )}
            </div>
          );
        })}
      </section>

      {/* 帶走 */}
      <div className="grid grid-cols-3 gap-2.5 print:hidden">
        <button type="button" onClick={copyAll}
          className="flex flex-col items-center gap-1.5 border border-line bg-card rounded-xl py-3.5 text-[13.5px] font-bold text-ink hover:bg-canvas transition">
          {copied ? <Check size={20} strokeWidth={2.1} /> : <Copy size={20} strokeWidth={1.9} />}
          {copied ? "已複製" : "複製"}
        </button>
        <button type="button" onClick={share}
          className="flex flex-col items-center gap-1.5 border border-line bg-card rounded-xl py-3.5 text-[13.5px] font-bold text-ink hover:bg-canvas transition">
          <Share2 size={20} strokeWidth={1.9} />
          傳給別人
        </button>
        <button type="button" onClick={() => window.print()}
          className="flex flex-col items-center gap-1.5 border border-line bg-card rounded-xl py-3.5 text-[13.5px] font-bold text-ink hover:bg-canvas transition">
          <Printer size={20} strokeWidth={1.9} />
          列印
        </button>
      </div>

      <a href="tel:1955"
        className="flex items-center justify-center gap-2.5 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-2xl py-4 text-[19px] font-black hover:brightness-110 transition print:hidden">
        <Phone size={22} strokeWidth={2.2} />
        不確定就打 1955
      </a>

      {/* 展開層：法律細節全部收在這裡 */}
      <details className="bg-card rounded-[20px] border border-line shadow-sm print:hidden">
        <summary className="cursor-pointer px-6 py-5 text-[17px] font-black text-ink select-none">
          想知道為什麼？（法律依據）
        </summary>
        <div className="px-6 pb-6 space-y-6 border-t border-line pt-5">
          <div className="space-y-2">
            <h3 className="text-[16px] font-black text-ink">兩條路，可以同時走</h3>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="rounded-xl border border-line p-4 space-y-1">
                <p className="text-[13px] font-bold text-muted">罰公司這條（公法）</p>
                <p className="text-[15px] text-ink">向勞工局申訴、申請勞動檢查</p>
              </div>
              <div className="rounded-xl border border-line p-4 space-y-1">
                <p className="text-[13px] font-bold text-muted">拿回錢這條（私法）</p>
                <p className="text-[15px] text-ink">勞資爭議調解 → 法院勞動調解 → 訴訟</p>
              </div>
            </div>
            <p className="text-[14px] text-muted">這兩條是不同的線，可以同時進行。</p>
          </div>

          <div className="space-y-3">
            <h3 className="text-[16px] font-black text-ink">五條路線</h3>
            {(Object.keys(PATHS) as (keyof typeof PATHS)[]).map((id) => {
              const p = PATHS[id];
              const isBlocked = result.blocked.some((b) => b.path === id);
              return (
                <div key={id} className={`rounded-xl border p-4 space-y-1.5 ${isBlocked ? "border-line bg-canvas opacity-70" : "border-line"}`}>
                  <p className="text-[15.5px] font-extrabold text-ink flex items-center gap-2">
                    {isBlocked && <Ban size={15} strokeWidth={2.1} className="text-muted" />}
                    {p.name}
                    <span className="text-[13px] font-medium text-muted">（{p.plainName}）</span>
                  </p>
                  <p className="text-[14px] text-muted">受理：{p.where}</p>
                  <p className="text-[14px] text-ink">效果：{p.effect}</p>
                  {p.cannotDo && <p className="text-[14px] text-danger-deep">{p.cannotDo}</p>}
                  <p className="text-[14px] text-muted">費用：{p.cost}</p>
                </div>
              );
            })}
          </div>

          <div className="space-y-3">
            <h3 className="text-[16px] font-black text-ink">法條原文</h3>
            <p className="text-[13.5px] text-muted">以下為逐字引用，未改寫。</p>
            {Array.from(
              new Set([
                ...result.primary.flatMap((id) => PATHS[id].statutes),
                ...result.advisories.flatMap((id) => ADVISORIES[id].statutes),
              ])
            ).map((k) => {
              const st = STATUTES[k];
              if (!st) return null;
              return (
                <div key={k} className="rounded-xl border border-line p-4 space-y-1.5">
                  <a href={st.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-[14.5px] font-extrabold text-navy-700 underline">
                    {st.article_no}
                    {!st.verified && <span className="text-danger-deep ml-1.5">（待查證）</span>}
                  </a>
                  <p className="text-[14.5px] text-ink leading-relaxed">{st.quote}</p>
                </div>
              );
            })}
          </div>
        </div>
      </details>

      <DisclaimerBanner />

      {IS_OPENSOURCE ? (
        <OpenSourceAiButtons prompt={buildTriagePrompt(result)} title="把這個情況拿去問 AI" />
      ) : (
        <Link
          href={`/ask?q=${encodeURIComponent(result.headline)}`}
          className="flex items-center justify-center gap-2 border border-line bg-card rounded-xl py-4 text-[16px] font-bold text-navy-700 hover:bg-canvas transition print:hidden"
        >
          再問 AI 律師 💬
        </Link>
      )}

      <Link href="/triage"
        className="flex items-center justify-center gap-2 text-[15px] text-muted underline print:hidden">
        <ArrowLeft size={16} strokeWidth={2} />
        重新回答一次
      </Link>
    </div>
  );
}

/** ⛔ useSearchParams() 沒有 Suspense 邊界，build 會出 CSR-bailout 錯誤 */
export default function TriageResultPage() {
  return (
    <Suspense fallback={<p className="text-center text-muted py-10">載入中⋯</p>}>
      <TriageResultInner />
    </Suspense>
  );
}
