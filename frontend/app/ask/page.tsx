"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { ChatThread } from "@/components/ask/ChatThread";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { OpenSourceAiButtons } from "@/components/shared/OpenSourceAiButtons";
import { askChat } from "@/lib/api";
import { IS_OPENSOURCE } from "@/lib/mode";
import { buildAskPrompt } from "@/lib/promptTemplate";
import type { ChatMessage, AskResponse } from "@/types";

const EXAMPLE_QUESTIONS = [
  "老闆叫我連上 7 天班，合法嗎？",
  "加班費怎麼計算？",
  "被要求假日出勤有加班費嗎？",
  "年假有幾天？什麼時候可以請？",
  "資遣費怎麼算？",
];

function AssistantAnswer({ answer }: { answer: AskResponse }) {
  const hasMarkdown = !!answer.markdown && answer.markdown.trim().length > 0;
  return (
    <div className="space-y-3 bg-white border border-gray-200 rounded-2xl rounded-bl-none shadow-sm p-4">
      {hasMarkdown ? (
        // 新版：律師口吻 Markdown 渲染
        <div className="prose prose-sm max-w-none text-gray-800
          prose-headings:text-gray-900 prose-headings:font-bold
          prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2 prose-h2:pb-1 prose-h2:border-b prose-h2:border-gray-200
          prose-p:my-2 prose-p:leading-relaxed
          prose-ul:my-2 prose-li:my-1
          prose-strong:text-teal-800">
          <ReactMarkdown>{answer.markdown!}</ReactMarkdown>
        </div>
      ) : (
        // 向後相容：舊版欄位
        <>
          <p className="font-semibold text-gray-800">{answer.headline}</p>
          {answer.summary && <p className="text-sm text-gray-700">{answer.summary}</p>}
          {answer.reasoning && (
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer text-teal-700 font-medium">查看法律依據</summary>
              <p className="mt-2">{answer.reasoning}</p>
            </details>
          )}
        </>
      )}
      {answer.law_references.length > 0 && (
        <div className="space-y-1 pt-1 border-t">
          <p className="text-xs font-medium text-gray-500">引用法條與判決</p>
          {answer.law_references.map((ref) => (
            <a
              key={ref.article_no + ref.title}
              href={ref.source_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs hover:underline"
            >
              {ref.doc_type === "judgment" ? (
                <>
                  <span className="shrink-0 rounded-full bg-orange-100 text-orange-700 px-1.5 py-0.5 font-medium">法院判決</span>
                  <span className="text-orange-800">{ref.title}</span>
                </>
              ) : (
                <span className="text-teal-700">勞基法 {ref.article_no}：{ref.title}</span>
              )}
            </a>
          ))}
        </div>
      )}
      {answer.followup_questions.length > 0 && (
        <div className="space-y-1 pt-1 border-t">
          <p className="text-xs font-medium text-gray-500">相關問題</p>
          <div className="flex flex-wrap gap-2">
            {answer.followup_questions.map((q) => (
              <span key={q} className="text-xs border border-teal-300 text-teal-700 rounded-full px-2 py-0.5 cursor-pointer hover:bg-teal-50">
                {q}
              </span>
            ))}
          </div>
        </div>
      )}
      {/* Complaint links */}
      <div className="pt-1 border-t">
        <p className="text-xs font-medium text-gray-500 mb-2">如需申訴，可透過以下管道：</p>
        <div className="flex flex-wrap gap-2">
          <a
            href="https://ap.bola.gov.taipei/LZ.aspx"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs bg-red-50 border border-red-300 text-red-700 rounded-full px-3 py-1 hover:bg-red-100"
          >
            台北市政府勞動局申訴
          </a>
          <a
            href="https://romeodex.osha.gov.tw/PO/WriteMail"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs bg-red-50 border border-red-300 text-red-700 rounded-full px-3 py-1 hover:bg-red-100"
          >
            勞動部申訴信箱
          </a>
          <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-3 py-1">
            專線：1955
          </span>
        </div>
      </div>
    </div>
  );
}

/** 開源版 ask 頁面：使用者打字 → 預覽 + 複製提示詞 → 跳 ChatGPT/Gemini */
function OpenSourceAskInner() {
  const searchParams = useSearchParams();
  const [input, setInput] = useState(searchParams.get("q") ?? "");
  const [prompt, setPrompt] = useState<string | null>(null);

  function generate() {
    const msg = input.trim();
    if (!msg) return;
    setPrompt(buildAskPrompt(msg));
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-800">情境詢問（開源版）</h1>
        <p className="text-sm text-gray-500">本網站不送資料到伺服器，請複製提示詞到 ChatGPT / Gemini 詢問</p>
      </div>

      <div className="bg-white border rounded-xl p-4 space-y-3">
        <label className="text-sm font-medium text-gray-700">描述你的情況</label>
        <textarea
          rows={4}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例如：老闆叫我連上 7 天班、加班費沒有給、休息日叫我來上班..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => setInput(q)}
              className="text-xs border border-gray-200 rounded-full px-3 py-1 text-gray-600 hover:border-indigo-400 hover:text-indigo-700"
            >
              {q}
            </button>
          ))}
        </div>
        <button
          onClick={generate}
          disabled={!input.trim()}
          className="w-full bg-indigo-700 text-white rounded-lg py-3 font-semibold hover:bg-indigo-800 disabled:opacity-50"
        >
          生成 AI 提示詞
        </button>
      </div>

      {prompt && <OpenSourceAiButtons prompt={prompt} />}

      <DisclaimerBanner />
    </div>
  );
}

