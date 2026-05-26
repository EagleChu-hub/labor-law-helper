import type { CheckRequest, CheckResult, AskRequest, AskResponse, LawSearchResponse } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * C-3：帶 timeout 的 fetch，超時後拋出 COLD_START_TIMEOUT 錯誤。
 * 用於偵測 Render 免費方案的冷啟動（約 30 秒），讓前端可顯示等待提示並自動重試。
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
