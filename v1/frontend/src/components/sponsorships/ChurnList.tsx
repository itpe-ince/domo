"use client";

/**
 * ChurnList — B-5 + D'-2 patronage-retention-ux
 *
 * Displays recently churned subscribers for the artist dashboard.
 * D'-2 booster: real cancellation reason display with color-coded badges
 * + feedback preview hover tooltip.
 *
 * Data: GET /v1/me/patronage/churn (D'-2 backend endpoint).
 * Graceful degrade: empty state if endpoint unavailable.
 */

import { useState, useEffect } from "react";
import { useI18n } from "@/i18n";
import { fetchChurnList, type ChurnItem, type CancellationReason } from "@/lib/api";

// ─── Badge color map ──────────────────────────────────────────────────────────

type BadgeVariant = "warning" | "neutral" | "error" | "info" | "muted";

const REASON_BADGE: Record<CancellationReason | "unknown", BadgeVariant> = {
  too_expensive: "warning",
  changed_mind: "neutral",
  not_satisfied: "error",
  other: "info",
  unknown: "muted",
};

const BADGE_CLASSES: Record<BadgeVariant, string> = {
  warning:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  neutral:
    "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  error:
    "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
  info:
    "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
  muted:
    "bg-surface-hover text-text-muted",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function ReasonBadge({
  reason,
}: {
  reason: CancellationReason | null | undefined;
}) {
  const { t } = useI18n();
  const key = reason ?? "unknown";
  const variant = REASON_BADGE[key as CancellationReason | "unknown"] ?? "muted";
  const label = t(
    `retention.churn.reason.${key}` as Parameters<typeof t>[0]
  );

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_CLASSES[variant]}`}
    >
      {label}
    </span>
  );
}

function FeedbackTooltip({ preview }: { preview: string }) {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        className="ml-1.5 text-xs text-text-muted underline decoration-dotted cursor-help"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        aria-label={t("patronage.churn.feedback.preview" as Parameters<typeof t>[0])}
      >
        {t("patronage.churn.feedback.preview" as Parameters<typeof t>[0])}
      </button>
      {visible && (
        <span
          role="tooltip"
          className="absolute bottom-full left-0 z-10 mb-1.5 w-56 rounded-lg border border-border bg-background px-3 py-2 text-xs text-text-secondary shadow-lg"
        >
          {preview}
        </span>
      )}
    </span>
  );
}

// ─── Avatar ───────────────────────────────────────────────────────────────────

function ChurnAvatar({ item }: { item: ChurnItem }) {
  const initial = item.username ? item.username.charAt(0).toUpperCase() : "?";
  if (item.avatar_url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={item.avatar_url}
        alt={item.username}
        className="w-8 h-8 rounded-full object-cover flex-shrink-0"
      />
    );
  }
  return (
    <div className="w-8 h-8 rounded-full bg-surface-hover flex items-center justify-center text-text-muted font-bold flex-shrink-0 text-sm">
      {initial}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

type Props = {
  limit?: number;
};

export function ChurnList({ limit = 20 }: Props) {
  const { t } = useI18n();
  const [items, setItems] = useState<ChurnItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchChurnList(limit)
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch(() => {
        // Endpoint may not be reachable — degrade gracefully
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [limit]);

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card h-14 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="card px-4 py-3 text-sm text-red-500 border border-red-200">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="card px-6 py-8 text-center text-text-muted text-sm">
        {t(
          "patronage.churn.empty.celebrated" as Parameters<typeof t>[0]
        ) || t("retention.churn.empty")}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-text-muted">
          {t("retention.churn.title")} {t("churn.last30DaysSuffix")}
        </p>
        <button
          disabled
          title="Phase 6 carry-over"
          className="text-xs text-text-muted opacity-50 cursor-not-allowed border border-border rounded-full px-3 py-1"
        >
          {t("retention.churn.sentCampaign")} {t("churn.comingSoonSuffix")}
        </button>
      </div>

      {/* Churn entries */}
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={`${item.user_id}-${item.cancelled_at}`}
            className="card px-4 py-3 flex items-start justify-between gap-4 text-sm"
          >
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <ChurnAvatar item={item} />
              <div className="min-w-0 space-y-1">
                <p className="font-medium text-text-primary truncate">
                  @{item.username}
                </p>
                <div className="flex items-center flex-wrap gap-1.5">
                  <ReasonBadge reason={item.cancellation_reason} />
                  {item.cancellation_feedback_preview && (
                    <FeedbackTooltip
                      preview={item.cancellation_feedback_preview}
                    />
                  )}
                </div>
              </div>
            </div>
            <div className="text-xs text-text-muted flex-shrink-0 pt-1">
              {new Date(item.cancelled_at).toLocaleDateString()}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
