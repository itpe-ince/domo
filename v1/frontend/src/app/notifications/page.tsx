"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationView,
  tokenStore,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  return `${Math.floor(hr / 24)}일 전`;
}

export default function NotificationsPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [items, setItems] = useState<NotificationView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      setLoading(false);
      return;
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchNotifications(false, 50));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleClick(n: NotificationView) {
    if (!n.is_read) {
      try {
        await markNotificationRead(n.id);
        setItems((prev) =>
          prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))
        );
      } catch {
        /* ignore */
      }
    }
    if (n.link) window.location.href = n.link;
  }

  async function handleReadAll() {
    try {
      await markAllNotificationsRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      /* ignore */
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">{t("notifications.title")}</h1>
        {me && items.length > 0 && (
          <button
            onClick={handleReadAll}
            className="text-xs text-text-muted hover:text-primary"
          >
            {t("notifications.markAllRead")}
          </button>
        )}
      </div>

      {!me && !meLoading ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          <p>{t("notifications.loginRequired")}</p>
          <p className="text-xs mt-2">{t("notifications.loginHint")}</p>
        </div>
      ) : loading ? (
        <div className="p-4 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="card p-4 animate-pulse"
            >
              <div className="h-4 w-2/3 bg-surface-hover rounded mb-2" />
              <div className="h-3 w-1/2 bg-surface-hover rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="card border-danger p-4 m-4 text-danger text-sm">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          {t("notifications.empty")}
        </div>
      ) : (
        <ul>
          {items.map((n) => (
            <li
              key={n.id}
              className={`border-b border-border ${
                !n.is_read ? "bg-surface-hover/30" : ""
              }`}
            >
              <button
                onClick={() => handleClick(n)}
                className="w-full text-left px-4 py-4 hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-start gap-3">
                  {!n.is_read && (
                    <span className="mt-2 w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-text-primary">
                      {n.title ?? n.type}
                    </div>
                    {n.body && (
                      <div className="text-sm text-text-secondary mt-1">
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
    </main>
  );
}
