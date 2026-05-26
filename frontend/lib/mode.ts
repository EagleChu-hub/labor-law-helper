/**
 * 應用模式切換。
 *
 * - `private`（預設）：完整版，按 AI 按鈕後呼叫後端 /api/v1/ask/chat，吃 Gemini quota。
 *   供作者自己與親友使用，網址私下分享。
 *
 * - `opensource`：開源版，AI 按鈕改為「複製提示詞 → 跳轉 ChatGPT/Gemini」，
 *   不打後端 LLM API。供公開分享，避免免費 quota 被吃光。
 *
 * 透過 Vercel 環境變數 `NEXT_PUBLIC_MODE=opensource|private` 切換，
 * 同一份 GitHub repo 部署兩個 Vercel 專案。
 */
export type AppMode = "private" | "opensource";

export const APP_MODE: AppMode =
  (process.env.NEXT_PUBLIC_MODE as AppMode) || "private";

export const IS_OPENSOURCE = APP_MODE === "opensource";
export const IS_PRIVATE = APP_MODE === "private";
