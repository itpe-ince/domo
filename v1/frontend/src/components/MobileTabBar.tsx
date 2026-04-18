"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useUnreadCount } from "@/lib/useUnreadCount";
import { LoginModal } from "./LoginModal";
import {
  BellIcon,
  ExploreIcon,
  HomeIcon,
  LayersIcon,
  PlusIcon,
  UserIcon,
  UsersIcon,
} from "./icons";

export function MobileTabBar() {
  const { me } = useMe();
  const { t } = useI18n();
  const pathname = usePathname();
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginRedirect, setLoginRedirect] = useState<string | undefined>();
  const unread = useUnreadCount();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  const iconCls = (active: boolean) =>
    active ? "text-primary" : "text-text-secondary";

  return (
    <>
      {/* Bottom tab bar — mirrors sidebar primary nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-background border-t border-border flex items-center justify-around h-14">
        <Link
          href="/"
          className={`flex-1 flex items-center justify-center py-2 ${iconCls(
            isActive("/")
          )}`}
          aria-label={t("nav.home")}
        >
          <HomeIcon />
        </Link>

        <Link
          href="/feed"
          className={`flex-1 flex items-center justify-center py-2 ${iconCls(
            isActive("/feed")
          )}`}
          aria-label={t("nav.feed")}
        >
          <LayersIcon />
        </Link>

        {me && (
          <Link
            href="/following"
            className={`flex-1 flex items-center justify-center py-2 ${iconCls(
              isActive("/following")
            )}`}
            aria-label={t("nav.following")}
          >
            <UsersIcon />
          </Link>
        )}

        <Link
          href="/search"
          className={`flex-1 flex items-center justify-center py-2 ${iconCls(
            isActive("/search")
          )}`}
          aria-label={t("common.search")}
        >
          <ExploreIcon />
        </Link>

        {me ? (
          <>
            <Link
              href="/notifications"
              className={`flex-1 flex items-center justify-center py-2 ${iconCls(
                isActive("/notifications")
              )}`}
              aria-label={
                unread > 0 ? `${t("nav.notifications")} (${unread})` : t("nav.notifications")
              }
            >
              <span className="relative">
                <BellIcon />
                {unread > 0 && (
                  <span className="absolute -top-1 -right-2 bg-primary text-background text-[10px] rounded-full px-1.5 min-w-[18px] h-[18px] flex items-center justify-center font-semibold">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </span>
            </Link>
            <Link
              href={`/users/${me.id}`}
              className={`flex-1 flex items-center justify-center py-2 ${iconCls(
                pathname.startsWith("/users/")
              )}`}
              aria-label={t("nav.profile")}
            >
              <UserIcon />
            </Link>
          </>
        ) : (
          <button
            onClick={() => setLoginOpen(true)}
            className="flex-1 flex items-center justify-center py-2 text-text-secondary hover:text-primary"
            aria-label={t("common.login")}
          >
            <UserIcon />
          </button>
        )}
      </nav>

      {/* Floating create button — always visible */}
      <div className="md:hidden fixed right-4 bottom-20 z-30">
        {me ? (
          <Link
            href="/posts/new"
            className="bg-primary text-background rounded-full p-4 shadow-lg hover:bg-primary-hover transition-colors flex items-center justify-center"
            aria-label={t("nav.register")}
          >
            <PlusIcon />
          </Link>
        ) : (
          <button
            onClick={() => {
              setLoginRedirect("/posts/new");
              setLoginOpen(true);
            }}
            className="bg-primary text-background rounded-full p-4 shadow-lg hover:bg-primary-hover transition-colors"
            aria-label={t("nav.register")}
          >
            <PlusIcon />
          </button>
        )}
      </div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} redirectTo={loginRedirect} />
    </>
  );
}
