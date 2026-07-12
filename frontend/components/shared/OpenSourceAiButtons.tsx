"use client";

import { useState } from "react";
import { Copy, Check, MessageSquareText, Sparkles, ChevronUp, ChevronDown } from "lucide-react";
import { AI_LINKS } from "@/lib/promptTemplate";

interface Props {
  /** 完整提示詞文字，包含 system instruction + 使用者情境 */
  prompt: string;
  /** 標題（選填） */
  title?: string;
}

/**
 * 開源版 AI 互動按鈕組：複製提示詞 + 跳轉到 ChatGPT/Gemini。
 * 不打後端 LLM API，使用者自行貼到外部 AI 服務。
 */
export function OpenSourceAiButtons({ prompt, title }: Props) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // 退路：開個 prompt 視窗讓使用者手動複製
      window.prompt("請手動複製以下提示詞：", prompt);
    }
  }

  /** 點 ChatGPT / Gemini 連結時自動複製提示詞（fire-and-forget，不擋導覽） */
  function handleAiLinkClick() {
    navigator.clipboard.writeText(prompt).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  return (
    <div className="bg-navy-50 border border-navy-100 rounded-2xl p-4 space-y-3">
      <div>
        <h3 className="font-black text-navy-900 text-sm">
          {title ?? "🤖 用 AI 律師幫你分析"}
        </h3>
        <p className="text-xs text-navy-600 mt-0.5">
          你的出勤資料只用於本網站法規判斷，<strong>不會傳送給 ChatGPT 或 Gemini</strong>。
          請：① 複製提示詞 → ② 點開任一 AI 服務 → ③ 貼上送出。
        </p>
      </div>

      <button
        onClick={copyToClipboard}
        className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-colors ${
          copied
            ? "bg-ok text-white"
            : "bg-gradient-to-b from-navy-600 to-navy-800 text-white hover:brightness-110"
        }`}
      >
        {copied ? <Check size={16} /> : <Copy size={16} />}
        {copied ? "已複製！點下方任一 AI 服務貼上即可" : "步驟 1：複製 AI 提示詞"}
      </button>

      <div className="grid grid-cols-2 gap-2">
        <a
          href={AI_LINKS.chatgpt}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleAiLinkClick}
          className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-card border border-line text-ink text-sm font-semibold hover:border-navy-600 hover:text-navy-700"
        >
          <MessageSquareText size={15} /> 步驟 2：ChatGPT
        </a>
        <a
          href={AI_LINKS.gemini}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleAiLinkClick}
          className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-card border border-line text-ink text-sm font-semibold hover:border-gold hover:text-gold-deep"
        >
          <Sparkles size={15} /> 步驟 2：Gemini
        </a>
      </div>

      <button
        onClick={() => setShowPreview((v) => !v)}
        className="flex items-center gap-1 text-xs text-navy-600 hover:underline"
      >
        {showPreview ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        {showPreview ? "收合預覽" : "預覽提示詞內容"}
      </button>
      {showPreview && (
        <pre className="text-xs text-muted bg-card border border-line rounded-lg p-3 whitespace-pre-wrap max-h-60 overflow-y-auto">
          {prompt}
        </pre>
      )}
    </div>
  );
}
