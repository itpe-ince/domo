"use client";

/**
 * TierDistribution — stacked bar chart showing supporter tier breakdown.
 *
 * Renders a horizontal stacked bar with three colored segments
 * (subscriber / sponsor / follower) and a legend below.
 * SVG-based — no external chart library required.
 */

import React from "react";
import type { TierDistribution as TierData } from "@/lib/api";

interface TierDistributionProps {
  data: TierData;
  loading?: boolean;
  labels?: {
    subscriber: string;
    sponsor: string;
    follower: string;
    title: string;
  };
}

const TIER_COLORS = {
  subscriber: "#6366f1", // indigo
  sponsor: "#f59e0b",    // amber
  follower: "#10b981",   // emerald
};

export function TierDistribution({ data, loading = false, labels }: TierDistributionProps) {
  const total = data.subscriber + data.sponsor + data.follower;

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-32 bg-surface-hover rounded mb-4" />
        <div className="h-5 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  const tiers: { key: keyof TierData; color: string; label: string; value: number }[] = [
    {
      key: "subscriber",
      color: TIER_COLORS.subscriber,
      label: labels?.subscriber ?? "Subscribers",
      value: data.subscriber,
    },
    {
      key: "sponsor",
      color: TIER_COLORS.sponsor,
      label: labels?.sponsor ?? "Sponsors",
      value: data.sponsor,
    },
    {
      key: "follower",
      color: TIER_COLORS.follower,
      label: labels?.follower ?? "Followers",
      value: data.follower,
    },
  ];

  return (
    <div className="card p-5 flex flex-col gap-4">
      <h3 className="text-sm text-text-muted">{labels?.title ?? "Tier Distribution"}</h3>

      {total === 0 ? (
        <div className="h-5 w-full rounded-full bg-surface-hover" />
      ) : (
        <div className="flex h-5 w-full rounded-full overflow-hidden gap-px">
          {tiers
            .filter((t) => t.value > 0)
            .map((t) => (
              <div
                key={t.key}
                style={{
                  width: `${(t.value / total) * 100}%`,
                  backgroundColor: t.color,
                }}
                title={`${t.label}: ${t.value}`}
              />
            ))}
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        {tiers.map((t) => (
          <div key={t.key} className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: t.color }}
            />
            <span>{t.label}</span>
            <span className="text-text-primary font-semibold tabular-nums">{t.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
