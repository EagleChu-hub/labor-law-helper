"use client";

import { useState } from "react";
import { Copy, Check, MessageSquareQuote } from "lucide-react";

/**
 * 「你可以這樣說」——本頁最重要的東西。
 *
 * ★ 為什麼這比法條重要：很多人卡住的不是「該打給誰」，而是「我不知道怎麼開口」。
 *   給一段可以照唸的話，比給五條路線的比較表更能讓人真的動起來。
 *
 * ⚠️ 空格一律用底線，不要填示範文字——否則會有人照著把示範內容唸出去。
 */
export function ScriptCard({ script, title = "你可以這樣說" }: { script: string; title?: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(script).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  return (
    <div className="rounded-2xl border border-gold-border bg-gold-soft p-5 space-y-3">
      <h3 className="flex items-center gap-2 text-[16px] font-black text-gold-deep">
        <MessageSquareQuote size={19} strokeWidth={1.9} />
        {title}
      </h3>

      <p className="text-[17px] leading-[1.9] text-ink whitespace-pre-line font-medium">
        {script}
      </p>

      <p className="text-[13px] text-muted">底線的地方換成你自己的狀況就好。</p>

      <button
        type="button"
        onClick={copy}
        className="w-full flex items-center justify-center gap-2 border border-gold-border bg-card rounded-xl py-3 text-[15px] font-bold text-gold-deep hover:brightness-105 transition"
      >
        {copied ? <Check size={18} strokeWidth={2.2} /> : <Copy size={18} strokeWidth={1.9} />}
        {copied ? "已複製" : "複製這段話"}
      </button>
    </div>
  );
}
