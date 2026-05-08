"use client";

import { useState } from "react";
import { Experiment, ExperimentStatus } from "@/lib/api";
import { useExperimentResults } from "@/lib/hooks/useExperiments";
import { PostHogEmbed } from "./PostHogEmbed";
import {
  CompleteConfirmModal,
  PauseConfirmModal,
} from "./ExperimentStatusModals";

interface ExperimentCardProps {
  experiment: Experiment;
  /** 상태 변경 콜백 — ExperimentsShell에서 주입 (patch + refetch) */
  onStatusChange: (
    name: string,
    status: "paused" | "completed" | "running"
  ) => Promise<void>;
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
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Confirm 모달 상태
  const [showPauseConfirm, setShowPauseConfirm] = useState(false);
  const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);

  const { results, isLoading: resultsLoading } = useExperimentResults(
    experiment.name,
    showAnalysis
  );

  const daysRunning = calcDaysRunning(experiment.started_at, experiment.ended_at);

  const distributionEntries = Object.entries(experiment.variant_distribution);
  const assignmentEntries = Object.entries(experiment.assignment_counts);

  async function handleAction(status: "paused" | "completed" | "running") {
    setActionPending(true);
    setActionError(null);
    try {
      await onStatusChange(experiment.name, status);
    } catch (err) {
      if (err instanceof Error) {
        setActionError(err.message);
      } else {
        setActionError("작업 처리 중 오류가 발생했습니다.");
      }
    } finally {
      setActionPending(false);
    }
  }

  const isCompleted = experiment.status === "completed";

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

      {/* 에러 메시지 */}
      {actionError && (
        <div className="mx-5 mb-3 px-3 py-2 bg-admin-danger/10 border border-admin-danger/30 rounded-lg text-[12px] text-admin-danger">
          {actionError}
        </div>
      )}

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

        {/* running 상태 — 일시정지 / 종료 */}
        {experiment.status === "running" && (
          <>
            <button
              disabled={actionPending}
              onClick={() => setShowPauseConfirm(true)}
              className="text-[12px] font-medium text-orange-600 border border-orange-500/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-orange-500/5"
            >
              일시정지
            </button>
            <button
              disabled={actionPending}
              onClick={() => setShowCompleteConfirm(true)}
              className="text-[12px] font-medium text-admin-danger border border-admin-danger/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-admin-danger/5"
            >
              실험 종료
            </button>
          </>
        )}

        {/* paused 상태 — 재개 / 종료 */}
        {experiment.status === "paused" && (
          <>
            <button
              disabled={actionPending}
              onClick={() => handleAction("running")}
              className="text-[12px] font-medium text-green-600 border border-green-500/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-green-500/5"
            >
              {actionPending ? "처리 중..." : "재개"}
            </button>
            <button
              disabled={actionPending}
              onClick={() => setShowCompleteConfirm(true)}
              className="text-[12px] font-medium text-admin-danger border border-admin-danger/30 rounded-md px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-admin-danger/5"
            >
              실험 종료
            </button>
          </>
        )}

        {/* completed 상태 — 영구 보존 안내 */}
        {isCompleted && (
          <span className="text-[12px] text-admin-muted italic">
            완료된 실험 (영구 보존)
          </span>
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

      {/* Confirm 모달 */}
      <PauseConfirmModal
        open={showPauseConfirm}
        experimentName={experiment.name}
        onConfirm={() => {
          setShowPauseConfirm(false);
          void handleAction("paused");
        }}
        onCancel={() => setShowPauseConfirm(false)}
      />
      <CompleteConfirmModal
        open={showCompleteConfirm}
        experimentName={experiment.name}
        onConfirm={() => {
          setShowCompleteConfirm(false);
          void handleAction("completed");
        }}
        onCancel={() => setShowCompleteConfirm(false)}
      />
    </div>
  );
}
