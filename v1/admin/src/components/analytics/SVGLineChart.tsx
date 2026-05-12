"use client";

/**
 * SVGLineChart — Phase 12 B-2.
 *
 * 순수 SVG 라인/바 차트. recharts/chart.js 의존성 없음.
 * viewBox="0 0 400 {height}", 접근성: role="img" + aria-label.
 */

export interface ChartDataPoint {
  date: string;
  value: number;
}

export interface ChartSeries {
  label: string;
  color: string;
  data: ChartDataPoint[];
}

interface SVGLineChartProps {
  series: ChartSeries[];
  yUnit?: string;
  height?: number;
  showLegend?: boolean;
  ariaLabel?: string;
}

const WIDTH = 400;
const PADDING = { top: 12, right: 16, bottom: 28, left: 40 };

function formatDateLabel(date: string): string {
  // "2026-04-08" → "04/08"
  const parts = date.split("-");
  if (parts.length === 3) return `${parts[1]}/${parts[2]}`;
  return date;
}

function formatValue(v: number, unit: string): string {
  if (unit === "%") return `${(v * 100).toFixed(1)}%`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
  return String(v);
}

export function SVGLineChart({
  series,
  yUnit = "",
  height = 160,
  showLegend = true,
  ariaLabel,
}: SVGLineChartProps) {
  const chartW = WIDTH - PADDING.left - PADDING.right;
  const chartH = height - PADDING.top - PADDING.bottom;

  // 모든 시리즈에서 x축 레이블 + y 범위 계산
  const allDates = Array.from(
    new Set(series.flatMap((s) => s.data.map((d) => d.date)))
  ).sort();

  const allValues = series.flatMap((s) => s.data.map((d) => d.value));
  const minVal = allValues.length ? Math.min(...allValues) : 0;
  const maxVal = allValues.length ? Math.max(...allValues) : 1;
  const valRange = maxVal - minVal || 1;

  // x축 최대 7개 레이블
  const xLabelStep = allDates.length > 7 ? Math.ceil(allDates.length / 7) : 1;
  const xLabels = allDates.filter((_, i) => i % xLabelStep === 0);

  // 좌표 변환
  function toX(date: string): number {
    const idx = allDates.indexOf(date);
    if (idx < 0 || allDates.length <= 1) return PADDING.left;
    return PADDING.left + (idx / (allDates.length - 1)) * chartW;
  }

  function toY(value: number): number {
    return PADDING.top + chartH - ((value - minVal) / valRange) * chartH;
  }

  // y축 4개 눈금
  const yTicks = [0, 1, 2, 3].map((i) => minVal + (valRange * i) / 3);

  const label = ariaLabel ?? series.map((s) => s.label).join(", ") + " 차트";

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        role="img"
        aria-label={label}
        className="w-full"
        style={{ height }}
      >
        {/* y축 눈금선 */}
        {yTicks.map((v, i) => {
          const y = toY(v);
          return (
            <g key={i}>
              <line
                x1={PADDING.left}
                y1={y}
                x2={PADDING.left + chartW}
                y2={y}
                stroke="#334155"
                strokeWidth={0.5}
                strokeDasharray="3,3"
              />
              <text
                x={PADDING.left - 4}
                y={y + 3}
                textAnchor="end"
                fontSize={9}
                fill="#94a3b8"
              >
                {formatValue(v, yUnit)}
              </text>
            </g>
          );
        })}

        {/* x축 레이블 */}
        {xLabels.map((date) => (
          <text
            key={date}
            x={toX(date)}
            y={PADDING.top + chartH + 16}
            textAnchor="middle"
            fontSize={9}
            fill="#94a3b8"
          >
            {formatDateLabel(date)}
          </text>
        ))}

        {/* 각 시리즈 라인 */}
        {series.map((s) => {
          if (s.data.length === 0) return null;

          const pts = s.data
            .filter((d) => allDates.includes(d.date))
            .sort((a, b) => a.date.localeCompare(b.date));

          if (pts.length === 0) return null;

          const polyline = pts.map((d) => `${toX(d.date)},${toY(d.value)}`).join(" ");

          return (
            <g key={s.label}>
              <polyline
                points={polyline}
                fill="none"
                stroke={s.color}
                strokeWidth={1.8}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* 데이터 점 */}
              {pts.map((d, i) => (
                <circle
                  key={i}
                  cx={toX(d.date)}
                  cy={toY(d.value)}
                  r={2.5}
                  fill={s.color}
                >
                  <title>{`${s.label}: ${formatValue(d.value, yUnit)} (${d.date})`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>

      {/* 범례 */}
      {showLegend && series.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 px-1">
          {series.map((s) => (
            <span key={s.label} className="flex items-center gap-1.5 text-[11px] text-admin-muted">
              <span
                className="inline-block h-2 w-4 rounded-sm"
                style={{ backgroundColor: s.color }}
              />
              {s.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── SVGBarChart (가로 바 — AIFeaturesUsageCard 전용) ─────────────────────────

export interface BarItem {
  label: string;
  value: number;
  color: string;
}

interface SVGBarChartProps {
  items: BarItem[];
  maxValue?: number;
  height?: number;
  ariaLabel?: string;
}

export function SVGBarChart({
  items,
  maxValue,
  height,
  ariaLabel,
}: SVGBarChartProps) {
  const max = maxValue ?? Math.max(...items.map((b) => b.value), 1);
  const rowH = 28;
  const barH = 14;
  const labelW = 64;
  const totalH = height ?? items.length * rowH + 8;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${totalH}`}
      role="img"
      aria-label={ariaLabel ?? "바 차트"}
      className="w-full"
      style={{ height: totalH }}
    >
      {items.map((item, i) => {
        const y = i * rowH + (rowH - barH) / 2;
        const barW = ((item.value / max) * (WIDTH - labelW - 60));
        const pct = max > 0 ? `${(item.value / max * 100).toFixed(1)}%` : "0%";

        return (
          <g key={item.label}>
            <text
              x={0}
              y={y + barH / 2 + 4}
              fontSize={10}
              fill="#94a3b8"
              textAnchor="start"
            >
              {item.label}
            </text>
            <rect
              x={labelW}
              y={y}
              width={Math.max(barW, 2)}
              height={barH}
              rx={3}
              fill={item.color}
              opacity={0.85}
            >
              <title>{`${item.label}: ${item.value.toLocaleString()} (${pct})`}</title>
            </rect>
            <text
              x={labelW + Math.max(barW, 2) + 6}
              y={y + barH / 2 + 4}
              fontSize={10}
              fill="#64748b"
            >
              {pct}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