function AskPageInner() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [answers, setAnswers] = useState<Map<number, AskResponse>>(new Map());
  const [input, setInput] = useState(searchParams.get("q") ?? "");
  const [loading, setLoading] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 載入中計時器
  useEffect(() => {
    if (!loading) {
      setElapsedSec(0);
      return;
    }
    const t = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");

    const userMsg: ChatMessage = { role: "user", content: msg };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const res = await askChat({ message: msg, history: messages });
      const assistantMsg: ChatMessage = { role: "assistant", content: res.headline };
      const idx = nextMessages.length;
      setAnswers((prev) => new Map(prev).set(idx, res));
      setMessages([...nextMessages, assistantMsg]);
    } catch {
      setMessages([...nextMessages, { role: "assistant", content: "發生錯誤，請稍後再試。" }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-4 h-[calc(100vh-12rem)]">
      <div>
        <h1 className="text-xl font-bold text-gray-800">情境詢問</h1>
        <p className="text-sm text-gray-500">用自然語言描述你的情況，AI 會根據勞基法給出分析</p>
      </div>

      {messages.length === 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">常見問題</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="text-xs border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 hover:border-teal-400 hover:text-teal-700 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 pb-2">
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="bg-teal-700 text-white rounded-2xl rounded-br-none px-4 py-3 text-sm max-w-[85%]">
                  {msg.content}
                </div>
              </div>
            ) : answers.has(i) ? (
              <AssistantAnswer answer={answers.get(i)!} />
            ) : (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 text-sm max-w-[85%] text-gray-800">
                  {msg.content}
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 text-sm text-gray-500">
              <span className="animate-pulse">⚖️ AI 律師正在比對法條與撰寫分析…</span>
              <span className="ml-2 text-xs text-gray-400">({elapsedSec}s)</span>
              {elapsedSec >= 60 && (
                <p className="text-xs text-amber-600 mt-1">AI 律師正在努力比對您的案件中</p>
              )}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="space-y-2">
        <DisclaimerBanner />
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="描述你的情況，例如：老闆叫我連上 7 天班..."
            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="bg-teal-700 text-white rounded-xl px-4 py-3 font-semibold hover:bg-teal-800 disabled:opacity-50 transition-colors"
          >
            送出
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AskPage() {
  return (
    <Suspense>
      {IS_OPENSOURCE ? <OpenSourceAskInner /> : <AskPageInner />}
    </Suspense>
  );
}
