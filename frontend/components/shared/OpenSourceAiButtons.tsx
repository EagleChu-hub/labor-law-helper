"use client";

import { useState } from "react";
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
    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl p-4 space-y-3">
      <div>
        <h3 className="font-semibold text-indigo-900 text-sm">
          {title ?? "🤖 用 AI 律師幫你分析"}
        </h3>
        <p className="text-xs text-indigo-700/80 mt-0.5">
          你的出勤資料只用於本網站法規判斷，<strong>不會傳送給 ChatGPT 或 Gemini</strong>。
          請：① 複製提示詞 → ② 點開任一 AI 服務 → ③ 貼上送出。
        </p>
      </div>

      <button
        onClick={copyToClipboard}
        className={`w-full py-3 rounded-lg font-semibold text-sm transition-colors ${
          copied
            ? "bg-green-600 text-white"
            : "bg-indigo-700 text-white hover:bg-indigo-800"
        }`}
      >
        {copied ? "✓ 已複製！點下方任一 AI 服務貼上即可" : "📋 步驟 1：複製 AI 提示詞"}
      </button>

      <div className="grid grid-cols-2 gap-2">
        <a
          href={AI_LINKS.chatgpt}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleAiLinkClick}
          className="py-2.5 text-center rounded-lg bg-white border border-gray-300 text-gray-700 text-sm font-medium hover:border-indigo-400 hover:text-indigo-700"
        >
          🤖 步驟 2：ChatGPT
        </a>
        <a
          href={AI_LINKS.gemini}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleAiLinkClick}
          className="py-2.5 text-center rounded-lg bg-white border border-gray-300 text-gray-700 text-sm font-medium hover:border-indigo-400 hover:text-indigo-700"
        >
          ✨ 步驟 2：Gemini
        </a>
      </div>

      <button
        onClick={() => setShowPreview((v) => !v)}
        className="text-xs text-indigo-600 hover:underline"
      >
        {showPreview ? "▲ 收合預覽" : "▼ 預覽提示詞內容"}
      </button>
      {showPreview && (
        <pre className="text-xs text-gray-600 bg-white border rounded p-3 whitespace-pre-wrap max-h-60 overflow-y-auto">
          {prompt}
        </pre>
      )}
    </div>
  );
}
