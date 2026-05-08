"use client";

import { CandidateReasoning } from "@/lib/api";

interface ScoreBreakdownProps {
  reasoning: CandidateReasoning;
}

type ScoreRowDef = {
  label: string;
  key: keyof Pick<CandidateReasoning, "engagement" | "rank" | "diversity" | "new_artist_bonus">;
  weight: number;
  color: string;
};

const SCORE_ROWS: ScoreRowDef[] = [
  { label: "참여도", key: "engagement", weight: 0.30, color: "bg-blue-500" },
  { label: "랭킹", key: "rank", weight: 0.30, color: "bg-purple-500" },
  { label: "다양성", key: "diversity", weight: 0.20, color: "bg-teal-500" },
  { label: "신진 보너스", key: "new_artist_bonus", weight: 0.20, color: "bg-amber-500" },
];

export function ScoreBreakdown({ reasoning }: ScoreBreakdownProps) {
  return (
    <div className="space-y-2">
      {SCORE_ROWS.map((row) => {
        const rawValue = reasoning[row.key] ?? 0;
        const pct = Math.round(rawValue * 100);
        return (
          <div key={row.key}>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[11px] text-admin-muted">
                {row.label}
                <span className="ml-1 text-admin-fg-soft opacity-60">
                  (w={row.weight.toFixed(2)})
                </span>
              </span>
              <span className="text-[11px] font-medium text-admin-fg">{pct}%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-admin-surface-2 overflow-hidden">
              <div
                className={`h-full rounded-full ${row.color} transition-all duration-300`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
