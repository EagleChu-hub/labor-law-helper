"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ClipboardCheck, MessageCircle, BookOpen, Scale, Compass } from "lucide-react";

// ⚠️ 手機底部是 flex-1 均分，5 項時標籤要夠短（4 字以內）才不會擠壓
const navItems = [
  { href: "/", label: "首頁", icon: Home },
  { href: "/triage", label: "怎麼辦", icon: Compass },
  { href: "/check", label: "快速判斷", icon: ClipboardCheck },
  { href: "/ask", label: "情境詢問", icon: MessageCircle },
  { href: "/law", label: "法條查詢", icon: BookOpen },
];

function BrandMark({ size }: { size: number }) {
  return (
    <span
      className="rounded-[10px] bg-white/10 flex items-center justify-center text-gold shrink-0"
      style={{ width: size, height: size }}
    >
      <Scale size={Math.round(size * 0.56)} strokeWidth={1.75} />
    </span>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      {/* Desktop top nav */}
      <header className="hidden md:block bg-gradient-to-r from-navy-800 to-navy-900 shadow-md">
        <div className="max-w-5xl mx-auto px-6 py-3.5 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 text-white">
            <BrandMark size={34} />
            <span className="font-black text-base tracking-tight">勞基法小幫手</span>
          </Link>
          <nav className="flex items-center gap-7 text-sm font-medium">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`pb-[3px] border-b-2 transition-colors ${
                    active
                      ? "text-white font-bold border-gold"
                      : "text-white/[0.72] border-transparent hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Mobile top bar */}
      <header className="md:hidden bg-gradient-to-r from-navy-800 to-navy-900 px-4 py-3 flex items-center gap-2.5 text-white">
        <BrandMark size={30} />
        <span className="font-black">勞基法小幫手</span>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 pb-24 md:pb-6">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-card border-t border-line flex safe-area-pb">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 flex flex-col items-center py-2 text-xs gap-1 transition-colors ${
                active ? "text-navy font-semibold" : "text-muted"
              }`}
            >
              <Icon size={19} strokeWidth={active ? 2 : 1.75} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
