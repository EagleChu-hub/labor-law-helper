import type { RiskLevel } from "@/types";

interface Props {
  level: RiskLevel;
  size?: "sm" | "md";
}

const config: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "低風險", className: "bg-green-100 text-green-700 border-green-300" },
  medium: { label: "中風險", className: "bg-amber-100 text-amber-700 border-amber-300" },
  high: { label: "高風險", className: "bg-red-100 text-red-700 border-red-300" },
};

export function RiskBadge({ level, size = "md" }: Props) {
  const { label, className } = config[level];
  return (
    <span
      className={`inline-flex items-center border rounded-full font-semibold ${className} ${
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1"
      }`}
    >
      {label}
    </span>
  );
}
