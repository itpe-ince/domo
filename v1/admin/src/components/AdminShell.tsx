"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/users", label: "유저 관리" },
  { href: "/schools", label: "학교 관리" },
  { href: "/applications", label: "작가 심사" },
  { href: "/posts", label: "콘텐츠 관리" },
  { href: "/transactions", label: "거래 관리" },
  { href: "/moderation", label: "모더레이션" },
  { href: "/settings", label: "시스템 설정" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard" || pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 flex-shrink-0 bg-surface border-r border-border">
        <div className="p-4 border-b border-border">
          <Link href="/dashboard" className="text-lg font-bold text-primary font-serif italic">
            Domo Admin
          </Link>
        </div>
        <nav className="p-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive(item.href)
                  ? "bg-primary/10 text-primary font-semibold"
                  : "text-text-secondary hover:bg-surface-hover"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 mt-auto border-t border-border">
          <a
            href="http://localhost:3700"
            target="_blank"
            className="text-xs text-text-muted hover:text-primary"
          >
            ← 사용자 앱으로
          </a>
        </div>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
