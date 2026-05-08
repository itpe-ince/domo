"use client";

import { AnalyticsPeriod } from "@/lib/api";

interface PeriodSelectorProps {
  value: AnalyticsPeriod;
  onChange: (period: AnalyticsPeriod) => void;
}

const PERIODS: { value: AnalyticsPeriod; label: string }[] = [
  { value: "7d", label: "최근 7일" },
  { value: "30d", label: "최근 30일" },
  { value: "90d", label: "최근 90일" },
];

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <div
      role="group"
      aria-label="분석 기간 선택"
      className="inline-flex rounded-md border border-admin-border overflow-hidden"
    >
      {PERIODS.map((p) => {
        const active = p.value === value;
        return (
          <button
            key={p.value}
            type="button"
            onClick={() => onChange(p.value)}
            aria-pressed={active}
            className={[
              "px-3 py-1.5 text-[12px] font-medium transition-colors",
              active
                ? "bg-admin-accent/10 text-admin-accent border-l border-r border-admin-accent/40"
                : "text-admin-muted hover:text-admin-fg hover:bg-admin-surface-2",
            ].join(" ")}
          >
            {p.label}
          </button>
        );
      })}
    </div>
  );
}
