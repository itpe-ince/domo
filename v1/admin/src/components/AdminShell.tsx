"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiUser,
  AUTH_CHANGED_EVENT,
  fetchMe,
  logout,
  tokenStore,
} from "@/lib/api";

const NAV_GROUPS: { label: string; items: { href: string; label: string }[] }[] = [
  {
    label: "Overview",
    items: [{ href: "/dashboard", label: "대시보드" }],
  },
  {
    label: "Operations",
    items: [
      { href: "/users", label: "유저 관리" },
      { href: "/schools", label: "학교 관리" },
      { href: "/applications", label: "작가 심사" },
      { href: "/posts", label: "콘텐츠 관리" },
      { href: "/transactions", label: "거래 관리" },
      { href: "/moderation", label: "모더레이션" },
    ],
  },
  {
    label: "System",
    items: [{ href: "/settings", label: "시스템 설정" }],
  },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<ApiUser | null>(null);

  // Login page renders fullscreen without sidebar
  const isLoginRoute = pathname === "/login";

  useEffect(() => {
    if (isLoginRoute) return;
    void loadMe();
    const handler = () => void loadMe();
    window.addEventListener(AUTH_CHANGED_EVENT, handler);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoginRoute]);

  async function loadMe() {
    if (!tokenStore.get()) {
      setMe(null);
      return;
    }
    try {
      const u = await fetchMe();
      setMe(u);
    } catch {
      setMe(null);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard" || pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  if (isLoginRoute) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen bg-admin-bg">
      <aside className="w-60 flex-shrink-0 bg-admin-surface border-r border-admin-border flex flex-col">
        <div className="px-5 py-4 border-b border-admin-border">
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-admin-accent/15 ring-1 ring-admin-accent/30">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-3.5 w-3.5 text-admin-accent"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </span>
            <div className="leading-tight">
              <div className="text-admin-fg text-sm font-semibold tracking-tight">
                Domo
              </div>
              <div className="text-admin-muted text-[10px] uppercase tracking-widest">
                Admin Console
              </div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-5">
              <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-admin-muted">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`block px-3 py-1.5 rounded-md text-[13px] transition-colors ${
                      isActive(item.href)
                        ? "bg-admin-accent/10 text-admin-accent font-medium border-l-2 border-admin-accent pl-[10px]"
                        : "text-admin-fg-soft hover:bg-admin-surface-2 hover:text-admin-fg"
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-admin-border p-3 space-y-2">
          {me && (
            <div className="flex items-center gap-2 px-2 py-1.5">
              <div className="h-7 w-7 rounded-full bg-admin-accent/20 flex items-center justify-center text-admin-accent text-xs font-semibold">
                {me.display_name?.[0]?.toUpperCase() ?? "A"}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-admin-fg text-xs font-medium truncate">
                  {me.display_name}
                </div>
                <div className="text-admin-muted text-[10px] truncate">
                  {me.email}
                </div>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2">
            <a
              href="http://localhost:3700"
              target="_blank"
              className="flex-1 text-center text-[11px] text-admin-muted hover:text-admin-accent border border-admin-border rounded-md py-1.5 transition-colors"
            >
              사용자 앱 ↗
            </a>
            {me && (
              <button
                onClick={handleLogout}
                className="text-[11px] text-admin-muted hover:text-admin-danger border border-admin-border rounded-md py-1.5 px-2.5 transition-colors"
              >
                로그아웃
              </button>
            )}
          </div>
        </div>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
