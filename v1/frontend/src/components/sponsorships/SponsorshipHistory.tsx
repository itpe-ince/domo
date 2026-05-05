"use client";

/**
 * SponsorshipHistory — B-3 supporter-dashboard
 *
 * Chronological list of one-time sponsorships (newest first).
 * Supports "show more" pagination (client-side windowing — no new backend
 * endpoint needed; the existing GET /v1/sponsorships/mine returns all records).
 */

import { useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import type { SponsorshipView } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  succeeded: "text-green-600 bg-green-50",
  completed: "text-green-600 bg-green-50",
  failed: "text-red-500 bg-red-50",
  refunded: "text-amber-600 bg-amber-50",
  pending: "text-text-muted bg-surface",
};

const PAGE_SIZE = 10;

type Props = {
  sponsorships: SponsorshipView[];
  loading: boolean;
};

export function SponsorshipHistory({ sponsorships, loading }: Props) {
  const { t } = useI18n();
  const [page, setPage] = useState(1);

  // Newest first
  const sorted = [...sponsorships].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  const visible = sorted.slice(0, page * PAGE_SIZE);
  const hasMore = visible.length < sorted.length;

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card p-4 animate-pulse h-16" />
        ))}
      </div>
    );
  }

  if (sponsorships.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="text-text-muted text-sm">
          {t("patronage.supporter.history.empty")}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {visible.map((s) => {
        const date = new Date(s.created_at).toLocaleDateString();
        const amount = `$${parseFloat(s.amount).toFixed(2)}`;
        // Determine a tier label from bluebird_count (platform default mapping)
        const tierLabel =
          s.bluebird_count >= 10
            ? "Sponsor 30d"
            : s.bluebird_count >= 3
            ? "Subscriber 7d"
            : "Follower 1d";

        return (
          <div key={s.id} className="card px-4 py-3 flex items-center gap-4">
            {/* Artist link */}
            <Link
              href={`/users/${s.artist_id}`}
              className="flex-shrink-0 w-9 h-9 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold text-sm hover:opacity-80 transition-opacity"
              aria-label={`Artist ${s.artist_id.slice(0, 6)}`}
            >
              {s.artist_id.charAt(0).toUpperCase()}
            </Link>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  href={`/users/${s.artist_id}`}
                  className="text-sm font-medium text-text-primary hover:underline truncate"
                >
                  @{s.artist_id.slice(0, 8)}
                </Link>
                {/* Status */}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[s.status] ?? "text-text-muted bg-surface"}`}
                >
                  {t(`patronage.supporter.history.status.${s.status}`) === `patronage.supporter.history.status.${s.status}`
                    ? s.status
                    : t(`patronage.supporter.history.status.${s.status}`)}
                </span>
              </div>
              <div className="flex gap-3 text-xs text-text-muted mt-0.5">
                <span>{date}</span>
                {s.status === "succeeded" || s.status === "completed" ? (
                  <span className="text-text-secondary">{tierLabel}</span>
                ) : null}
              </div>
            </div>

            {/* Amount */}
            <div className="flex-shrink-0 text-right">
              <span className="font-semibold text-text-primary">{amount}</span>
              <div className="text-xs text-text-muted">{s.currency.toUpperCase()}</div>
            </div>
          </div>
        );
      })}

      {hasMore && (
        <div className="text-center pt-2">
          <button
            onClick={() => setPage((p) => p + 1)}
            className="text-sm text-primary hover:underline"
          >
            {t("patronage.supporter.history.showMore")}
          </button>
        </div>
      )}
    </div>
  );
}
