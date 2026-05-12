"use client";

/**
 * RevenueChart — SVG line chart for patronage revenue time-series.
 *
 * Self-contained, zero external dependencies. Draws a responsive SVG
 * line chart with:
 *   - Smooth polyline path (no curves for clarity)
 *   - X-axis date labels (sparse — avoids overlap)
 *   - Y-axis value labels (in USD)
 *   - A filled area under the line for visual weight
 *   - Hover tooltip via SVG <title> on each data point circle
 *
 * granularity toggle is handled by the parent dashboard page.
 */

import React, { useMemo } from "react";
import type { RevenueDataPoint } from "@/lib/api";

interface RevenueChartProps {
  data: RevenueDataPoint[];
  loading?: boolean;
  granularity: "daily" | "monthly";
  /** i18n labels */
  labels?: {
    daily: string;
    monthly: string;
    toggleDaily: string;
    toggleMonthly: string;
    noData: string;
    chartAriaLabel?: string;
  };
  onGranularityChange?: (g: "daily" | "monthly") => void;
}

const CHART_H = 160;
const CHART_W = 600; // viewBox width — scales with container
const PAD_LEFT = 48;
const PAD_RIGHT = 12;
const PAD_TOP = 12;
const PAD_BOTTOM = 32;

function centsToDisplay(cents: number): string {
  const usd = cents / 100;
  if (usd >= 1000) return `$${(usd / 1000).toFixed(1)}k`;
  return `$${usd.toFixed(0)}`;
}

function formatXLabel(dateStr: string, granularity: "daily" | "monthly"): string {
  if (granularity === "monthly") {
    // "2026-01" → "Jan"
    const [, m] = dateStr.split("-");
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return months[(parseInt(m, 10) - 1) % 12] ?? m;
  }
  // "2026-04-15" → "15"
  return dateStr.slice(-2);
}

export function RevenueChart({
  data,
  loading = false,
  granularity,
  labels,
  onGranularityChange,
}: RevenueChartProps) {
  const plotW = CHART_W - PAD_LEFT - PAD_RIGHT;
  const plotH = CHART_H - PAD_TOP - PAD_BOTTOM;

  const { points, yMax, yTicks, xLabels } = useMemo(() => {
    if (!data.length) return { points: [], yMax: 0, yTicks: [], xLabels: [] };

    const max = Math.max(...data.map((d) => d.amount_cents), 1);
    const yMax = Math.ceil(max * 1.1);

    // Y-axis: 4 ticks
    const yTicks = [0, 0.33, 0.66, 1.0].map((f) => ({
      v: Math.round(yMax * f),
      y: PAD_TOP + plotH - Math.round(f * plotH),
    }));

    const n = data.length;
    const points = data.map((d, i) => ({
      x: PAD_LEFT + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW),
      y: PAD_TOP + plotH - (d.amount_cents / yMax) * plotH,
      d,
      label: formatXLabel(d.date, granularity),
    }));

    // X labels: show at most 8, evenly spaced
    const step = Math.max(1, Math.ceil(n / 8));
    const xLabels = points.filter((_, i) => i % step === 0 || i === n - 1);

    return { points, yMax, yTicks, xLabels };
  }, [data, granularity, plotW, plotH]);

  const pathD = useMemo(() => {
    if (!points.length) return "";
    return (
      points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")
    );
  }, [points]);

  const areaD = useMemo(() => {
    if (!points.length) return "";
    const bottom = PAD_TOP + plotH;
    const first = points[0];
    const last = points[points.length - 1];
    return `${pathD} L ${last.x.toFixed(1)} ${bottom} L ${first.x.toFixed(1)} ${bottom} Z`;
  }, [pathD, points, plotH]);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-40 bg-surface-hover rounded mb-4" />
        <div className="h-40 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  const noData = !data.length || data.every((d) => d.amount_cents === 0);

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          {granularity === "daily"
            ? (labels?.daily ?? "Revenue (Last 30 Days)")
            : (labels?.monthly ?? "Revenue (Last 12 Months)")}
        </h3>
        {onGranularityChange && (
          <div className="flex gap-1">
            <button
              onClick={() => onGranularityChange("daily")}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                granularity === "daily"
                  ? "bg-primary text-background"
                  : "text-text-muted hover:bg-surface-hover"
              }`}
            >
              {labels?.toggleDaily ?? "Daily"}
            </button>
            <button
              onClick={() => onGranularityChange("monthly")}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                granularity === "monthly"
                  ? "bg-primary text-background"
                  : "text-text-muted hover:bg-surface-hover"
              }`}
            >
              {labels?.toggleMonthly ?? "Monthly"}
            </button>
          </div>
        )}
      </div>

      {noData ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No revenue data yet."}
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${CHART_W} ${CHART_H}`}
          className="w-full"
          aria-label={labels?.chartAriaLabel ?? (granularity === "daily" ? (labels?.daily ?? "Revenue chart") : (labels?.monthly ?? "Revenue chart"))}
          role="img"
        >
          {/* Y-axis ticks */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line
                x1={PAD_LEFT}
                y1={t.y}
                x2={CHART_W - PAD_RIGHT}
                y2={t.y}
                stroke="currentColor"
                strokeOpacity={0.08}
                strokeWidth={1}
              />
              <text
                x={PAD_LEFT - 6}
                y={t.y + 4}
                textAnchor="end"
                fontSize={9}
                fill="currentColor"
                opacity={0.45}
              >
                {centsToDisplay(t.v)}
              </text>
            </g>
          ))}

          {/* Area fill */}
          <path d={areaD} fill="var(--color-primary, #6366f1)" fillOpacity={0.08} />

          {/* Line */}
          <path
            d={pathD}
            fill="none"
            stroke="var(--color-primary, #6366f1)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data point circles */}
          {points.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={3} fill="var(--color-primary, #6366f1)">
              <title>{`${p.d.date}: ${centsToDisplay(p.d.amount_cents)}`}</title>
            </circle>
          ))}

          {/* X-axis labels */}
          {xLabels.map((p, i) => (
            <text
              key={i}
              x={p.x}
              y={CHART_H - 6}
              textAnchor="middle"
              fontSize={9}
              fill="currentColor"
              opacity={0.45}
            >
              {p.label}
            </text>
          ))}
        </svg>
      )}
    </div>
  );
}
