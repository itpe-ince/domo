"use client";

import { useState } from "react";
import { Experiment, ExperimentStatus } from "@/lib/api";
import { useExperimentResults } from "@/lib/hooks/useExperiments";
import { PostHogEmbed } from "./PostHogEmbed";

interface ExperimentCardProps {
  experiment: Experiment;
  onStatusChange: (name: string, status: "paused" | "completed") => Promise<void>;
}

function StatusBadge({ status }: { status: ExperimentStatus }) {
  const map: Record<ExperimentStatus, { label: string; cls: string }> = {
    draft: { label: "초안", cls: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
    running: { label: "진행 중", cls: "bg-green-500/10 text-green-600 border-green-500/20" },
    paused: { label: "일시정지", cls: "bg-orange-500/10 text-orange-600 border-orange-500/20" },
    completed: { label: "완료", cls: "bg-admin-muted/20 text-admin-muted border-admin-border" },
  };
  const { label, cls } = map[status] ?? map.draft;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cls}`}
    >
      {label}
    </span>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function calcDaysRunning(startedAt: string | null, endedAt: string | null): number | null {
  if (!startedAt) return null;
  const start = new Date(startedAt);
  const end = endedAt ? new Date(endedAt) : new Date();
  return Math.max(0, Math.floor((end.getTime() - start.getTime()) / 86_400_000));
}

export function ExperimentCard({ experiment, onStatusChange }: ExperimentCardProps) {
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [hypothesisExpanded, setHypothesisExpanded] = useState(false);
  const [confirmComplete, setConfirmComplete] = useState(false);
  const [actionPending, setActionPending] = useState(false);

  const { results, isLoading: resultsLoading } = useExperimentResults(
    experiment.name,
    showAnalysis
  );

  const daysRunning = calcDaysRunning(experiment.started_at, experiment.ended_at);

  const distributionEntries = Object.entries(experiment.variant_distribution);
  const assignmentEntries = Object.entries(experiment.assignment_counts);

  const isPauseable = experiment.status === "running";
  const isCompletable = experiment.status === "running" || experiment.status === "paused";

  async function handlePause() {
    setActionPending(true);
    try {
      await onStatusChange(experiment.name, "paused");
    } finally {
      setActionPending(false);
    }
  }

  async function handleComplete() {
    if (!confirmComplete) {
      setConfirmComplete(true);
      return;
    }
    setActionPending(true);
    setConfirmComplete(false);
    try {
      await onStatusChange(experiment.name, "completed");
    } finally {
      setActionPending(false);
    }
  }

  return (
    <div className="bg-admin-surface rounded-xl border border-admin-border overflow-hidden">
      {/* 카드 헤더 */}
      <div className="px-5 py-4 flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-admin-fg font-mono break-all">
              {experiment.name}
            </h3>
            <StatusBadge status={experiment.status} />
            {daysRunning !== null && (
              <span className="text-[11px] text-admin-muted border border-admin-border rounded-full px-2 py-0.5">
                {daysRunning}일 운영 중
              </span>
            )}
          </div>

          {/* 가설 */}
          {experiment.hypothesis && (
            <div className="mt-2">
              <span className="text-[11px] font-semibold text-admin-fg-soft uppercase tracking-wide">
                가설
              </span>
              <p
                className={`mt-0.5 text-sm text-admin-fg ${
                  !hypothesisExpanded ? "line-clamp-2" : ""
                }`}
              >
                {experiment.hypothesis}
              </p>
              {experiment.hypothesis.length > 80 && (
                <button
                  onClick={() => setHypothesisExpanded(!hypothesisExpanded)}
                  className="text-[11px] text-admin-accent mt-0.5"
                >
                  {hypothesisExpanded ? "접기" : "더보기"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 메타 정보 그리드 */}
      <div className="px-5 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* 분배 비율 */}
        <div>
          <div className="text-[11px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1">
            분배 비율
          </div>
          <div className="flex flex-col gap-0.5">
            {distributionEntries.map(([variant, ratio]) => (
              <span key={variant} className="text-sm text-admin-fg">
                {variant}: {Math.round(ratio * 100)}%
              </span>
            ))}
          </div>
        </div>

        {/* 측정 지표 */}
        <div>
          <div className="text-[11px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1">
            측정 지표
          </div>
          <span className="text-sm text-admin-fg font-mono">
            {experiment.target_metric ?? "—"}
          </span>
        </div>

        {/* 기간 */}
        <div>
          <div className="text-[11px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1">
            기간
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-sm text-admin-fg">
              시작: {formatDate(experiment.started_at)}
            </span>
            <span className="text-sm text-admin-fg">
              종료: {formatDate(experiment.ended_at)}
            </span>
          </div>
        </div>

        {/* 참여자 수 */}
        <div>
          <div className="text-[11px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1">
            참여자 수
          </div>
          {assignmentEntries.length > 0 ? (
            <div className="flex flex-col gap-0.5">
              {assignmentEntries.map(([variant, count]) => (
                <span key={variant} className="text-sm text-admin-fg">
                  {variant}: {count.toLocaleString()}명
                </span>
              ))}
            </div>
          ) : (
            <span className="text-sm text-admin-muted">배정 없음</span>
          )}
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="px-5 pb-4 flex items-center gap-2 flex-wrap border-t border-admin-border pt-3">
        {/* 결과 분석 토글 */}
        <button
          onClick={() => setShowAnalysis(!showAnalysis)}
          className="text-[12px] font-medium text-admin-accent border border-admin-accent/30 rounded-md px-3 py-1.5 hover:bg-admin-accent/5 transition-colors"
          aria-label={showAnalysis ? "결과 분석 닫기" : "결과 분석 열기"}
        >
          {showAnalysis ? "결과 분석 닫기" : "결과 분석 열기"}
        </button>

        {/* 일시정지 — PATCH 미구현: disabled + 안내 */}
        <div className="relative group">
          <button
            disabled={!isPauseable || actionPending}
            onClick={handlePause}
            className="text-[12px] font-medium text-orange-600 border border-orange-500/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-orange-500/5"
            aria-disabled={!isPauseable}
            title="Phase 12 후속 백엔드 작업 필요 (PATCH endpoint 미구현)"
          >
            일시정지
          </button>
          {isPauseable && (
            <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-10 w-60 text-[11px] text-admin-fg bg-admin-surface border border-admin-border rounded-md px-2.5 py-2 shadow-lg pointer-events-none">
              Phase 12 후속 백엔드 작업 필요 (PATCH /admin/experiments/&#123;name&#125; 미구현)
            </div>
          )}
        </div>

        {/* 실험 종료 — PATCH 미구현: disabled + 안내 */}
        {confirmComplete ? (
          <div className="flex items-center gap-1.5">
            <span className="text-[12px] text-admin-fg">종료하시겠습니까?</span>
            <button
              onClick={handleComplete}
              disabled={actionPending}
              className="text-[12px] font-medium text-admin-danger border border-admin-danger/30 rounded-md px-2.5 py-1 hover:bg-admin-danger/5 disabled:opacity-40"
            >
              확인
            </button>
            <button
              onClick={() => setConfirmComplete(false)}
              className="text-[12px] text-admin-muted border border-admin-border rounded-md px-2.5 py-1 hover:bg-admin-surface-2"
            >
              취소
            </button>
          </div>
        ) : (
          <div className="relative group">
            <button
              disabled={!isCompletable || actionPending}
              onClick={handleComplete}
              className="text-[12px] font-medium text-admin-danger border border-admin-danger/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-admin-danger/5"
              aria-disabled={!isCompletable}
              title="Phase 12 후속 백엔드 작업 필요 (PATCH endpoint 미구현)"
            >
              실험 종료
            </button>
            {isCompletable && (
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-10 w-60 text-[11px] text-admin-fg bg-admin-surface border border-admin-border rounded-md px-2.5 py-2 shadow-lg pointer-events-none">
                Phase 12 후속 백엔드 작업 필요 (PATCH /admin/experiments/&#123;name&#125; 미구현)
              </div>
            )}
          </div>
        )}
      </div>

      {/* PostHog 분석 패널 슬라이드 다운 */}
      {showAnalysis && (
        <div className="px-5 pb-5 border-t border-admin-border pt-1">
          {resultsLoading ? (
            <div className="mt-3 h-12 flex items-center text-sm text-admin-muted">
              결과를 불러오는 중...
            </div>
          ) : (
            <PostHogEmbed
              experimentName={experiment.name}
              posthogInsightsUrl={results?.posthog_insights_url ?? ""}
            />
          )}
          {results?.note && (
            <p className="mt-2 text-[11px] text-admin-muted">{results.note}</p>
          )}
        </div>
      )}
    </div>
  );
}
