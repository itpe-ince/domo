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
    label: "Security",
    items: [
      { href: "/settings/passkeys", label: "패스키" },
      { href: "/settings/recovery-codes", label: "복구 코드" },
    ],
  },
  {
    label: "System",
    items: [{ href: "/settings", label: "시스템 설정" }],
  },
];

// Routes that render fullscreen without the admin sidebar.
// Used for auth gates / forced-flow pages where the admin must complete
// a step before accessing the rest of the console.
const STANDALONE_ROUTES = new Set<string>([
  "/login",
  "/settings/totp-setup",
]);

// Routes admin without 2FA can still reach (TOTP/Passkey enrollment paths,
// own-account routes). All other routes redirect to /settings/totp-setup.
// This is a defense-in-depth — the BACKEND is the authority via
// `require_admin_with_2fa`, which returns SECOND_FACTOR_REQUIRED 403.
const ALLOW_WITHOUT_2FA = new Set<string>([
  "/login",
  "/settings/totp-setup",
  "/settings/passkeys",
  "/settings/recovery-codes",
]);

function isStandalonePath(pathname: string): boolean {
  return STANDALONE_ROUTES.has(pathname);
}

function needsSecondFactor(me: ApiUser | null): boolean {
  if (!me || me.role !== "admin") return false;
  // If backend doesn't expose the field (older API), fall back to TOTP check
  if (typeof me.second_factor_enrolled === "boolean") {
    return !me.second_factor_enrolled;
  }
  return !me.totp_enabled_at && !(me.passkey_count && me.passkey_count > 0);
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<ApiUser | null>(null);

  const isStandalone = isStandalonePath(pathname);

  useEffect(() => {
    if (isStandalone) return;
    void loadMe();
    const handler = () => void loadMe();
    window.addEventListener(AUTH_CHANGED_EVENT, handler);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStandalone]);

  // Force first-time admin (no TOTP and no Passkey) into setup flow no
  // matter what URL they typed. Bypass attempt → instant redirect.
  useEffect(() => {
    if (!me) return;
    if (needsSecondFactor(me) && !ALLOW_WITHOUT_2FA.has(pathname)) {
      router.replace("/settings/totp-setup");
    }
  }, [me, pathname, router]);

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

  if (isStandalone) {
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
