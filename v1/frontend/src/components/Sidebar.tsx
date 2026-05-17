"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useI18n } from "@/i18n";
import { logout } from "@/lib/api";
import { captureEvent, resetIdentity } from "@/lib/analytics/capture";
import { useMe } from "@/lib/useMe";
import { useUnreadCount } from "@/lib/useUnreadCount";
import { useOnboarding } from "@/lib/hooks/useOnboarding";
import { LoginModal } from "./LoginModal";
import { SearchBar } from "./SearchBar";
import {
  BellIcon,
  BluebirdIcon,
  BookOpenIcon,
  DashboardIcon,
  DraftIcon,
  ExploreIcon,
  HeartHandshakeIcon,
  HomeIcon,
  LayersIcon,
  LogoutIcon,
  MessageCircleIcon,
  MoreHorizontalIcon,
  PlusIcon,
  ReceiptIcon,
  SettingsIcon,
  ShieldAlertIcon,
  TrophyIcon,
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
  const { me, loading: meLoading } = useMe();
  const pathname = usePathname();
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginRedirect, setLoginRedirect] = useState<string | undefined>();
  const unread = useUnreadCount();
  const { t } = useI18n();
  const { isFirstSession, reopenWizard } = useOnboarding();

  async function handleLogout() {
    captureEvent({ type: "logout" });
    resetIdentity();
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
    // B'-2 dm-messaging
    {
      href: "/me/messages",
      label: t("nav.messages"),
      Icon: MessageCircleIcon,
      needsAuth: true,
    },
  ];

  const secondary: NavItem[] = [
    // A-7 storytelling-hub — public (no auth required)
    { href: "/stories", label: t("nav.stories"), Icon: BookOpenIcon },
    // A-6 artist-index-v1 — global ranking page (public, no auth required)
    { href: "/artists/index", label: t("nav.artistIndex"), Icon: TrophyIcon },
    { href: "/communities", label: t("nav.communities"), Icon: UsersIcon },
    {
      href: "/subscriptions",
      label: t("nav.subscription"),
      Icon: BluebirdIcon,
      needsAuth: true,
    },
    {
      href: "/me/sponsorships",
      label: t("nav.mySponsoring"),
      Icon: HeartHandshakeIcon,
      needsAuth: true,
    },
    // artist-patronage-dashboard B-2 + tier-benefits B-4 — 작가 본인만 표시
    ...(me?.role === "artist"
      ? [
          {
            href: "/me/patronage",
            label: t("nav.patronageDashboard"),
            Icon: DashboardIcon,
            needsAuth: true,
          } as NavItem,
          {
            href: "/me/tier-benefits",
            label: t("nav.tierBenefits"),
            Icon: HeartHandshakeIcon,
            needsAuth: true,
          } as NavItem,
        ]
      : []),
    { href: "/orders", label: t("nav.orders"), Icon: ReceiptIcon, needsAuth: true },
    {
      href: "/warnings",
      label: t("nav.warnings"),
      Icon: ShieldAlertIcon,
      needsAuth: true,
    },
    { href: "/me/settings", label: t("nav.settings"), Icon: SettingsIcon, needsAuth: true },
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
      {/* z-50: establish a stacking context above CookieConsent(z-40)/page sticky headers(z-20)
          so the bottom user-menu dropdown (which overflows right via left-full) is not occluded. */}
      <aside className="hidden md:flex sticky top-0 z-50 h-screen flex flex-col min-h-0 py-4 px-2 xl:px-4 w-[80px] xl:w-[260px] border-r border-border bg-background flex-shrink-0">
        <div className="flex flex-col flex-1 min-h-0">
          {/* 스크롤은 상단 내비만 — 프로필 메뉴는 하단 고정, 드롭다운이 overflow에 잘리지 않음 */}
          <div className="flex-1 overflow-y-auto min-h-0 overscroll-contain flex flex-col gap-1">
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

          {/* A-2: Onboarding indicator for first-session authenticated users */}
          {me && isFirstSession && (
            <>
              <div className="border-t border-border my-2" />
              <button
                type="button"
                onClick={reopenWizard}
                className="group flex items-center justify-center xl:justify-start gap-3 rounded-xl px-3 py-2.5 w-full bg-primary/10 hover:bg-primary/15 transition-colors text-left"
                aria-label={t("onboarding.sidebar.indicator")}
              >
                <span className="text-primary text-lg flex-shrink-0" aria-hidden="true">🎨</span>
                <span className="hidden xl:flex flex-col flex-1 min-w-0">
                  <span className="text-xs font-semibold text-primary truncate">
                    {t("onboarding.sidebar.title")}
                  </span>
                  <span className="text-[10px] text-text-muted truncate">
                    {t("onboarding.sidebar.hint")}
                  </span>
                </span>
              </button>
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

          {/* 로그인 버튼 — me가 확정된 비로그인 상태에서만 노출.
              meLoading=true 동안엔 placeholder를 두어 비로그인↔로그인 깜빡임 방지. */}
          {meLoading ? (
            <div
              className="h-12 mx-3 rounded-full bg-surface-hover/40 animate-pulse"
              aria-hidden
            />
          ) : !me ? (
            <button
              onClick={() => { setLoginRedirect(undefined); setLoginOpen(true); }}
              className="group flex items-center justify-center xl:justify-start gap-4 rounded-full px-3 py-3 transition-colors text-text-primary hover:bg-surface-hover w-full"
            >
              <UserIcon />
              <span className="hidden xl:inline text-lg font-medium">{t("common.login")}</span>
            </button>
          ) : null}
          </div>

        {/* Profile card at bottom — meLoading 동안 placeholder로 layout shift 방지 */}
        {meLoading && (
          <div className="flex-shrink-0 mx-3 mt-2 mb-2 h-14 rounded-full bg-surface-hover/40 animate-pulse" aria-hidden />
        )}
        {/* 비로그인 PreferencesCard 제거 — 통화/언어 변경은 /me/settings/display에서 처리 */}
        {!meLoading && me && (
          <div className="relative flex-shrink-0 mt-auto pt-2">
            <details className="group">
              <summary
                className="list-none cursor-pointer flex items-center gap-3 rounded-full px-3 py-3 hover:bg-surface-hover transition-colors [&::-webkit-details-marker]:hidden"
                aria-label={t("nav.moreMenu")}
              >
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
                <span className="flex-shrink-0 text-text-muted ml-auto xl:ml-0" aria-hidden>
                  <MoreHorizontalIcon size={20} />
                </span>
              </summary>
              {/* Dropdown
                  - 축소 (xl 미만): 사이드바 옆(right)으로 펼침 — 상단 스크롤 영역과 분리해 overflow 클리핑 방지
                  - 확장 (xl 이상): 사이드바 안에서 위로 펼침 */}
              <div
                className="absolute z-[100] card p-2 space-y-1 w-44 whitespace-nowrap shadow-xl
                           bottom-0 left-full ml-2
                           xl:bottom-full xl:left-2 xl:right-2 xl:w-auto xl:ml-0 xl:mb-2"
              >
                <Link
                  href={`/users/${me.id}`}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <UserIcon />
                  <span>{t("nav.profile")}</span>
                </Link>
                {/* editor-draft-autosave PDCA — Q-2: drafts list in user menu */}
                <Link
                  href="/posts/drafts"
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <DraftIcon />
                  <span>{t("nav.draftsList")}</span>
                </Link>
                <Link
                  href="/me/settings/display"
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <SettingsIcon />
                  <span>{t("nav.displaySettings")}</span>
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
        </div>
      </aside>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} redirectTo={loginRedirect} />
    </>
  );
}
