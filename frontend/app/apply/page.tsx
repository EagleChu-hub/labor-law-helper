"use client";

import { useState } from "react";
import Link from "next/link";
import { MapPin, ExternalLink, AlertTriangle, Phone, ArrowLeft } from "lucide-react";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { OptionCard } from "@/components/triage/OptionCard";
import { ScriptCard } from "@/components/triage/ScriptCard";
import {
  DIRECTORY_URL, LABOR_BUREAUS, buildMediationDraft,
  type LaborBureau, type MediationMethod,
} from "@/lib/laborBureaus";
import { STATUTES } from "@/lib/triageTree";

export default function ApplyPage() {
  const [city, setCity] = useState<string>("");
  const [method, setMethod] = useState<MediationMethod>("mediator");

  const bureau: LaborBureau | null =
    LABOR_BUREAUS.find((b) => b.city === city) ?? null;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-[26px] font-black text-ink leading-tight">要去哪裡申請？</h1>
        <p className="text-[16px] text-muted mt-1.5">選你上班的縣市，幫你把申請書草稿寫好</p>
      </div>

      {/* ⛔ 最容易錯的一格，放最前面 */}
      <div className="rounded-[20px] border-2 border-danger-border bg-danger-soft p-6 space-y-2.5">
        <h2 className="flex items-center gap-2 text-[18px] font-black text-danger-deep">
          <AlertTriangle size={21} strokeWidth={2.1} />
          是你「上班」的縣市，不是你住的縣市
        </h2>
        <p className="text-[16px] text-ink leading-relaxed">
          很多人跑錯地方。法律規定要向你<strong>提供勞務所在地</strong>的政府申請。
        </p>
        <p className="text-[15px] text-muted leading-relaxed">
          住新北、在台北上班 → 去<strong className="text-ink">臺北市</strong>。
        </p>
      </div>

      {/* 縣市選單 */}
      <section className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-4">
        <h2 className="flex items-center gap-2 text-[18px] font-black text-ink">
          <MapPin size={20} strokeWidth={1.9} />
          你在哪個縣市上班？
        </h2>
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="w-full border-[1.5px] border-line rounded-xl px-4 py-4 text-[17px] font-bold text-ink bg-card"
        >
          <option value="">請選擇⋯</option>
          {LABOR_BUREAUS.map((b) => (
            <option key={b.city} value={b.city}>
              {b.city}
            </option>
          ))}
        </select>

        {bureau && (
          <div className="rounded-2xl border-2 border-navy bg-navy-50 p-5 space-y-3">
            <p className="text-[13px] font-bold text-navy-700">你要找的是</p>
            <p className="text-[19px] font-black text-ink leading-snug">{bureau.name}</p>
            <a
              href={bureau.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-xl px-5 py-3.5 text-[15.5px] font-bold hover:brightness-110 transition"
            >
              打開官網
              <ExternalLink size={17} strokeWidth={2} />
            </a>
            <p className="text-[13.5px] text-muted">
              正式的申請表格請在這個網站上找「勞資爭議調解」。
            </p>
          </div>
        )}

        <p className="text-[13.5px] text-muted">
          連結失效了？到{" "}
          <a href={DIRECTORY_URL} target="_blank" rel="noopener noreferrer" className="underline text-navy-700">
            勞保局的官方名冊
          </a>{" "}
          查最新的。
        </p>
      </section>

      {/* 調解方式：申請書上必填、但幾乎沒人知道差別的一格 */}
      <section className="bg-card rounded-[20px] border border-line shadow-sm p-6 space-y-4">
        <h2 className="text-[18px] font-black text-ink">申請書上要你選一種，差別在這裡</h2>
        <div className="grid gap-3">
          <OptionCard
            label="指派調解人"
            desc="一個人來協調，通常比較快。多數案件走這個。"
            selected={method === "mediator"}
            onSelect={() => setMethod("mediator")}
          />
          <OptionCard
            label="組成調解委員會"
            desc="由多人組成，程序較完整，通常花比較久。"
            selected={method === "committee"}
            onSelect={() => setMethod("committee")}
          />
        </div>
        <p className="text-[13.5px] text-muted">
          不確定就選第一個，這是最常見的選擇。
        </p>
      </section>

      {/* 草稿 */}
      <ScriptCard script={buildMediationDraft(bureau, method)} title="申請書草稿（可複製）" />
      <p className="text-[13.5px] text-muted -mt-3">
        ⚠️ 這是<strong className="text-ink">草稿</strong>，方便你先想好要寫什麼。
        正式送件請用該機關網站上的表格。
      </p>

      <a
        href="tel:1955"
        className="flex items-center justify-center gap-2.5 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-2xl py-4 text-[19px] font-black hover:brightness-110 transition"
      >
        <Phone size={22} strokeWidth={2.2} />
        不確定就打 1955
      </a>

      {/* 法律依據收在展開層 */}
      <details className="bg-card rounded-[20px] border border-line shadow-sm">
        <summary className="cursor-pointer px-6 py-5 text-[17px] font-black text-ink select-none">
          想知道為什麼？（法律依據）
        </summary>
        <div className="px-6 pb-6 space-y-4 border-t border-line pt-5">
          <p className="text-[13.5px] text-muted">以下為逐字引用，未改寫。</p>
          {["SDA9", "SDA10", "SDA11"].map((k) => {
            const st = STATUTES[k];
            return (
              <div key={k} className="rounded-xl border border-line p-4 space-y-1.5">
                <a
                  href={st.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[14.5px] font-extrabold text-navy-700 underline"
                >
                  {st.article_no}
                </a>
                <p className="text-[14.5px] text-ink leading-relaxed">{st.quote}</p>
              </div>
            );
          })}
        </div>
      </details>

      <DisclaimerBanner />

      <Link
        href="/triage"
        className="flex items-center justify-center gap-2 text-[15px] text-muted underline"
      >
        <ArrowLeft size={16} strokeWidth={2} />
        回去看我該走哪條路
      </Link>
    </div>
  );
}
