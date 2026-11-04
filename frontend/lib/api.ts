import type { CheckRequest, CheckResult, AskRequest, AskResponse, LawSearchResponse } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * C-3：帶 timeout 的 fetch，超時後拋出 COLD_START_TIMEOUT 錯誤。
 * 用於偵測 Render 免費方案的冷啟動（約 1 分鐘），讓前端可顯示等待提示並自動重試。
 */
async function fetchWithTimeout(
  input: string,
  init?: RequestInit,
  timeoutMs = 65000,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") {
      throw new Error("COLD_START_TIMEOUT");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function fetchJSON<T>(path: string, options?: RequestInit, withTimeout = false): Promise<T> {
  const fetcher = withTimeout ? fetchWithTimeout : fetch;
  const res = await fetcher(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

/**
 * 先把後端叫醒（fire-and-forget）。
 * Render 免費方案閒置 15 分鐘就休眠，醒來要 約 1 分鐘；
 * 勞工填出勤表要 1～3 分鐘，進表單時先叫醒，送出時伺服器就已經醒了。
 */
export function wakeBackend(): void {
  fetch(`${BASE_URL}/`).catch(() => {});
}

/**
 * 法條搜尋的索引在第一次搜尋時才建立（bm25_retriever 的 lru_cache），
 * 2026-11 實測第一次搜尋要 28 秒、之後 0.25 秒。進頁面就先查一次，讓索引在使用者打字時建好。
 */
export function warmLawSearch(): void {
  fetch(`${BASE_URL}/api/v1/law/search?q=${encodeURIComponent("加班費")}`).catch(() => {});
}

export async function checkAnalyze(request: CheckRequest): Promise<CheckResult> {
  return fetchJSON<CheckResult>(
    "/api/v1/check/analyze",
    { method: "POST", body: JSON.stringify(request) },
    true, // 啟用 65 秒 timeout，讓冷啟動提示有機會顯示
  );
}

export async function askChat(request: AskRequest): Promise<AskResponse> {
  return fetchJSON<AskResponse>("/api/v1/ask/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function lawSearch(query: string): Promise<LawSearchResponse> {
  return fetchJSON<LawSearchResponse>(`/api/v1/law/search?q=${encodeURIComponent(query)}`);
}
