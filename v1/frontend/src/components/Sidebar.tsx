"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useI18n, LOCALE_LABELS, Locale } from "@/i18n";
import { logout } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { useUnreadCount } from "@/lib/useUnreadCount";
import { LoginModal } from "./LoginModal";
import { SearchBar } from "./SearchBar";
import {
  BellIcon,
  BluebirdIcon,
  DashboardIcon,
  ExploreIcon,
  HomeIcon,
  LayersIcon,
  LogoutIcon,
  MoreHorizontalIcon,
  PlusIcon,
  ReceiptIcon,
  SettingsIcon,
  ShieldAlertIcon,
  UserIcon,
  UsersIcon,
} from "./icons";

type NavItem = {
  href: string;
  label: string;
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  needsAuth?: boolean;
  adminOnly?: boolean;
  badge?: number;
};

export function Sidebar() {
  const { me } = useMe();
  const pathname = usePathname();
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginRedirect, setLoginRedirect] = useState<string | undefined>();
  const unread = useUnreadCount();
  const { t, locale, setLocale } = useI18n();

  async function handleLogout() {
    await logout();
  }

  const primary: NavItem[] = [
    { href: "/", label: t("nav.home"), Icon: HomeIcon },
    { href: "/feed", label: t("nav.feed"), Icon: LayersIcon },
    {
      href: "/following",
      label: t("nav.following"),
      Icon: UsersIcon,
      needsAuth: true,
    },
    { href: "/explore", label: t("nav.explore"), Icon: ExploreIcon },
    {
      href: "/notifications",
      label: t("nav.notifications"),
      Icon: BellIcon,
      needsAuth: true,
      badge: unread,
    },
  ];

  const secondary: NavItem[] = [
    { href: "/communities", label: t("nav.communities"), Icon: UsersIcon },
    {
      href: "/subscriptions",
      label: t("nav.subscription"),
      Icon: BluebirdIcon,
      needsAuth: true,
    },
    { href: "/orders", label: t("nav.orders"), Icon: ReceiptIcon, needsAuth: true },
    {
      href: "/warnings",
      label: t("nav.warnings"),
      Icon: ShieldAlertIcon,
      needsAuth: true,
    },
    { href: "/me/account", label: t("nav.settings"), Icon: SettingsIcon, needsAuth: true },
  ];

  // Admin은 별도 앱 (포트 3800)

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  const renderItem = (item: NavItem) => {
    if (item.needsAuth && !me) return null;
    if (item.adminOnly && me?.role !== "admin") return null;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href + item.label}
        href={item.href}
        className={`group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors ${
          active
            ? "text-primary"
            : "text-text-primary hover:bg-surface-hover"
        }`}
      >
        <span className="relative flex items-center justify-center">
          <item.Icon />
          {item.badge && item.badge > 0 ? (
            <span className="absolute -top-1 -right-2 bg-primary text-background text-[10px] rounded-full px-1.5 min-w-[18px] h-[18px] flex items-center justify-center font-semibold">
              {item.badge > 99 ? "99+" : item.badge}
            </span>
          ) : null}
        </span>
        <span className="hidden xl:inline text-lg font-medium">
          {item.label}
        </span>
      </Link>
    );
  };

  return (
    <>
      <aside className="hidden md:flex sticky top-0 h-screen flex-col justify-between py-4 px-2 xl:px-4 w-[80px] xl:w-[260px] border-r border-border bg-background flex-shrink-0">
        <div className="flex flex-col gap-1">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center justify-center xl:justify-start gap-2 px-3 py-3 mb-2 hover:bg-surface-hover rounded-full transition-colors"
          >
            <span className="text-primary text-2xl font-logo xl:hidden">
              DL
            </span>
            <span className="text-primary text-2xl font-logo hidden xl:inline">
              Domo Lounge
            </span>
          </Link>

          {/* Search */}
          <div className="mb-1">
            <div className="hidden xl:block">
              <SearchBar />
            </div>
            <div className="xl:hidden flex justify-center">
              <SearchBar compact />
            </div>
          </div>

          {/* Primary nav */}
          <nav className="flex flex-col gap-0.5">
            {primary.map(renderItem)}
          </nav>

          {/* Secondary divider */}
          {me && (
            <>
              <div className="border-t border-border my-2" />
              <nav className="flex flex-col gap-0.5">
                {secondary.map(renderItem)}
              </nav>
            </>
          )}

          {/* Admin — 별도 앱 링크 */}
          {me?.role === "admin" && (
            <>
              <div className="border-t border-border my-2" />
              <a
                href="http://localhost:3800"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors text-text-primary hover:bg-surface-hover"
              >
                <DashboardIcon />
                <span className="hidden xl:inline text-lg font-medium">{t("nav.admin")}</span>
              </a>
            </>
          )}

          {/* 등록 버튼 */}
          {me ? (
            <Link
              href="/posts/new"
              className={`group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors ${
                pathname.startsWith("/posts/new")
                  ? "text-primary"
                  : "text-text-primary hover:bg-surface-hover"
              }`}
            >
              <PlusIcon />
              <span className="hidden xl:inline text-lg font-medium">{t("nav.register")}</span>
            </Link>
          ) : (
            <button
              onClick={() => {
                setLoginRedirect("/posts/new");
                setLoginOpen(true);
              }}
              className="group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors text-text-primary hover:bg-surface-hover w-full"
            >
              <PlusIcon />
              <span className="hidden xl:inline text-lg font-medium">{t("nav.register")}</span>
            </button>
          )}

          {/* 로그인 (비로그인 상태에서만 노출) — 로그인 후엔 하단 사용자 메뉴에서 프로필 접근 */}
          {!me && (
            <button
              onClick={() => { setLoginRedirect(undefined); setLoginOpen(true); }}
              className="group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors text-text-primary hover:bg-surface-hover w-full"
            >
              <UserIcon />
              <span className="hidden xl:inline text-lg font-medium">{t("common.login")}</span>
            </button>
          )}
        </div>

        {/* Profile card at bottom */}
        {me && (
          <div className="relative">
            <details className="group">
              <summary className="list-none cursor-pointer flex items-center gap-3 rounded-full px-3 py-3 hover:bg-surface-hover transition-colors">
                <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-sm flex-shrink-0">
                  {me.avatar_url ? (
                    <img
                      src={me.avatar_url}
                      alt=""
                      className="w-full h-full rounded-full object-cover"
                    />
                  ) : (
                    <span className="text-primary font-bold">
                      {me.display_name.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="hidden xl:flex flex-col flex-1 min-w-0 text-left">
                  <span className="text-sm font-semibold text-text-primary truncate">
                    @{me.display_name}
                  </span>
                  <span className="text-xs text-text-muted truncate">
                    {me.role}
                  </span>
                </div>
                <span className="hidden xl:inline text-text-muted">
                  <MoreHorizontalIcon size={20} />
                </span>
              </summary>
              <div className="absolute bottom-full mb-2 left-0 right-0 xl:left-2 xl:right-2 card p-2 z-40 space-y-1">
                <Link
                  href={`/users/${me.id}`}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <UserIcon />
                  <span>{t("nav.profile")}</span>
                </Link>
                <div className="border-t border-border my-1" />
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <LogoutIcon size={18} />
                  <span>{t("common.logout")}</span>
                </button>
              </div>
            </details>
          </div>
        )}

        {/* Language switcher */}
        <div className="mx-3 mb-2">
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            className="w-full bg-surface border border-border rounded-full px-3 py-1.5 text-xs text-text-muted focus:border-primary outline-none cursor-pointer"
          >
            {(Object.entries(LOCALE_LABELS) as [Locale, { flag: string; name: string }][]).map(
              ([code, { flag, name }]) => (
                <option key={code} value={code}>
                  {flag} {name}
                </option>
              )
            )}
          </select>
        </div>
      </aside>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} redirectTo={loginRedirect} />
    </>
  );
}
