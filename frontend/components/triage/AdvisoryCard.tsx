import { ADVISORIES, type AdvisoryId } from "@/lib/triageTree";

/**
 * 提醒卡。自 app/triage/result/page.tsx 抽出，讓 /check/result 也能複用。
 *
 * ⛔ 抽出的理由不是為了少寫幾行：這些文案是逐字對過法條的，
 *    重寫一份就會有兩份會各自漂移的版本（本專案已經在「只抄一半」上栽過兩次）。
 *
 * ★ kind === "practice" 會自動標示「這是經驗提醒，不是法律規定」，
 *   讀者永遠分得出哪一句有法條撐、哪一句沒有。
 */
const TONE = {
  stop: "border-danger-border bg-danger-soft",
  warn: "border-warn-border bg-warn-soft",
  info: "border-line bg-card",
} as const;

export function AdvisoryCard({ id }: { id: AdvisoryId }) {
  const ad = ADVISORIES[id];
  return (
    <div className={`rounded-2xl border p-5 space-y-2 ${TONE[ad.severity]}`}>
      <h3 className="text-[16.5px] font-black text-ink leading-snug">{ad.title}</h3>
      {ad.body.map((b) => (
        <p key={b} className="text-[15.5px] text-ink leading-relaxed">
          {b}
        </p>
      ))}
      {ad.kind === "practice" && (
        <p className="text-[13px] text-muted pt-0.5">※ 這是經驗提醒，不是法律規定。</p>
      )}
    </div>
  );
}
