import { AlertTriangle, CheckCircle2, Coins } from "lucide-react";
import type { ViolationItem } from "@/types";

interface Props {
  violation: ViolationItem;
}

const statusConfig = {
  suspected_violation: {
    label: "疑似違規",
    bar: "bg-danger",
    bg: "bg-danger-soft",
    border: "border-danger-border",
    text: "text-danger-deep",
    Icon: AlertTriangle,
    iconColor: "text-danger",
  },
  warning: {
    label: "需注意",
    bar: "bg-warn",
    bg: "bg-warn-soft",
    border: "border-warn-border",
    text: "text-amber-700",
    Icon: AlertTriangle,
    iconColor: "text-warn",
  },
  compliant: {
    label: "合規",
    bar: "bg-ok",
    bg: "bg-ok-soft",
    border: "border-ok-border",
    text: "text-ok",
    Icon: CheckCircle2,
    iconColor: "text-ok",
  },
};

const confidenceLabel = { high: "高", medium: "中", low: "低" };

export function ViolationCard({ violation }: Props) {
  const { label, bar, bg, border, text, Icon, iconColor } = statusConfig[violation.status];
  return (
    <div className={`flex rounded-2xl overflow-hidden border ${bg} ${border}`}>
      <div className={`w-[5px] shrink-0 ${bar}`} />
      <div className="p-5 flex-1 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="flex items-center gap-2 font-black text-base text-ink">
            <Icon size={19} strokeWidth={1.9} className={iconColor} />
            {violation.title}
          </h3>
          <div className="flex gap-2">
            <span className={`text-xs font-bold px-2.5 py-0.5 bg-card border ${border} ${text} rounded-full`}>
              {label}
            </span>
            <span className="text-xs font-semibold px-2.5 py-0.5 bg-card border border-line text-muted rounded-full">
              可信度：{confidenceLabel[violation.confidence]}
            </span>
          </div>
        </div>

        <p className="text-sm text-ink leading-relaxed">{violation.explanation}</p>

        {(violation.estimated_shortfall_ntd ?? 0) > 0 && (
          <div className="bg-card border border-gold-border rounded-[13px] p-4 space-y-1.5">
            <p className="flex items-center gap-2 text-sm font-extrabold text-gold-deep">
              <Coins size={17} strokeWidth={1.9} />
              試算可能短少：
              <span className="font-sora">NT$ {violation.estimated_shortfall_ntd!.toLocaleString()}</span>
            </p>
            {violation.shortfall_formula && (
              <p className="text-xs text-muted font-sora ml-6">公式：{violation.shortfall_formula}</p>
            )}
          </div>
        )}

        {violation.law_references.length > 0 && (
          <div className={`text-xs text-muted border-t ${border} pt-3`}>
            相關法條 ·{" "}
            {violation.law_references.map((ref, i) => (
              <span key={ref.article_no}>
                {i > 0 && "、"}
                <a
                  href={ref.source_url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-navy-600 font-semibold hover:text-gold-deep"
                >
                  勞基法 {ref.article_no}：{ref.title}
                </a>
              </span>
            ))}
          </div>
        )}

        {violation.missing_facts.length > 0 && (
          <div className="text-xs text-muted space-y-1">
            {violation.missing_facts.map((fact, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <span className="text-warn font-bold shrink-0">尚需確認</span>
                <span>{fact}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
