"use client";

import { Experiment, ExperimentStatus } from "@/lib/api";
import { ExperimentCard } from "./ExperimentCard";

interface ExperimentsListProps {
  experiments: Experiment[];
  onCreateClick: () => void;
  onStatusChange: (name: string, status: "paused" | "completed") => Promise<void>;
}

export function ExperimentsList({
  experiments,
  onCreateClick,
  onStatusChange,
}: ExperimentsListProps) {
  if (experiments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-admin-muted text-sm mb-4">생성된 실험이 없습니다.</div>
        <button
          onClick={onCreateClick}
          className="text-sm font-medium bg-admin-accent text-white rounded-lg px-5 py-2 hover:opacity-90 transition-opacity"
        >
          + 첫 번째 실험 생성하기
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {experiments.map((exp) => (
        <ExperimentCard
          key={exp.id}
          experiment={exp}
          onStatusChange={onStatusChange}
        />
      ))}
    </div>
  );
}

// ── 필터 탭 컴포넌트 ──────────────────────────────────────────────────────────

const FILTER_TABS: { value: ExperimentStatus | "all"; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "running", label: "진행 중" },
  { value: "paused", label: "일시정지" },
  { value: "completed", label: "완료" },
  { value: "draft", label: "초안" },
];

interface FilterTabsProps {
  current: ExperimentStatus | "all";
  onChange: (v: ExperimentStatus | "all") => void;
  counts: Record<string, number>;
}

export function FilterTabs({ current, onChange, counts }: FilterTabsProps) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {FILTER_TABS.map((tab) => {
        const count = tab.value === "all"
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : (counts[tab.value] ?? 0);
        const isActive = current === tab.value;
        return (
          <button
            key={tab.value}
            onClick={() => onChange(tab.value)}
            className={`px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors ${
              isActive
                ? "bg-admin-accent text-white"
                : "text-admin-muted border border-admin-border hover:border-admin-accent hover:text-admin-accent"
            }`}
          >
            {tab.label}
            {count > 0 && (
              <span
                className={`ml-1.5 text-[10px] font-bold ${
                  isActive ? "opacity-80" : "opacity-60"
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
