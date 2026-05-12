"use client";

/**
 * CouponRedemptionStats — Donut chart showing winback coupon lifecycle.
 *
 * Tracks: issued → applied → cancel_reverted vs expired
 * SVG self-drawn (zero external deps), mirrors RevenueChart pattern.
 */

import React, { useMemo } from "react";
import type { CouponRedemptionData } from "@/lib/hooks/usePatronageAnalytics";

interface CouponRedemptionStatsProps {
  data: CouponRedemptionData | null;
  loading?: boolean;
  isMock?: boolean;
  labels?: {
    title: string;
    issued: string;
    applied: string;
    cancelReverted: string;
    expired: string;
    redemptionRate: string;
    noData: string;
    mockBadge: string;
  };
}

const MOCK_DATA: CouponRedemptionData = {
  issued: 120,
  applied: 72,
  cancel_reverted: 38,
  expired: 48,
};

const SEGMENTS: Array<{
  key: keyof CouponRedemptionData;
  labelKey: "applied" | "cancelReverted" | "expired";
  color: string;
}> = [
  { key: "applied", labelKey: "applied", color: "#6366f1" },
  { key: "cancel_reverted", labelKey: "cancelReverted", color: "#22c55e" },
  { key: "expired", labelKey: "expired", color: "#e5e7eb" },
];

const CX = 80;
const CY = 80;
const R_OUTER = 60;
const R_INNER = 36;

function polarToXY(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function donutSegment(
  cx: number,
  cy: number,
  rOuter: number,
  rInner: number,
  startDeg: number,
  endDeg: number,
): string {
  const large = endDeg - startDeg > 180 ? 1 : 0;
  const o1 = polarToXY(cx, cy, rOuter, startDeg);
  const o2 = polarToXY(cx, cy, rOuter, endDeg);
  const i1 = polarToXY(cx, cy, rInner, endDeg);
  const i2 = polarToXY(cx, cy, rInner, startDeg);
  return [
    `M ${o1.x.toFixed(2)} ${o1.y.toFixed(2)}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${o2.x.toFixed(2)} ${o2.y.toFixed(2)}`,
    `L ${i1.x.toFixed(2)} ${i1.y.toFixed(2)}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${i2.x.toFixed(2)} ${i2.y.toFixed(2)}`,
    "Z",
  ].join(" ");
}

export function CouponRedemptionStats({
  data,
  loading = false,
  isMock = false,
  labels,
}: CouponRedemptionStatsProps) {
  const activeData = data ?? (isMock ? MOCK_DATA : null);

  const segments = useMemo(() => {
    if (!activeData || activeData.issued === 0) return [];
    const total = activeData.issued;
    const vals: Array<{ key: keyof CouponRedemptionData; v: number; color: string }> = SEGMENTS.map((s) => ({
      key: s.key,
      v: activeData[s.key],
      color: s.color,
    }));
    let cursor = 0;
    return vals.map((seg) => {
      const pct = seg.v / total;
      const startDeg = cursor * 360;
      cursor += pct;
      const endDeg = cursor * 360;
      return { ...seg, startDeg, endDeg, pct };
    });
  }, [activeData]);

  const redemptionRate =
    activeData && activeData.issued > 0
      ? Math.round((activeData.applied / activeData.issued) * 100)
      : null;

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-48 bg-surface-hover rounded mb-4" />
        <div className="h-40 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  const noData = !activeData || activeData.issued === 0;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-text-primary">
          {labels?.title ?? "Winback Coupon Redemption"}
        </h3>
        {isMock && !noData && (
          <span className="px-1.5 py-0.5 bg-surface-hover rounded text-xs text-text-muted">
            {labels?.mockBadge ?? "sample"}
          </span>
        )}
      </div>

      {noData ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          {labels?.noData ?? "No coupon data yet."}
        </div>
      ) : (
        <div className="flex items-center gap-6 flex-wrap">
          {/* Donut */}
          <svg viewBox="0 0 160 160" className="w-32 h-32 flex-shrink-0" role="img" aria-label={labels?.title ?? "Coupon redemption donut chart"}>
            {segments.length === 0 ? (
              <circle cx={CX} cy={CY} r={R_OUTER} fill="#e5e7eb" />
            ) : (
              segments.map((seg, i) => (
                <path key={i} d={donutSegment(CX, CY, R_OUTER, R_INNER, seg.startDeg, seg.endDeg)} fill={seg.color}>
                  <title>{`${seg.key}: ${seg.v} (${Math.round(seg.pct * 100)}%)`}</title>
                </path>
              ))
            )}
            {/* Center label */}
            <text x={CX} y={CY - 4} textAnchor="middle" fontSize={18} fontWeight={700} fill="currentColor">
              {redemptionRate}%
            </text>
            <text x={CX} y={CY + 14} textAnchor="middle" fontSize={8} fill="currentColor" opacity={0.5}>
              {labels?.redemptionRate ?? "Redemption"}
            </text>
          </svg>

          {/* Legend */}
          <div className="flex flex-col gap-2 text-xs text-text-muted">
            <div className="text-text-secondary font-medium">
              {(labels?.issued ?? "Issued")}: <span className="font-semibold text-text-primary">{activeData?.issued}</span>
            </div>
            {SEGMENTS.map((s) => (
              <div key={s.key} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
                <span>
                  {labels?.[s.labelKey] ?? s.key}:{" "}
                  <span className="font-medium text-text-secondary">{activeData?.[s.key]}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
