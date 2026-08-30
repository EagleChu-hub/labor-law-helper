import Link from "next/link";
import { Compass, ClipboardCheck } from "lucide-react";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";

/**
 * 誕生故事。
 *
 * 文案集中在下方常數，換版只需改 ORIGIN_STORY 指向哪一個陣列。
 * 兩個版本語氣不同，內容都不涉及任何具體人事時地。
 */
const STORY_B = [
  "我聽到一件事。",
  "然後才發現：法律其實站在勞工這邊，但站得離他很遠。",
  "條文寫得清楚，可是要先知道去哪裡查、知道該問什麼、知道自己有立場問——這三件事，沒有一件是理所當然的。",
  "後來去看網路上其他人的處境，發現卡住的地方幾乎一模一樣：「我不敢」「聽說沒用」「證據都在老闆手上」「我不知道下一步要幹嘛」。",
  "於是把一步一步查出來的東西整理起來，做成這個網站。",
  "它不會幫你打官司。它做的是更前面的事：讓你知道明天可以做什麼，知道走進那扇門的時候要怎麼開口。",
];

/** 退路版本：素材全部來自公開的網路貼文 */
const STORY_A = [
  "這個網站不是從「勞工需要懂法律」這個想法開始的。",
  "是從一句一句真實的抱怨開始的。在網路上，你會一直看到同樣幾句話：「我不敢，怕被認出來是我。」「勞工局申訴根本沒用吧？」「證據都在老闆手上，我要不到。」「我知道我被坑了，可是我不知道下一步要幹嘛。」",
  "這些話裡面沒有一句在問法條。他們卡住的地方，法律其實都有答案——只是那些答案被寫在一般人不會去讀、讀了也看不懂的地方。",
  "而且會被坑的人，往往就是最沒有餘力去讀那些東西的人。有辦法的人自己就找得到辦法；真正需要幫忙的，是下班已經很累、看到「調解」「執行名義」這種詞就想關掉的人。",
  "所以這個網站的目標不是把法律講完整，是讓你明天知道要做什麼、知道怎麼開口。",
  "如果你正卡在上面那幾句話裡面——你不是唯一一個。",
];

const ORIGIN_STORY = STORY_B;

// 讓 STORY_A 不被視為未使用（保留為可切換的版本）
void STORY_A;

export const metadata = {
  title: "這個網站為什麼在 — 勞基法小幫手",
};

export default function AboutPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-7">
      <h1 className="text-[27px] font-black text-ink leading-tight">這個網站為什麼在</h1>

      <div className="space-y-5">
        {ORIGIN_STORY.map((p) => (
          <p key={p} className="text-[17px] text-ink leading-[1.95]">
            {p}
          </p>
        ))}
      </div>

      <div className="rounded-[20px] border border-line bg-card p-6 space-y-4">
        <p className="text-[16px] font-black text-ink">從哪裡開始都可以</p>
        <div className="grid gap-3">
          <Link
            href="/triage"
            className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-line bg-canvas hover:border-navy-600 transition"
          >
            <span className="w-11 h-11 rounded-xl bg-navy-50 flex items-center justify-center text-navy shrink-0">
              <Compass size={22} strokeWidth={1.75} />
            </span>
            <span className="flex-1">
              <span className="block text-[15.5px] font-extrabold text-ink">我該怎麼辦？</span>
              <span className="block text-[13.5px] text-muted mt-0.5">回答幾個問題，告訴你明天可以做什麼</span>
            </span>
          </Link>
          <Link
            href="/check"
            className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-line bg-canvas hover:border-navy-600 transition"
          >
            <span className="w-11 h-11 rounded-xl bg-navy-50 flex items-center justify-center text-navy shrink-0">
              <ClipboardCheck size={22} strokeWidth={1.75} />
            </span>
            <span className="flex-1">
              <span className="block text-[15.5px] font-extrabold text-ink">先算算我的班表對不對</span>
              <span className="block text-[13.5px] text-muted mt-0.5">工時、加班費、排休——填一週紀錄自動檢查</span>
            </span>
          </Link>
        </div>
      </div>

      <DisclaimerBanner />
    </div>
  );
}
