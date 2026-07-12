import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { RiskLevel } from "@/types";

interface Props {
  level: RiskLevel;
  size?: "sm" | "md";
}

const config: Record<RiskLevel, { label: string; className: string; Icon: typeof AlertTriangle }> = {
  low: { label: "低風險", className: "bg-ok-soft text-ok border-ok-border", Icon: CheckCircle2 },
  medium: { label: "中風險", className: "bg-warn-soft text-warn border-warn-border", Icon: AlertTriangle },
  high: { label: "高風險", className: "bg-danger-soft text-danger-deep border-danger-border", Icon: AlertTriangle },
};

export function RiskBadge({ level, size = "md" }: Props) {
  const { label, className, Icon } = config[level];
  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded-full font-bold ${className} ${
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1"
      }`}
    >
      <Icon size={size === "sm" ? 12 : 14} strokeWidth={2.1} />
      {label}
    </span>
  );
}
