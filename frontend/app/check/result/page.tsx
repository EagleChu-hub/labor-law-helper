"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { ViolationCard } from "@/components/results/ViolationCard";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { checkAnalyze } from "@/lib/api";
import { IS_OPENSOURCE } from "@/lib/mode";
import { buildResultPrompt } from "@/lib/promptTemplate";
import { OpenSourceAiButtons } from "@/components/shared/OpenSourceAiButtons";
import type { CheckResult, CheckRequest } from "@/types";

function minutesToHours(min: number) {
  return (min / 60).toFixed(1);
}

function buildAskUrl(result: CheckResult): string {
  const issues = result.violations
    .filter((v) => v.status !== "compliant")
    .map((v) => v.title);

  if (issues.length === 0) {
    return "/ask?q=" + encodeURIComponent("我的出勤快速判斷結果良好，請問有哪些勞基法權益我應該平時注意？");
  }

  const issueList = issues.map((t) => `「${t}」`).join("、");
  const moneyLine = (result.total_shortfall_ntd ?? 0) > 0
    ? `系統估算我可能少領 NT$ ${result.total_shortfall_ntd?.toLocaleString()} 元。`
    : "";
  const msg = `我剛做了出勤快速判斷，系統發現以下疑似問題：${issueList}。${moneyLine}請根據勞基法幫我詳細分析這些情況，並告訴我應該如何主張自己的權益？`;
  return "/ask?q=" + encodeURIComponent(msg);
}

function formatNtd(n: number): string {
  return `NT$ ${Math.round(n).toLocaleString()}`;
}

