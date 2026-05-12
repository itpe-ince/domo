"use client";

/**
 * DmEngagementCard — B'-2 booster metric card.
 *
 * Shows:
 *   - First-message rate: % of new supporters who sent the artist a DM
 *   - Avg response time: median artist reply time (minutes)
 *   - Total DM threads initiated
 */

import React from "react";
import type { DmEngagementData } from "@/lib/hooks/usePatronageAnalytics";

interface DmEngagementCardProps {
  data: DmEngagementData | null;
  loading?: boolean;
  isMock?: boolean;
  labels?: {
    title: string;
    firstMessageRate: string;
    firstMessageHint: string;
    avgResponseTime: string;
    avgResponseUnit: string;
    totalThreads: string;
    noData: string;
    mockBadge: string;
  };
}

const MOCK_DATA: DmEngagementData = {
  first_message_rate: 34.5,
  avg_response_minutes: 42,
  total_threads: 88,
};

function formatMinutes(min: number): string {
  if (min < 60) return `${Math.round(min)}m`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function DmEngagementCard({
  data,
  loading = false,
  isMock = false,
  labels,
}: DmEngagementCardProps) {
  const activeData = data ?? (isMock ? MOCK_DATA : null);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-48 bg-surface-hover rounded mb-3" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((k) => (
            <div key={k} className="h-16 bg-surface-hover rounded" />
          ))}
        </div>
      </div>
    );
  }

  const noData = !activeData;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-text-primary">
          {labels?.title ?? "DM Engagement"}
        </h3>
        {isMock && !noData && (
          <span className="px-1.5 py-0.5 bg-surface-hover rounded text-xs text-text-muted">
            {labels?.mockBadge ?? "sample"}
          </span>
        )}
      </div>

      {noData ? (
        <div className="h-20 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No DM engagement data yet."}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {/* First-message rate */}
          <div className="flex flex-col gap-1 p-3 bg-surface rounded-lg">
            <p className="text-xs text-text-muted leading-tight">
              {labels?.firstMessageRate ?? "First-message rate"}
            </p>
            <p className="text-xl font-bold text-text-primary tabular-nums">
              {activeData.first_message_rate.toFixed(1)}%
            </p>
            {labels?.firstMessageHint && (
              <p className="text-[10px] text-text-muted leading-tight">
                {labels.firstMessageHint}
              </p>
            )}
          </div>

          {/* Avg response time */}
          <div className="flex flex-col gap-1 p-3 bg-surface rounded-lg">
            <p className="text-xs text-text-muted leading-tight">
              {labels?.avgResponseTime ?? "Avg response time"}
            </p>
            <p className="text-xl font-bold text-text-primary tabular-nums">
              {formatMinutes(activeData.avg_response_minutes)}
            </p>
            {labels?.avgResponseUnit && (
              <p className="text-[10px] text-text-muted leading-tight">
                {labels.avgResponseUnit}
              </p>
            )}
          </div>

          {/* Total threads */}
          <div className="flex flex-col gap-1 p-3 bg-surface rounded-lg">
            <p className="text-xs text-text-muted leading-tight">
              {labels?.totalThreads ?? "Total threads"}
            </p>
            <p className="text-xl font-bold text-text-primary tabular-nums">
              {activeData.total_threads.toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
