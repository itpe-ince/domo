"use client";

/**
 * SupportersTable — paginated list of artist supporters.
 *
 * Columns: avatar + username | tier badge | since | lifetime | status
 * Features:
 *   - Filter radio: active / churned / all
 *   - Cursor pagination "Load more" button
 *   - Username links to /users/[id]
 */

import Link from "next/link";
import React from "react";
import type { SupporterItem } from "@/lib/api";
import type { SupporterFilter } from "@/lib/hooks/usePatronageDashboard";

interface SupportersTableProps {
  supporters: SupporterItem[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  filter: SupporterFilter;
  onFilterChange: (f: SupporterFilter) => void;
  onLoadMore: () => void;
  labels?: {
    title: string;
    filterActive: string;
    filterChurned: string;
    filterAll: string;
    colUsername: string;
    colTier: string;
    colSince: string;
    colLifetime: string;
    colStatus: string;
    empty: string;
    loadMore: string;
    loading: string;
  };
}

function centsToDisplay(cents: number): string {
  const usd = cents / 100;
  if (usd >= 1000) return `$${(usd / 1000).toFixed(1)}k`;
  return `$${usd.toFixed(0)}`;
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

const TIER_COLORS: Record<string, string> = {
  subscriber: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  sponsor: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  follower: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
};

const STATUS_COLORS: Record<string, string> = {
  active: "text-green-500",
  cancelled: "text-text-muted line-through",
  past_due: "text-red-500",
};

const FILTERS: { key: SupporterFilter; labelKey: keyof NonNullable<SupportersTableProps["labels"]> }[] = [
  { key: "all", labelKey: "filterAll" },
  { key: "active", labelKey: "filterActive" },
  { key: "churned", labelKey: "filterChurned" },
];

export function SupportersTable({
  supporters,
  loading,
  loadingMore,
  hasMore,
  filter,
  onFilterChange,
  onLoadMore,
  labels,
}: SupportersTableProps) {
  const L = {
    title: labels?.title ?? "Supporters",
    filterActive: labels?.filterActive ?? "Active",
    filterChurned: labels?.filterChurned ?? "Churned",
    filterAll: labels?.filterAll ?? "All",
    colUsername: labels?.colUsername ?? "User",
    colTier: labels?.colTier ?? "Tier",
    colSince: labels?.colSince ?? "Since",
    colLifetime: labels?.colLifetime ?? "Lifetime",
    colStatus: labels?.colStatus ?? "Status",
    empty: labels?.empty ?? "No supporters yet.",
    loadMore: labels?.loadMore ?? "Load more",
    loading: labels?.loading ?? "Loading...",
  };

  return (
    <div className="card flex flex-col gap-0 overflow-hidden">
      {/* Header + filter */}
      <div className="flex items-center justify-between p-5 border-b border-border">
        <h3 className="text-sm font-semibold text-text-primary">{L.title}</h3>
        <div className="flex gap-1">
          {FILTERS.map(({ key, labelKey }) => (
            <button
              key={key}
              onClick={() => onFilterChange(key)}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                filter === key
                  ? "bg-primary text-background"
                  : "text-text-muted hover:bg-surface-hover"
              }`}
            >
              {L[labelKey]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-8 text-center text-text-muted text-sm animate-pulse">{L.loading}</div>
      ) : supporters.length === 0 ? (
        <div className="p-8 text-center text-text-muted text-sm">{L.empty}</div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-muted text-xs border-b border-border">
                  <th scope="col" className="px-5 py-3 font-medium">{L.colUsername}</th>
                  <th scope="col" className="px-3 py-3 font-medium">{L.colTier}</th>
                  <th scope="col" className="px-3 py-3 font-medium">{L.colSince}</th>
                  <th scope="col" className="px-3 py-3 font-medium">{L.colLifetime}</th>
                  <th scope="col" className="px-3 py-3 font-medium">{L.colStatus}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {supporters.map((s) => (
                  <tr key={s.user_id} className="hover:bg-surface-hover/30 transition-colors">
                    <td className="px-5 py-3">
                      <Link
                        href={`/users/${s.user_id}`}
                        className="flex items-center gap-3 group"
                      >
                        <div className="w-8 h-8 rounded-full bg-surface-hover flex items-center justify-center flex-shrink-0 text-xs font-bold text-text-muted">
                          {s.avatar_url ? (
                            <img
                              src={s.avatar_url}
                              alt=""
                              className="w-full h-full rounded-full object-cover"
                            />
                          ) : (
                            s.username.charAt(0).toUpperCase()
                          )}
                        </div>
                        <span className="text-text-primary group-hover:text-primary transition-colors">
                          @{s.username}
                        </span>
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          TIER_COLORS[s.tier] ?? "bg-surface-hover text-text-secondary"
                        }`}
                      >
                        {s.tier}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-text-secondary tabular-nums">
                      {formatDate(s.since)}
                    </td>
                    <td className="px-3 py-3 text-text-primary font-semibold tabular-nums">
                      {centsToDisplay(s.lifetime_amount_cents)}
                    </td>
                    <td className="px-3 py-3">
                      {s.subscription_status ? (
                        <span
                          className={`text-xs ${
                            STATUS_COLORS[s.subscription_status] ?? "text-text-secondary"
                          }`}
                        >
                          {s.subscription_status}
                        </span>
                      ) : (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile list */}
          <ul className="sm:hidden divide-y divide-border">
            {supporters.map((s) => (
              <li key={s.user_id} className="px-5 py-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center flex-shrink-0 text-sm font-bold text-text-muted">
                  {s.avatar_url ? (
                    <img src={s.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
                  ) : (
                    s.username.charAt(0).toUpperCase()
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <Link href={`/users/${s.user_id}`} className="font-medium text-text-primary hover:text-primary">
                    @{s.username}
                  </Link>
                  <div className="flex items-center gap-2 mt-0.5 text-xs text-text-muted">
                    <span
                      className={`px-1.5 py-0.5 rounded-full ${
                        TIER_COLORS[s.tier] ?? "bg-surface-hover text-text-secondary"
                      }`}
                    >
                      {s.tier}
                    </span>
                    <span>{formatDate(s.since)}</span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="font-semibold text-text-primary tabular-nums">
                    {centsToDisplay(s.lifetime_amount_cents)}
                  </p>
                  {s.subscription_status && (
                    <p className={`text-xs ${STATUS_COLORS[s.subscription_status] ?? ""}`}>
                      {s.subscription_status}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {/* Load more */}
          {hasMore && (
            <div className="p-4 border-t border-border text-center">
              <button
                onClick={onLoadMore}
                disabled={loadingMore}
                className="text-sm text-primary hover:underline disabled:opacity-50 disabled:no-underline"
              >
                {loadingMore ? L.loading : L.loadMore}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
