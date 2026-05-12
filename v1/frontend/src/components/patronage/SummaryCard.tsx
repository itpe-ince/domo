"use client";

/**
 * SummaryCard — single stat card for the patronage dashboard.
 *
 * Renders a label, primary value, and optional delta badge.
 * Used in the 4-card responsive grid at the top of the dashboard.
 */

import React from "react";

interface SummaryCardProps {
  label: string;
  value: string | number;
  /** Optional change vs previous period, e.g. "+12%" or "-3" */
  delta?: string;
  /** positive | negative | neutral — controls delta badge color */
  deltaDir?: "positive" | "negative" | "neutral";
  icon?: React.ReactNode;
  loading?: boolean;
}

export function SummaryCard({
  label,
  value,
  delta,
  deltaDir = "neutral",
  icon,
  loading = false,
}: SummaryCardProps) {
  const deltaColor =
    deltaDir === "positive"
      ? "text-green-500"
      : deltaDir === "negative"
      ? "text-red-500"
      : "text-text-muted";

  if (loading) {
    return (
      <div className="card p-5 flex flex-col gap-3 animate-pulse">
        <div className="h-4 w-24 bg-surface-hover rounded" />
        <div className="h-8 w-16 bg-surface-hover rounded" />
      </div>
    );
  }

  return (
    <div className="card p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-text-muted text-sm">
        {icon && <span className="opacity-70">{icon}</span>}
        <span>{label}</span>
      </div>
      <p className="text-3xl font-bold text-text-primary tabular-nums">{value}</p>
      {delta && (
        <p className={`text-xs font-medium ${deltaColor}`}>{delta}</p>
      )}
    </div>
  );
}