/** 加班費即時試算機（純前端） */
function OvertimeCalculator() {
  const [open, setOpen] = useState(false);
  const [hourly, setHourly] = useState<string>("200");
  const [mode, setMode] = useState<"weekday_ot" | "rest_day" | "mandatory_rest" | "national_holiday">("weekday_ot");
  const [hours, setHours] = useState<string>("4");

  const calc = (): { total: number; breakdown: string } => {
    const h = Number(hourly) || 0;
    const hr = Number(hours) || 0;
    if (h <= 0 || hr <= 0) return { total: 0, breakdown: "（請輸入時薪與時數）" };

    if (mode === "weekday_ot") {
      const first2 = Math.min(hr, 2) * h * 1.34;
      const after = Math.max(hr - 2, 0) * h * 1.67;
      return {
        total: first2 + after,
        breakdown: `前 2h × ${h} × 1.34 = ${formatNtd(first2)}；其後 × 1.67 = ${formatNtd(after)}`,
      };
    }
    if (mode === "rest_day") {
      const first2 = Math.min(hr, 2) * h * 1.34;
      const next6 = Math.min(Math.max(hr - 2, 0), 6) * h * 1.67;
      const after8 = Math.max(hr - 8, 0) * h * 2.67;
      return {
        total: first2 + next6 + after8,
        breakdown: `前 2h × 1.34 + 2-8h × 1.67 + >8h × 2.67`,
      };
    }
    if (mode === "mandatory_rest") {
      const daily = 8 * h;
      const first2 = Math.min(hr, 2) * h * 1.34;
      const after = Math.max(hr - 2, 0) * h * 1.67;
      return {
        total: daily + first2 + after,
        breakdown: `加發 1 日 (${formatNtd(daily)}) + 工時加成 (前 2h ×1.34、其後 ×1.67)`,
      };
    }
    // national_holiday
    const daily = 8 * h;
    const work = hr * h;
    return {
      total: daily + work,
      breakdown: `原工資 ${formatNtd(work)} + 加發 1 日工資 ${formatNtd(daily)}（雙倍工資）`,
    };
  };

  const { total, breakdown } = calc();

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="bg-white border rounded-xl p-4"
    >
      <summary className="cursor-pointer font-semibold text-gray-700 select-none">
        🧮 加班費試算機（即時調整、不送出）
      </summary>
      <div className="mt-3 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500">平日時薪 NT$</label>
            <input
              type="number" min={0} value={hourly}
              onChange={(e) => setHourly(e.target.value)}
              className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">該班工時（小時）</label>
            <input
              type="number" min={0} step={0.5} value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500">情境</label>
          <div className="grid grid-cols-2 gap-2 mt-1">
            {([
              { v: "weekday_ot", label: "平日加班（8h 後）" },
              { v: "rest_day", label: "休息日出勤" },
              { v: "mandatory_rest", label: "例假日出勤" },
              { v: "national_holiday", label: "國定假日出勤" },
            ] as const).map(({ v, label }) => (
              <button
                key={v}
                type="button"
                onClick={() => setMode(v)}
                className={`text-xs py-2 px-2 rounded-lg border ${mode === v ? "bg-teal-700 text-white border-teal-700" : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="bg-gradient-to-br from-teal-50 to-teal-100 rounded-lg p-4">
          <p className="text-xs text-teal-700">應給金額</p>
          <p className="text-2xl font-bold text-teal-800">{formatNtd(total)}</p>
          <p className="text-xs text-teal-700 mt-1">{breakdown}</p>
        </div>
        <p className="text-xs text-gray-400">
          試算為參考數值，實際金額以勞動契約與雇主計算為準。若雇主已給付部分加班費，請以本金額扣除。
        </p>
      </div>
    </details>
  );
}

export default function CheckResultPage() {
  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // C-3：Render 冷啟動提示 + 自動重試（最多 2 次，每次間隔 6 秒）
  const [retryCount, setRetryCount] = useState(0);
  const [coldStartMsg, setColdStartMsg] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("checkRequest");
    if (!raw) {
      setError("找不到出勤資料，請重新填寫。");
      return;
    }
    const request: CheckRequest = JSON.parse(raw);
    checkAnalyze(request)
      .then(setResult)
      .catch((e: Error) => {
        if (e.message === "COLD_START_TIMEOUT" && retryCount < 2) {
          setColdStartMsg(true);
          setTimeout(() => {
            setColdStartMsg(false);
            setRetryCount((n) => n + 1); // 觸發 useEffect 重新執行
          }, 6000);
        } else {
          setError(e.message);
        }
      });
  }, [retryCount]); // retryCount 改變時重新呼叫 API

  if (error) return <ErrorState message={error} />;
  if (!result) return (
    <div className="py-12 space-y-4">
      {coldStartMsg && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 flex items-start gap-3">
          <span className="text-xl leading-none">⏳</span>
          <div>
            <p className="font-semibold">後端正在喚醒中</p>
            <p className="text-xs mt-1 text-amber-700">
              Render 免費方案冷啟動需約 30 秒。正在自動重試（第 {retryCount + 1} 次 / 最多 3 次）...
            </p>
          </div>
        </div>
      )}
      <LoadingSkeleton lines={6} />
    </div>
  );

  const violationCount = result.violations.filter((v) => v.status !== "compliant").length;
  const totalShortfall = result.total_shortfall_ntd ?? 0;
  const hasWage = !!result.has_wage_input;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* ⭐ 最顯眼：少領金額紅卡 */}
      {violationCount > 0 && (
        hasWage && totalShortfall > 0 ? (
          <div className="bg-gradient-to-br from-red-500 to-red-600 text-white rounded-2xl shadow-lg p-6 space-y-2">
            <p className="text-sm font-medium text-red-100">你這段期間可能少領</p>
            <p className="text-4xl sm:text-5xl font-bold tracking-tight">{formatNtd(totalShortfall)}</p>
            <p className="text-xs text-red-100">
              依勞基法第 24、39 條倍率試算。點下方違規卡片看每項明細，或捲到最底用試算機自己調參數重算。
            </p>
          </div>
        ) : (
          <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-5 space-y-2">
            <p className="text-sm font-bold text-amber-900">
              ⚠️ 這段期間有 {violationCount} 個班可能涉及加班費或假日工資未付足
            </p>
            <p className="text-xs text-amber-800">
              想看具體金額？回上一步在「💰 時薪資訊」填入平日時薪，系統會幫你算出可能短少多少 NT$。
            </p>
            <Link href="/check" className="inline-block mt-1 text-xs text-amber-900 underline font-medium">
              ← 回上一步補時薪
            </Link>
          </div>
        )
      )}

      {/* Summary */}
      <div className="bg-white rounded-xl border shadow-sm p-6 space-y-3">
        <div className="flex items-center gap-3">
          <RiskBadge level={result.risk_level} />
          {violationCount > 0 && (
            <span className="text-sm text-gray-500">發現 {violationCount} 項疑似問題</span>
          )}
        </div>
        <h1 className="text-lg font-bold text-gray-800">{result.headline}</h1>
        <p className="text-xs text-gray-500">{result.disclaimer}</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "總工時", value: `${minutesToHours(result.metrics.total_work_minutes)} 小時` },
          { label: "加班時數", value: `${minutesToHours(result.metrics.total_overtime_minutes)} 小時` },
          { label: "最長連班", value: `${result.metrics.max_consecutive_days} 天` },
          { label: "日均工時", value: `${minutesToHours(result.metrics.avg_daily_minutes)} 小時` },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-lg border p-3 text-center">
            <div className="text-lg font-bold text-teal-700">{m.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Violations */}
      {result.violations.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-semibold text-gray-700">詳細分析</h2>
          {result.violations.map((v) => (
            <ViolationCard key={v.rule_id} violation={v} />
          ))}
        </section>
      )}

      {/* Next actions */}
      {result.next_actions.length > 0 && (
        <section className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-2">
          <h2 className="font-semibold text-blue-800">建議下一步</h2>
          <ul className="space-y-1">
            {result.next_actions.map((action, i) => (
              <li key={i} className="text-sm text-blue-700 flex items-start gap-2">
                <span className="mt-0.5">•</span>
                {action}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Complaint links — shown only when violations exist */}
      {violationCount > 0 && (
        <section className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-3">
          <h2 className="font-semibold text-red-800">向主管機關申訴</h2>
          <p className="text-sm text-red-700">若您確認雇主違法，可透過以下管道正式申訴：</p>
          <div className="flex flex-col sm:flex-row gap-2">
            <a
              href="https://ap.bola.gov.taipei/LZ.aspx"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 py-2.5 px-4 bg-red-600 text-white rounded-lg text-sm font-medium text-center hover:bg-red-700"
            >
              台北市政府勞動局申訴
            </a>
            <a
              href="https://romeodex.osha.gov.tw/PO/WriteMail"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 py-2.5 px-4 border border-red-600 text-red-700 rounded-lg text-sm font-medium text-center hover:bg-red-50"
            >
              勞動部申訴信箱
            </a>
          </div>
          <p className="text-xs text-gray-500">或撥打勞工諮詢專線：<strong>1955</strong></p>
        </section>
      )}

      {/* 加班費試算機（純前端） */}
      <OvertimeCalculator />

      <DisclaimerBanner />

      {/* AI 進一步詢問：依模式切換 */}
      {IS_OPENSOURCE ? (
        <OpenSourceAiButtons
          prompt={buildResultPrompt(result)}
          title="🤖 用 AI 律師詳細分析這份結果"
        />
      ) : null}

      <div className="flex gap-3">
        <Link
          href="/check"
          className="flex-1 py-3 text-center border border-gray-300 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50"
        >
          重新輸入
        </Link>
        {!IS_OPENSOURCE && (
          <Link
            href={buildAskUrl(result)}
            className="flex-1 py-3 text-center bg-teal-700 text-white rounded-xl font-semibold hover:bg-teal-800"
          >
            進一步詢問 AI
          </Link>
        )}
      </div>
    </div>
  );
}
