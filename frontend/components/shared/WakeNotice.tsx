"use client";

import { useEffect, useState } from "react";

/**
 * 等待超過 delayMs 才出現的說明。
 *
 * ⛔ 2026-11 實測：第一次送出要等 20～30 秒（Render 免費方案休眠後要重新開機），
 *    畫面只有灰色方塊；原本的提示要到 65 秒逾時後才出現，而且寫的是「Render 冷啟動」。
 *    一般人等 10 秒沒反應就會以為壞了、關掉。
 */
export function WakeNotice({ delayMs = 3000, what = "計算" }: { delayMs?: number; what?: string }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setShow(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);
  if (!show) return null;
  return (
    <div role="status" className="bg-warn-soft border border-warn-border rounded-lg p-4 text-sm text-amber-800 flex items-start gap-3">
      <span className="text-xl leading-none">⏳</span>
      <div>
        <p className="font-semibold">還在{what}，請不要關掉這一頁</p>
        <p className="text-xs mt-1 text-amber-700">
          這個網站用的是免費主機，一段時間沒人用就會休息。第一次使用要等它醒來，最久大約 30 秒，之後就會很快。
        </p>
      </div>
    </div>
  );
}
