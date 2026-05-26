import type { ViolationItem } from "@/types";

interface Props {
  violation: ViolationItem;
}

const statusConfig = {
  suspected_violation: { label: "疑似違規", color: "border-l-red-500 bg-red-50" },
  warning: { label: "需注意", color: "border-l-amber-500 bg-amber-50" },
  compliant: { label: "合規", color: "border-l-green-500 bg-green-50" },
};

const confidenceLabel = { high: "高", medium: "中", low: "低" };

export function ViolationCard({ violation }: Props) {
  const { label, color } = statusConfig[violation.status];
  return (
    <div className={`border-l-4 rounded-r-lg p-4 space-y-3 ${color}`}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-semibold text-gray-800">{violation.title}</h3>
        <div className="flex gap-2">
          <span className="text-xs px-2 py-0.5 bg-white border rounded-full text-gray-600">
            {label}
          </span>
          <span className="text-xs px-2 py-0.5 bg-white border rounded-full text-gray-500">
            可信度：{confidenceLabel[violation.confidence]}
          </span>
        </div>
      </div>

      <p className="text-sm text-gray-700">{violation.explanation}</p>

      {(violation.estimated_shortfall_ntd ?? 0) > 0 && (
        <div className="bg-white border border-red-200 rounded-lg p-3 space-y-1">
          <p className="text-sm font-semibold text-red-700">
            💰 試算可能短少：NT$ {violation.estimated_shortfall_ntd!.toLocaleString()}
          </p>
          {violation.shortfall_formula && (
            <p className="text-xs text-gray-500">公式：{violation.shortfall_formula}</p>
          )}
        </div>
      )}

      {violation.law_references.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500">相關法條</p>
          {violation.law_references.map((ref) => (
            <a
              key={ref.article_no}
              href={ref.source_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs text-teal-700 hover:underline"
            >
              勞基法 {ref.article_no}：{ref.title}
            </a>
          ))}
        </div>
      )}

      {violation.missing_facts.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500">尚需確認</p>
          <ul className="list-disc list-inside text-xs text-gray-600 space-y-0.5">
            {violation.missing_facts.map((fact, i) => (
              <li key={i}>{fact}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
