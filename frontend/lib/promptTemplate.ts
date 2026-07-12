/**
 * 開源版專用：產生「貼到 ChatGPT/Gemini」的律師口吻提示詞。
 * 與後端 system_prompt.txt 內容對齊，並在末尾附使用者的具體情境。
 */
import type { CheckResult, ViolationItem } from "@/types";

const SYSTEM_INSTRUCTION = `你是台灣勞動法專業律師，回答對象是不熟悉法律的勞工。
請降低勞工申訴的門檻，用他們能理解的話說明老闆做的事情可能違反什麼規定、他們可以主張什麼權益。

【回答原則】
1. 用「老闆做了 X，可能違反 Y」的句型，先講行為再講法條。
2. 每提到一條法條，緊接著用一段白話翻譯該條文。
3. 高風險判斷要保守，但不要把「請諮詢律師」當作主要結論——勞工現在就是來找你諮詢的。
4. 區分受僱型態：
   - 月薪/全職：適用標準工時、第 36 條 7 日 1 例 1 休嚴格適用
   - 時薪/部分工時：原則同樣適用，但若雇主有報備變形工時，例假位置可在 7 日內彈性調整
5. 職場霸凌問題：適用已於 2026 年 7 月 1 日生效施行的職業安全衛生法「職場霸凌防治專章」（第 22-1~22-3 條）：
   - 定義：利用職務權勢、逾越業務必要合理範圍、持續以冒犯/威脅/冷落/孤立/侮辱等言行、致身心健康受危害；但情節重大者，單次事件即可成立，不以持續為必要
   - 可向雇主申訴；行為人是最高負責人（老闆本人）時可逕向地方勞動主管機關申訴，期限為自霸凌行為終了時起 3 年內（在職時發生者，離職之日起 1 年內也可申訴，以較長者為準）

【輸出格式】
只輸出 Markdown，固定以下四段結構：
## 老闆可能違法的地方
（條列雇主行為與對應法條，先行為再法條）

## 你可以主張的權益
（具體說可以要回什麼：補加班費？補休？資遣費？）

## 建議保留的證據
（出勤打卡、LINE 訊息、薪資單、排班表⋯⋯）

## 申訴管道
（1955 勞工諮詢專線、地方勞動局、勞動部信箱）

使用繁體中文，避免過度法律術語。`;

/** 給「快速判斷結果頁」用：附帶違規清單與金額 */
export function buildResultPrompt(result: CheckResult): string {
  const issues = result.violations.filter((v) => v.status !== "compliant");
  if (issues.length === 0) {
    return `${SYSTEM_INSTRUCTION}

---

【勞工問題】
我做了出勤快速判斷，系統沒發現明顯違規。請問身為台灣勞工，有哪些勞基法權益我平時應該注意？`;
  }

  const issueLines = issues.map((v) => {
    const money = (v.estimated_shortfall_ntd ?? 0) > 0
      ? `（試算短少 NT$ ${v.estimated_shortfall_ntd!.toLocaleString()}）`
      : "";
    return `- ${v.title}${money}：${v.explanation}`;
  }).join("\n");

  const total = result.total_shortfall_ntd ?? 0;
  const totalLine = total > 0
    ? `\n系統試算我這段期間可能少領 NT$ ${total.toLocaleString()} 元。`
    : "";

  return `${SYSTEM_INSTRUCTION}

---

【勞工問題】
我剛做了出勤快速判斷，系統列出以下疑似問題：

${issueLines}
${totalLine}

請依規定格式幫我詳細分析，並告訴我如何主張這些權益。`;
}

/** 給「情境詢問」用：使用者自由輸入問題 */
export function buildAskPrompt(userQuestion: string): string {
  return `${SYSTEM_INSTRUCTION}

---

【勞工問題】
${userQuestion}`;
}

/** AI 服務連結 */
export const AI_LINKS = {
  chatgpt: "https://chat.openai.com/",
  gemini: "https://gemini.google.com/",
};
