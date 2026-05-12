"use client";

/**
 * NewsletterStats — SVG bar chart for newsletter open/click rates.
 *
 * Shows the last N issues with stacked bars:
 *   - Open rate (primary color)
 *   - Click rate (green, overlaid within open bar)
 * Zero external dependencies; mirrors RevenueChart SVG pattern.
 */

import React, { useMemo } from "react";
import type { NewsletterIssueStats } from "@/lib/hooks/usePatronageAnalytics";

interface NewsletterStatsProps {
  data: NewsletterIssueStats[];
  loading?: boolean;
  isMock?: boolean;
  labels?: {
    title: string;
    openRate: string;
    clickRate: string;
    noData: string;
    mockBadge: string;
  };
}

const CHART_H = 160;
const CHART_W = 600;
const PAD_LEFT = 40;
const PAD_RIGHT = 12;
const PAD_TOP = 12;
const PAD_BOTTOM = 32;

const COLOR_OPEN = "#6366f1";
const COLOR_CLICK = "#22c55e";

const MOCK_DATA: NewsletterIssueStats[] = [
  { issue: "#1", sent: 800, opened: 440, clicked: 132, open_rate: 55, click_rate: 16.5 },
  { issue: "#2", sent: 820, opened: 476, clicked: 148, open_rate: 58, click_rate: 18.0 },
  { issue: "#3", sent: 810, opened: 437, clicked: 130, open_rate: 54, click_rate: 16.0 },
  { issue: "#4", sent: 850, opened: 510, clicked: 170, open_rate: 60, click_rate: 20.0 },
  { issue: "#5", sent: 870, opened: 522, clicked: 165, open_rate: 60, click_rate: 19.0 },
];

export function NewsletterStats({
  data,
  loading = false,
  isMock = false,
  labels,
}: NewsletterStatsProps) {
  const plotW = CHART_W - PAD_LEFT - PAD_RIGHT;
  const plotH = CHART_H - PAD_TOP - PAD_BOTTOM;

  const activeData = data.length > 0 ? data : isMock ? MOCK_DATA : [];

  const { bars, yTicks } = useMemo(() => {
    if (!activeData.length) return { bars: [], yTicks: [] };

    const n = activeData.length;
    const barW = Math.max(8, plotW / n - 6);
    const gap = plotW / n;

    const bars = activeData.map((d, i) => {
      const cx = PAD_LEFT + i * gap + gap / 2;
      const openH = (d.open_rate / 100) * plotH;
      const clickH = (d.click_rate / 100) * plotH;
      return {
        d,
        cx,
        barW,
        openH,
        clickH,
        openY: PAD_TOP + plotH - openH,
        clickY: PAD_TOP + plotH - clickH,
      };
    });

    const yTicks = [0, 25, 50, 75, 100].map((v) => ({
      v,
      y: PAD_TOP + plotH - (v / 100) * plotH,
    }));

    return { bars, yTicks };
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
          {labels?.title ?? "Newsletter Open & Click Rates"}
        </h3>
        <div className="flex items-center gap-4 text-xs text-text-muted">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLOR_OPEN }} />
            {labels?.openRate ?? "Open rate"}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLOR_CLICK }} />
            {labels?.clickRate ?? "Click rate"}
          </span>
          {isMock && !noData && (
            <span className="px-1.5 py-0.5 bg-surface-hover rounded text-xs text-text-muted">
              {labels?.mockBadge ?? "sample"}
            </span>
          )}
        </div>
      </div>

      {noData ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No newsletter data yet."}
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${CHART_W} ${CHART_H}`}
          className="w-full"
          role="img"
          aria-label={labels?.title ?? "Newsletter stats bar chart"}
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

          {/* Bars */}
          {bars.map((b, i) => (
            <g key={i}>
              {/* Open rate bar */}
              <rect
                x={b.cx - b.barW / 2}
                y={b.openY}
                width={b.barW}
                height={b.openH}
                fill={COLOR_OPEN}
                fillOpacity={0.7}
                rx={2}
              >
                <title>{`${b.d.issue} open: ${b.d.open_rate}%`}</title>
              </rect>
              {/* Click rate bar (overlay) */}
              <rect
                x={b.cx - b.barW / 2}
                y={b.clickY}
                width={b.barW}
                height={b.clickH}
                fill={COLOR_CLICK}
                fillOpacity={0.85}
                rx={2}
              >
                <title>{`${b.d.issue} click: ${b.d.click_rate}%`}</title>
              </rect>
              {/* X label */}
              <text
                x={b.cx}
                y={CHART_H - 6}
                textAnchor="middle"
                fontSize={9}
                fill="currentColor"
                opacity={0.45}
              >
                {b.d.issue}
              </text>
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}
