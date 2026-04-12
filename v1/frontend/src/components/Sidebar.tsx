"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { logout } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { useUnreadCount } from "@/lib/useUnreadCount";
import { CreateMenu } from "./CreateMenu";
import { LoginModal } from "./LoginModal";
import {
  BellIcon,
  BluebirdIcon,
  CheckCircleIcon,
  DashboardIcon,
  ExploreIcon,
  FlagIcon,
  HomeIcon,
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
  const unread = useUnreadCount();

  async function handleLogout() {
    await logout();
  }

  const primary: NavItem[] = [
    { href: "/", label: "홈", Icon: HomeIcon },
    {
      href: "/following",
      label: "팔로잉",
      Icon: UsersIcon,
      needsAuth: true,
    },
    { href: "/explore", label: "탐색", Icon: ExploreIcon },
    {
      href: "/notifications",
      label: "알림",
      Icon: BellIcon,
      needsAuth: true,
      badge: unread,
    },
    {
      href: me ? `/users/${me.id}` : "/",
      label: "프로필",
      Icon: UserIcon,
      needsAuth: true,
    },
  ];

  const secondary: NavItem[] = [
    {
      href: "/subscriptions",
      label: "정기 후원",
      Icon: BluebirdIcon,
      needsAuth: true,
    },
    { href: "/orders", label: "주문", Icon: ReceiptIcon, needsAuth: true },
    {
      href: "/warnings",
      label: "내 경고",
      Icon: ShieldAlertIcon,
      needsAuth: true,
    },
    { href: "/me/account", label: "설정", Icon: SettingsIcon, needsAuth: true },
  ];

  const admin: NavItem[] = [
    {
      href: "/admin/dashboard",
      label: "대시보드",
      Icon: DashboardIcon,
      adminOnly: true,
    },
    {
      href: "/admin/applications",
      label: "작가 승인",
      Icon: CheckCircleIcon,
      adminOnly: true,
    },
    {
      href: "/admin/moderation",
      label: "모더레이션",
      Icon: FlagIcon,
      adminOnly: true,
    },
    {
      href: "/admin/settings",
      label: "시스템 설정",
      Icon: SettingsIcon,
      adminOnly: true,
    },
  ];

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
        className={`group flex items-center gap-4 rounded-full px-3 py-3 transition-colors ${
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
            className="flex items-center gap-2 px-3 py-3 mb-2 hover:bg-surface-hover rounded-full transition-colors"
          >
            <span className="text-primary text-3xl font-bold leading-none">
              D
            </span>
            <span className="hidden xl:inline text-2xl font-bold text-primary">
              Domo
            </span>
          </Link>

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

          {/* Admin */}
          {me?.role === "admin" && (
            <>
              <div className="border-t border-border my-2" />
              <div className="hidden xl:block px-3 py-1 text-xs uppercase tracking-wide text-text-muted">
                Admin
              </div>
              <nav className="flex flex-col gap-0.5">
                {admin.map(renderItem)}
              </nav>
            </>
          )}

          {/* Create menu button */}
          {me && (
            <div className="mt-3">
              <CreateMenu
                align="top"
                side="left"
                trigger={({ toggle, triggerProps }) => (
                  <button
                    onClick={toggle}
                    className="w-full bg-primary text-background hover:bg-primary-hover rounded-full font-bold transition-colors flex items-center justify-center py-3"
                    aria-label="작성"
                    {...triggerProps}
                  >
                    <span className="xl:hidden">
                      <PlusIcon />
                    </span>
                    <span className="hidden xl:inline">+ 작성</span>
                  </button>
                )}
              />
            </div>
          )}

          {/* Sign in button */}
          {!me && (
            <button
              onClick={() => setLoginOpen(true)}
              className="mt-3 bg-primary text-background hover:bg-primary-hover rounded-full font-bold transition-colors py-3 xl:px-6"
            >
              <span className="xl:hidden">↵</span>
              <span className="hidden xl:inline">로그인</span>
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
              <div className="absolute bottom-full mb-2 left-0 right-0 xl:left-2 xl:right-2 card p-2 z-40">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover text-sm text-text-primary"
                >
                  <LogoutIcon size={18} />
                  <span>로그아웃</span>
                </button>
              </div>
            </details>
          </div>
        )}
      </aside>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
