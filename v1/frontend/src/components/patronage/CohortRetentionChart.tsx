"use client";

/**
 * CohortRetentionChart — SVG line chart for D1/D7/D30 cohort retention.
 *
 * Mirrors the RevenueChart SVG pattern (zero external deps).
 * Shows retention rate (0–100%) over cohort weeks, with three lines:
 *   D1 (day-1), D7 (day-7), D30 (day-30).
 *
 * Mock mode: when data is empty, renders sample data with a visual indicator.
 */

import React, { useMemo } from "react";
import type { CohortRetentionData } from "@/lib/hooks/usePatronageAnalytics";

interface CohortRetentionChartProps {
  data: CohortRetentionData[];
  loading?: boolean;
  isMock?: boolean;
  labels?: {
    title: string;
    d1: string;
    d7: string;
    d30: string;
    noData: string;
    mockBadge: string;
  };
}

const CHART_H = 160;
const CHART_W = 600;
const PAD_LEFT = 40;
const PAD_RIGHT = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 32;

const COLORS = {
  d1: "#6366f1",
  d7: "#22c55e",
  d30: "#f59e0b",
};

function pctY(pct: number, plotH: number): number {
  return PAD_TOP + plotH - (pct / 100) * plotH;
}

function buildPath(
  points: Array<{ x: number; y: number }>,
): string {
  if (!points.length) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
}

const MOCK_DATA: CohortRetentionData[] = [
  { week: "W1", d1: 72, d7: 48, d30: 22 },
  { week: "W2", d1: 68, d7: 44, d30: 20 },
  { week: "W3", d1: 70, d7: 46, d30: 21 },
  { week: "W4", d1: 65, d7: 41, d30: 18 },
  { week: "W5", d1: 71, d7: 47, d30: 23 },
  { week: "W6", d1: 67, d7: 43, d30: 19 },
];

export function CohortRetentionChart({
  data,
  loading = false,
  isMock = false,
  labels,
}: CohortRetentionChartProps) {
  const plotW = CHART_W - PAD_LEFT - PAD_RIGHT;
  const plotH = CHART_H - PAD_TOP - PAD_BOTTOM;

  const activeData = data.length > 0 ? data : isMock ? MOCK_DATA : [];

  const { d1Points, d7Points, d30Points, yTicks, xLabels } = useMemo(() => {
    if (!activeData.length) {
      return { d1Points: [], d7Points: [], d30Points: [], yTicks: [], xLabels: [] };
    }

    const n = activeData.length;
    const xFor = (i: number) =>
      PAD_LEFT + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);

    const d1Points = activeData.map((d, i) => ({ x: xFor(i), y: pctY(d.d1, plotH) }));
    const d7Points = activeData.map((d, i) => ({ x: xFor(i), y: pctY(d.d7, plotH) }));
    const d30Points = activeData.map((d, i) => ({ x: xFor(i), y: pctY(d.d30, plotH) }));

    const yTicks = [0, 25, 50, 75, 100].map((v) => ({
      v,
      y: pctY(v, plotH),
    }));

    const step = Math.max(1, Math.ceil(n / 8));
    const xLabels = activeData
      .map((d, i) => ({ label: d.week, x: xFor(i), show: i % step === 0 || i === n - 1 }))
      .filter((l) => l.show);

    return { d1Points, d7Points, d30Points, yTicks, xLabels };
  }, [activeData, plotW, plotH]);

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-48 bg-surface-hover rounded mb-4" />
        <div className="h-40 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  const noData = !activeData.length;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-semibold text-text-primary">
          {labels?.title ?? "Cohort Retention"}
        </h3>
        <div className="flex items-center gap-4 text-xs text-text-muted">
          {(["d1", "d7", "d30"] as const).map((k) => (
            <span key={k} className="flex items-center gap-1">
              <span
                className="inline-block w-3 h-0.5 rounded"
                style={{ backgroundColor: COLORS[k] }}
              />
              {labels?.[k] ?? k.toUpperCase()}
            </span>
          ))}
          {isMock && activeData.length > 0 && (
            <span className="px-1.5 py-0.5 bg-surface-hover rounded text-xs text-text-muted">
              {labels?.mockBadge ?? "sample"}
            </span>
          )}
        </div>
      </div>

      {noData ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No retention data yet."}
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${CHART_W} ${CHART_H}`}
          className="w-full"
          role="img"
          aria-label={labels?.title ?? "Cohort retention chart"}
        >
          {/* Y-axis grid + labels */}
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
                x={PAD_LEFT - 5}
                y={t.y + 4}
                textAnchor="end"
                fontSize={9}
                fill="currentColor"
                opacity={0.45}
              >
                {t.v}%
              </text>
            </g>
          ))}

          {/* D1 line */}
          <path
            d={buildPath(d1Points)}
            fill="none"
            stroke={COLORS.d1}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* D7 line */}
          <path
            d={buildPath(d7Points)}
            fill="none"
            stroke={COLORS.d7}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* D30 line */}
          <path
            d={buildPath(d30Points)}
            fill="none"
            stroke={COLORS.d30}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data dots — D1 */}
          {d1Points.map((p, i) => (
            <circle key={`d1-${i}`} cx={p.x} cy={p.y} r={2.5} fill={COLORS.d1}>
              <title>{`${activeData[i]?.week} D1: ${activeData[i]?.d1}%`}</title>
            </circle>
          ))}
          {d7Points.map((p, i) => (
            <circle key={`d7-${i}`} cx={p.x} cy={p.y} r={2.5} fill={COLORS.d7}>
              <title>{`${activeData[i]?.week} D7: ${activeData[i]?.d7}%`}</title>
            </circle>
          ))}
          {d30Points.map((p, i) => (
            <circle key={`d30-${i}`} cx={p.x} cy={p.y} r={2.5} fill={COLORS.d30}>
              <title>{`${activeData[i]?.week} D30: ${activeData[i]?.d30}%`}</title>
            </circle>
          ))}

          {/* X-axis labels */}
          {xLabels.map((l, i) => (
            <text
              key={i}
              x={l.x}
              y={CHART_H - 6}
              textAnchor="middle"
              fontSize={9}
              fill="currentColor"
              opacity={0.45}
            >
              {l.label}
            </text>
          ))}
        </svg>
      )}
    </div>
  );
}
