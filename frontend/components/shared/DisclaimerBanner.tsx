export function DisclaimerBanner() {
  return (
    <div className="flex gap-2.5 items-start bg-warn-soft border border-warn-border rounded-xl px-4 py-3">
      <span className="text-base leading-relaxed">⚠️</span>
      <p className="m-0 text-[13px] leading-relaxed text-amber-900">
        <span className="font-semibold">注意：</span>
        本系統提供參考資訊，不構成法律意見。如有勞資爭議，建議洽詢專業律師或撥打
        <strong> 1955 勞工諮詢專線</strong>。
      </p>
    </div>
  );
}
