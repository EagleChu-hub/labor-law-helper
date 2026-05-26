import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/shared/AppShell";

export const metadata: Metadata = {
  title: "勞基法小幫手 — 了解你的勞工權益",
  description: "輸入出勤狀況，立即判斷是否違反勞基法。支援情境詢問與法條查詢。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW">
      <body className="antialiased bg-gray-50">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
