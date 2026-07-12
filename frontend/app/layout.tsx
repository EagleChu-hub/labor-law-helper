import type { Metadata } from "next";
import { Noto_Sans_TC, Sora } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/shared/AppShell";

const notoSansTC = Noto_Sans_TC({
  subsets: ["latin"],
  weight: ["400", "500", "700", "900"],
  variable: "--font-noto",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-sora",
  display: "swap",
});

export const metadata: Metadata = {
  title: "勞基法小幫手 — 了解你的勞工權益",
  description: "輸入出勤狀況，立即判斷是否違反勞基法。支援情境詢問與法條查詢。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW" className={`${notoSansTC.variable} ${sora.variable}`}>
      <body className="antialiased bg-canvas text-ink font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
