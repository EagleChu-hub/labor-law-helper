"use client";

import type { LucideIcon } from "lucide-react";

/**
 * 分流導引的選項卡。抽自 app/check/page.tsx 內聯三次的 radio-card，
 * 但**刻意放大**：本頁使用者多半是單手滑手機、很累、可能有老花。
 * ⛔ 最小高度 ≥ 56px（實際約 72px），字級比 /check 大一級。
 *
 * ⛔ Tailwind 坑：class 名稱**必須是完整字面字串**。
 *    寫成 `border-${accent}` 會在 build 時被 purge 掉（掃描器看不到組出來的字串）。
 *    所以底下用 Record 存整段 class，比照 components/results/ViolationCard.tsx 的做法。
 */
type Tone = "navy" | "gold";

const TONE: Record<Tone, { box: string; mark: string; markText: string; icon: string; iconOn: string }> = {
  navy: {
    box: "border-2 border-navy bg-navy-50",
    mark: "border-navy",
    markText: "text-navy",
    icon: "bg-navy-50 text-navy",
    iconOn: "bg-white border border-navy-100 text-navy",
  },
  gold: {
    box: "border-2 border-gold bg-gold-soft",
    mark: "border-gold-deep",
    markText: "text-gold-deep",
    icon: "bg-gold-soft text-gold-deep",
    iconOn: "bg-white border border-gold-border text-gold-deep",
  },
};

export function OptionCard({
  label,
  desc,
  Icon,
  selected,
  onSelect,
  type = "radio",
  tone = "navy",
}: {
  label: string;
  desc?: string;
  Icon?: LucideIcon;
  selected: boolean;
  onSelect: () => void;
  type?: "radio" | "checkbox";
  tone?: Tone;
}) {
  const t = TONE[tone];
  return (
    <label
      className={`flex items-center gap-4 px-5 py-5 min-h-[72px] rounded-2xl cursor-pointer transition-colors ${
        selected ? t.box : "border-[1.5px] border-line bg-card hover:border-navy-100"
      }`}
    >
      <span
        className={`w-6 h-6 border-2 flex items-center justify-center shrink-0 ${
          type === "checkbox" ? "rounded-md" : "rounded-full"
        } ${selected ? t.mark : "border-line"}`}
      >
        {selected &&
          (type === "checkbox" ? (
            <span className={`${t.markText} text-sm font-black leading-none`}>✓</span>
          ) : (
            <span className={`w-3 h-3 rounded-full ${tone === "gold" ? "bg-gold-deep" : "bg-navy"}`} />
          ))}
      </span>

      {Icon && (
        <span
          className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
            selected ? t.iconOn : t.icon
          }`}
        >
          <Icon size={24} strokeWidth={1.75} />
        </span>
      )}

      <input type={type} checked={selected} onChange={onSelect} className="sr-only" />

      <span className="flex-1">
        <span className="block text-[17px] font-extrabold text-ink leading-snug">{label}</span>
        {desc && <span className="block text-[14px] text-muted mt-1 leading-relaxed">{desc}</span>}
      </span>
    </label>
  );
}
