"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationView,
  tokenStore,
} from "@/lib/api";

const POLL_MS = 30000;

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const days = Math.floor(hr / 24);
  return `${days}일 전`;
}

export function NotificationBell() {
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationView[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!tokenStore.get()) return;
    void refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  async function refresh() {
    if (!tokenStore.get()) return;
    try {
      const r = await fetchUnreadCount();
      setCount(r.count);
    } catch {
      // ignore
    }
  }

  async function handleOpen() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    setLoading(true);
    try {
      const list = await fetchNotifications(false, 15);
      setNotifications(list);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkAll() {
    try {
      await markAllNotificationsRead();
      setCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  }

  async function handleClickItem(n: NotificationView) {
    if (!n.is_read) {
      try {
        await markNotificationRead(n.id);
        setCount((c) => Math.max(0, c - 1));
        setNotifications((prev) =>
          prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))
        );
      } catch {
        // ignore
      }
    }
    if (n.link) {
      setOpen(false);
      window.location.href = n.link;
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={handleOpen}
        className="btn-ghost text-sm relative"
        aria-label="알림"
      >
        🔔
        {count > 0 && (
          <span className="absolute -top-1 -right-1 bg-primary text-background text-xs rounded-full px-1.5 min-w-[18px] h-[18px] flex items-center justify-center font-semibold">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-[70vh] card overflow-hidden z-40 flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 className="font-semibold text-sm">알림</h3>
            <button
              onClick={handleMarkAll}
              className="text-text-muted text-xs hover:text-primary"
            >
              모두 읽음
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-6 text-center text-text-muted text-sm">
                로딩 중...
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-6 text-center text-text-muted text-sm">
                알림이 없습니다.
              </div>
            ) : (
              <ul>
                {notifications.map((n) => (
                  <li key={n.id}>
                    <button
                      onClick={() => handleClickItem(n)}
                      className={`w-full text-left px-4 py-3 border-b border-border hover:bg-surface-hover transition-colors ${
                        !n.is_read ? "bg-surface-hover/40" : ""
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {!n.is_read && (
                          <span className="mt-1.5 w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-text-primary truncate">
                            {n.title ?? n.type}
                          </div>
                          {n.body && (
                            <div className="text-xs text-text-secondary mt-0.5 line-clamp-2">
                              {n.body}
                            </div>
                          )}
                          <div className="text-xs text-text-muted mt-1">
                            {timeAgo(n.created_at)}
                          </div>
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
