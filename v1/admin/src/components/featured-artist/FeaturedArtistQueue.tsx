"use client";

import { useEffect, useState } from "react";
import { useFeaturedArtistQueue } from "@/lib/hooks/useFeaturedArtistQueue";
import { CandidateCard } from "./CandidateCard";

function getRecentWeeks(count = 8): string[] {
  const weeks: string[] = [];
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0=일, 1=월 ... 6=토
  const daysToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(today);
  monday.setDate(today.getDate() + daysToMonday);
  monday.setHours(0, 0, 0, 0);

  for (let i = 0; i < count; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() - i * 7);
    weeks.push(d.toISOString().slice(0, 10));
  }
  return weeks;
}

function formatWeekLabel(weekStart: string): string {
  return `Week of ${weekStart}`;
}

export function FeaturedArtistQueue() {
  const weeks = getRecentWeeks(8);
  const [selectedWeek, setSelectedWeek] = useState<string>(weeks[0]);

  const { data, loading, error, load, approve, publish, reject, actionLoading } =
    useFeaturedArtistQueue(selectedWeek);

  useEffect(() => {
    void load();
  }, [load]);

  function handleWeekChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedWeek(e.target.value);
  }

  return (
    <div>
      {/* 헤더 컨트롤 */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <select
          value={selectedWeek}
          onChange={handleWeekChange}
          className="bg-admin-surface border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg focus:outline-none focus:border-admin-accent"
        >
          {weeks.map((w) => (
            <option key={w} value={w}>
              {formatWeekLabel(w)}
            </option>
          ))}
        </select>

        {/* 통계 위젯 — 4주 후 표시 (MVP placeholder) */}
        <div className="text-[12px] text-admin-muted border border-admin-border rounded-lg px-3 py-1.5">
          정확도 N/A — 운영 4주 후 표시
        </div>

        {/* 새로고침 */}
        <button
          onClick={() => void load()}
          disabled={loading}
          className="ml-auto text-[12px] text-admin-muted hover:text-admin-fg border border-admin-border rounded-lg px-3 py-1.5 transition-colors disabled:opacity-40"
        >
          {loading ? "로딩 중..." : "새로고침"}
        </button>
      </div>

      {/* 에러 */}
      {error && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* 로딩 스켈레톤 */}
      {loading && !data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-admin-surface border border-admin-border rounded-xl p-5 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-admin-surface-2" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 w-24 bg-admin-surface-2 rounded" />
                  <div className="h-2.5 w-16 bg-admin-surface-2 rounded" />
                </div>
              </div>
              <div className="h-6 w-16 bg-admin-surface-2 rounded mb-3" />
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j} className="h-3 bg-admin-surface-2 rounded" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && data && data.candidates.length === 0 && (
        <div className="text-center py-16 text-admin-muted">
          <div className="text-4xl mb-3">🎨</div>
          <div className="text-sm font-medium text-admin-fg mb-1">이번 주 후보가 없습니다.</div>
          <div className="text-xs">다음 주 월요일 09:00 UTC에 자동 선정됩니다.</div>
        </div>
      )}

      {/* 카드 그리드 */}
      {data && data.candidates.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              onApprove={approve}
              onPublish={publish}
              onReject={reject}
              actionLoading={actionLoading}
            />
          ))}
        </div>
      )}
    </div>
  );
}
