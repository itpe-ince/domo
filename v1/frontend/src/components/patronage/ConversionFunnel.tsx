"use client";

/**
 * ConversionFunnel — SVG funnel chart for sponsorship conversion.
 *
 * 4 steps: post_click → sponsor_start → sponsor_success → active_30d
 * Self-contained SVG, zero external deps.
 */

import React, { useMemo } from "react";
import type { ConversionFunnelData } from "@/lib/hooks/usePatronageAnalytics";

interface ConversionFunnelProps {
  data: ConversionFunnelData | null;
  loading?: boolean;
  isMock?: boolean;
  labels?: {
    title: string;
    postClick: string;
    sponsorStart: string;
    sponsorSuccess: string;
    active30d: string;
    noData: string;
    mockBadge: string;
    conversionRate: string;
  };
}

const MOCK_DATA: ConversionFunnelData = {
  post_click: 2400,
  sponsor_start: 480,
  sponsor_success: 320,
  active_30d: 260,
};

const FUNNEL_W = 600;
const FUNNEL_H = 180;
const BAR_H = 28;
const BAR_GAP = 12;
const LABEL_W = 130;
const MAX_BAR_W = FUNNEL_W - LABEL_W - 80; // reserve space for count labels

const COLORS = ["#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"];
const DROP_COLOR = "#94a3b8";

type FunnelStep = {
  key: keyof ConversionFunnelData;
  labelKey: keyof NonNullable<ConversionFunnelProps["labels"]>;
};

const STEPS: FunnelStep[] = [
  { key: "post_click", labelKey: "postClick" },
  { key: "sponsor_start", labelKey: "sponsorStart" },
  { key: "sponsor_success", labelKey: "sponsorSuccess" },
  { key: "active_30d", labelKey: "active30d" },
];

export function ConversionFunnel({
  data,
  loading = false,
  isMock = false,
  labels,
}: ConversionFunnelProps) {
  const activeData = data ?? (isMock ? MOCK_DATA : null);

  const rows = useMemo(() => {
    if (!activeData) return [];
    const top = Math.max(activeData.post_click, 1);
    return STEPS.map((step, i) => {
      const v = activeData[step.key];
      const prev = i === 0 ? v : activeData[STEPS[i - 1].key];
      const barW = (v / top) * MAX_BAR_W;
      const dropPct = prev > 0 ? Math.round(((prev - v) / prev) * 100) : 0;
      const y = i * (BAR_H + BAR_GAP);
      return { step, v, barW, dropPct, y, isFirst: i === 0, color: COLORS[i] };
    });
  }, [activeData]);

  const overallRate =
    activeData && activeData.post_click > 0
      ? ((activeData.active_30d / activeData.post_click) * 100).toFixed(1)
      : null;

  const svgH = STEPS.length * (BAR_H + BAR_GAP) - BAR_GAP + 4;

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-48 bg-surface-hover rounded mb-4" />
        <div className="h-40 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  const noData = !activeData || activeData.post_click === 0;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-semibold text-text-primary">
          {labels?.title ?? "Sponsorship Conversion Funnel"}
        </h3>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          {overallRate !== null && (
            <span>
              {labels?.conversionRate ?? "Overall"}: <strong className="text-text-primary">{overallRate}%</strong>
            </span>
          )}
          {isMock && !noData && (
            <span className="px-1.5 py-0.5 bg-surface-hover rounded text-xs text-text-muted">
              {labels?.mockBadge ?? "sample"}
            </span>
          )}
        </div>
      </div>

      {noData ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No funnel data yet."}
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${FUNNEL_W} ${svgH}`}
          className="w-full"
          role="img"
          aria-label={labels?.title ?? "Conversion funnel chart"}
        >
          {rows.map((row, i) => (
            <g key={i}>
              {/* Step label */}
              <text
                x={0}
                y={row.y + BAR_H / 2 + 4}
                fontSize={10}
                fill="currentColor"
                opacity={0.7}
              >
                {labels?.[row.step.labelKey as keyof typeof labels] ?? row.step.key}
              </text>

              {/* Bar */}
              <rect
                x={LABEL_W}
                y={row.y}
                width={row.barW}
                height={BAR_H}
                fill={row.color}
                rx={3}
              >
                <title>{`${row.v.toLocaleString()}`}</title>
              </rect>

              {/* Count */}
              <text
                x={LABEL_W + row.barW + 6}
                y={row.y + BAR_H / 2 + 4}
                fontSize={10}
                fill="currentColor"
                opacity={0.75}
              >
                {row.v.toLocaleString()}
              </text>

              {/* Drop indicator between steps */}
              {!row.isFirst && row.dropPct > 0 && (
                <text
                  x={LABEL_W + row.barW + 6}
                  y={row.y - BAR_GAP / 2 + 3}
                  fontSize={9}
                  fill={DROP_COLOR}
                >
                  -{row.dropPct}%
                </text>
              )}
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}
