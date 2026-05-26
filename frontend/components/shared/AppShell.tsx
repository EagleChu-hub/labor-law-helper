"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "首頁", icon: "🏠" },
  { href: "/check", label: "快速判斷", icon: "✅" },
  { href: "/ask", label: "情境詢問", icon: "💬" },
  { href: "/law", label: "法條查詢", icon: "📖" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Desktop top nav */}
      <header className="hidden md:block bg-teal-700 text-white shadow-md">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="font-bold text-lg tracking-tight">
            ⚖️ 勞基法小幫手
          </Link>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  pathname === item.href ? "bg-teal-900" : "hover:bg-teal-600"
                }`}
              >
                {item.icon} {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Mobile top bar */}
      <header className="md:hidden bg-teal-700 text-white px-4 py-3 flex items-center">
        <span className="font-bold">⚖️ 勞基法小幫手</span>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 pb-24 md:pb-6">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 flex safe-area-pb">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex-1 flex flex-col items-center py-2 text-xs gap-0.5 transition-colors ${
              pathname === item.href ? "text-teal-700 font-semibold" : "text-gray-500"
            }`}
          >
            <span className="text-lg">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
