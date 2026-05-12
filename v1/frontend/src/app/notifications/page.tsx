"use client";

import { useEffect, useState } from "react";
import {
  fetchNotificationsByFilter,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationFilter,
  NotificationView,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { formatRelativeTime as timeAgo } from "@/lib/formatRelativeTime";
import {
  BellIcon,
  GavelIcon,
  BluebirdIcon,
  HeartIcon,
  MessageCircleIcon,
  UserPlusIcon,
  InfoIcon,
  SendIcon,
} from "@/components/icons";

// ─── Filter tab config ────────────────────────────────────────────────────

type FilterTab = {
  key: NotificationFilter;
  labelKey: string;
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
};

const FILTER_TABS: FilterTab[] = [
  { key: "all", labelKey: "notifications.center.filter.all", Icon: BellIcon },
  { key: "unread", labelKey: "notifications.center.filter.unread", Icon: BellIcon },
  { key: "auction", labelKey: "notifications.center.filter.auction", Icon: GavelIcon },
  { key: "sponsorship", labelKey: "notifications.center.filter.sponsorship", Icon: BluebirdIcon },
  { key: "engagement", labelKey: "notifications.center.filter.engagement", Icon: HeartIcon },
  { key: "system", labelKey: "notifications.center.filter.system", Icon: InfoIcon },
];

// ─── Per-type icon helper ─────────────────────────────────────────────────

function NotifIcon({ type }: { type: string }) {
  const cls = "w-5 h-5 flex-shrink-0 mt-0.5";
  if (type.startsWith("auction")) return <GavelIcon className={cls} />;
  if (type === "like") return <HeartIcon className={cls} />;
  if (type === "comment" || type === "reply" || type === "mention")
    return <MessageCircleIcon className={cls} />;
  if (type === "follow") return <UserPlusIcon className={cls} />;
  if (type === "sponsor_received" || type === "sponsor_milestone" || type.startsWith("subscription"))
    return <BluebirdIcon className={cls} />;
  // B'-2 dm-messaging — dm_received notification
  if (type === "dm_received") return <SendIcon className={cls} />;
  return <InfoIcon className={cls} />;
}

// ─── Toast notification ───────────────────────────────────────────────────

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-text-primary text-background text-sm px-4 py-2.5 rounded-full shadow-lg pointer-events-none">
      {message}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [activeFilter, setActiveFilter] = useState<NotificationFilter>("all");
  const [items, setItems] = useState<NotificationView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      setLoading(false);
      return;
    }
    void load(activeFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading, activeFilter]);

  async function load(filter: NotificationFilter) {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchNotificationsByFilter(filter, 50));
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
      const result = await markAllNotificationsRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      const count = result?.updated ?? 0;
      if (count > 0) {
        setToast(t("notifications.center.markedAsRead", { count }));
      }
    } catch {
      /* ignore */
    }
  }

  function handleFilterChange(filter: NotificationFilter) {
    setActiveFilter(filter);
  }

  const unreadCount = items.filter((n) => !n.is_read).length;
  const emptyKey =
    activeFilter === "unread"
      ? "notifications.center.empty.unread"
      : "notifications.center.empty.all";

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">{t("notifications.center.title")}</h1>
        {me && unreadCount > 0 && (
          <button
            onClick={handleReadAll}
            className="text-xs text-text-muted hover:text-primary transition-colors"
          >
            {t("notifications.center.markAllRead")}
          </button>
        )}
      </div>

      {/* Filter tabs */}
      {me && !meLoading && (
        <div
          className="flex gap-0 border-b border-border overflow-x-auto scrollbar-none"
          role="tablist"
          aria-label={t("notifications.center.title")}
        >
          {FILTER_TABS.map((tab) => {
            const isActive = activeFilter === tab.key;
            return (
              <button
                key={tab.key}
                role="tab"
                aria-selected={isActive}
                onClick={() => handleFilterChange(tab.key)}
                className={`flex-shrink-0 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-text-muted hover:text-text-primary"
                }`}
              >
                {t(tab.labelKey)}
              </button>
            );
          })}
        </div>
      )}

      {/* Content */}
      {!me && !meLoading ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          <p>{t("notifications.loginRequired")}</p>
          <p className="text-xs mt-2">{t("notifications.loginHint")}</p>
        </div>
      ) : loading ? (
        <div className="p-4 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-surface-hover flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="h-4 w-2/3 bg-surface-hover rounded mb-2" />
                  <div className="h-3 w-1/2 bg-surface-hover rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="card border-danger p-4 m-4 text-danger text-sm">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          <BellIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">{t(emptyKey)}</p>
        </div>
      ) : (
        <ul aria-label={t("notifications.center.title")} aria-live="polite">
          {items.map((n) => (
            <li
              key={n.id}
              className={`border-b border-border ${
                !n.is_read ? "bg-surface-hover/30" : ""
              }`}
            >
              <button
                onClick={() => handleClick(n)}
                aria-label={`${n.title ?? n.type}${!n.is_read ? " (unread)" : ""}`}
                className="w-full text-left px-4 py-4 hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-start gap-3">
                  {/* Unread dot */}
                  {!n.is_read ? (
                    <span className="mt-2 w-2 h-2 rounded-full bg-primary flex-shrink-0" aria-hidden="true" />
                  ) : (
                    <span className="mt-2 w-2 h-2 flex-shrink-0" aria-hidden="true" />
                  )}
                  {/* Type icon */}
                  <span className={`text-text-muted ${!n.is_read ? "text-primary" : ""}`}>
                    <NotifIcon type={n.type} />
                  </span>
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className={`font-semibold text-sm ${!n.is_read ? "text-text-primary" : "text-text-secondary"}`}>
                      {n.title ?? n.type}
                    </div>
                    {n.body && (
                      <div className="text-sm text-text-secondary mt-1 line-clamp-2">
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

      {/* Toast */}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </main>
  );
}
