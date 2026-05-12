"use client";

import { useEffect, useRef, useState } from "react";
import { CreateExperimentPayload, ExperimentStatus } from "@/lib/api";
import { useCreateExperiment } from "@/lib/hooks/useExperiments";

const TARGET_METRIC_OPTIONS = [
  { value: "feed_ctr", label: "feed_ctr" },
  { value: "session_duration", label: "session_duration" },
  { value: "sponsor_cvr", label: "sponsor_cvr" },
];

interface CreateExperimentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateExperimentModal({
  isOpen,
  onClose,
  onCreated,
}: CreateExperimentModalProps) {
  const [name, setName] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [v1Ratio, setV1Ratio] = useState(50);
  const [targetMetric, setTargetMetric] = useState("feed_ctr");
  const [customMetric, setCustomMetric] = useState("");
  const [status, setStatus] = useState<ExperimentStatus>("running");
  const [autoComplete, setAutoComplete] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  const nameInputRef = useRef<HTMLInputElement>(null);

  const { submit, isSubmitting, submitError, setSubmitError } =
    useCreateExperiment(() => {
      onCreated();
      handleClose();
    });

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => nameInputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // ESC 키 닫기
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  function handleClose() {
    setName("");
    setHypothesis("");
    setV1Ratio(50);
    setTargetMetric("feed_ctr");
    setCustomMetric("");
    setStatus("running");
    setAutoComplete(false);
    setNameError(null);
    setSubmitError(null);
    onClose();
  }

  function validateName(value: string): string | null {
    if (!value) return "실험 이름은 필수입니다.";
    if (!/^[a-z0-9_]+$/.test(value))
      return "소문자, 숫자, 언더스코어(_)만 사용 가능합니다.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const nameErr = validateName(name);
    setNameError(nameErr);
    if (nameErr) return;

    const v2Ratio = 100 - v1Ratio;
    const effectiveMetric = targetMetric === "__custom__" ? customMetric : targetMetric;

    const payload: CreateExperimentPayload = {
      name,
      status,
      variant_distribution: {
        v1: v1Ratio / 100,
        v2: v2Ratio / 100,
      },
      ...(effectiveMetric ? { target_metric: effectiveMetric } : {}),
      ...(hypothesis ? { hypothesis } : {}),
    };

    try {
      await submit(payload);
    } catch {
      // 에러는 useCreateExperiment에서 setSubmitError로 처리됨
    }
  }

  if (!isOpen) return null;

  const v2Ratio = 100 - v1Ratio;
  const isRatioValid = v1Ratio >= 0 && v1Ratio <= 100;

  return (
    /* backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      {/* dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-experiment-modal-title"
        className="bg-admin-surface border border-admin-border rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-admin-border">
          <h2
            id="create-experiment-modal-title"
            className="text-base font-semibold text-admin-fg"
          >
            새 A/B 실험 생성
          </h2>
          <button
            onClick={handleClose}
            className="text-admin-muted hover:text-admin-fg text-xl leading-none"
            aria-label="모달 닫기"
          >
            ×
          </button>
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* 실험 이름 */}
          <div>
            <label
              htmlFor="exp-name"
              className="block text-[12px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1"
            >
              실험 이름 <span className="text-admin-danger">*</span>
            </label>
            <input
              ref={nameInputRef}
              id="exp-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setNameError(null);
              }}
              placeholder="feed_diversity_v1"
              className={`w-full bg-admin-surface-2 border ${
                nameError ? "border-admin-danger" : "border-admin-border"
              } rounded-lg px-3 py-2 text-sm text-admin-fg placeholder-admin-muted focus:outline-none focus:border-admin-accent font-mono`}
            />
            {nameError && (
              <p className="mt-1 text-[11px] text-admin-danger">{nameError}</p>
            )}
            <p className="mt-1 text-[11px] text-admin-muted">
              소문자, 숫자, 언더스코어(_)만 허용 (예: feed_diversity_v1)
            </p>
          </div>

          {/* 가설 */}
          <div>
            <label
              htmlFor="exp-hypothesis"
              className="block text-[12px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1"
            >
              가설 (선택)
            </label>
            <textarea
              id="exp-hypothesis"
              value={hypothesis}
              onChange={(e) => setHypothesis(e.target.value)}
              placeholder="실험 가설을 입력하세요"
              rows={3}
              className="w-full bg-admin-surface-2 border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg placeholder-admin-muted focus:outline-none focus:border-admin-accent resize-none"
            />
          </div>

          {/* 분배 비율 */}
          <div>
            <div className="text-[12px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-2">
              분배 비율 (합계 100%)
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <label htmlFor="v1-ratio" className="text-sm text-admin-fg font-mono w-6">v1</label>
                <input
                  id="v1-ratio"
                  type="number"
                  min={0}
                  max={100}
                  value={v1Ratio}
                  onChange={(e) => setV1Ratio(Number(e.target.value))}
                  className="w-20 bg-admin-surface-2 border border-admin-border rounded-lg px-2 py-1.5 text-sm text-admin-fg text-center focus:outline-none focus:border-admin-accent"
                />
                <span className="text-sm text-admin-muted">%</span>
              </div>
              <span className="text-admin-muted">/</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm text-admin-fg font-mono w-6">v2</span>
                <div className="w-20 bg-admin-surface-2 border border-admin-border rounded-lg px-2 py-1.5 text-sm text-admin-muted text-center">
                  {v2Ratio}
                </div>
                <span className="text-sm text-admin-muted">%</span>
              </div>
            </div>
            {!isRatioValid && (
              <p className="mt-1 text-[11px] text-admin-danger">
                0~100 사이의 값을 입력해 주세요.
              </p>
            )}
          </div>

          {/* 측정 지표 */}
          <div>
            <label
              htmlFor="exp-metric"
              className="block text-[12px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-1"
            >
              측정 지표 (target_metric)
            </label>
            <select
              id="exp-metric"
              value={targetMetric}
              onChange={(e) => setTargetMetric(e.target.value)}
              className="w-full bg-admin-surface-2 border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg focus:outline-none focus:border-admin-accent"
            >
              {TARGET_METRIC_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
              <option value="__custom__">직접 입력</option>
            </select>
            {targetMetric === "__custom__" && (
              <input
                type="text"
                value={customMetric}
                onChange={(e) => setCustomMetric(e.target.value)}
                placeholder="지표명 입력"
                className="mt-2 w-full bg-admin-surface-2 border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg placeholder-admin-muted focus:outline-none focus:border-admin-accent font-mono"
              />
            )}
          </div>

          {/* 자동 종료 */}
          <div className="flex items-center gap-2">
            <input
              id="auto-complete"
              type="checkbox"
              checked={autoComplete}
              onChange={(e) => setAutoComplete(e.target.checked)}
              className="accent-admin-accent"
            />
            <label htmlFor="auto-complete" className="text-sm text-admin-fg">
              14일 후 자동 종료 활성화{" "}
              <span className="text-[11px] text-admin-muted">(백엔드 cron 별도 구현)</span>
            </label>
          </div>

          {/* 상태 */}
          <div>
            <div className="text-[12px] font-semibold text-admin-fg-soft uppercase tracking-wide mb-2">
              상태
            </div>
            <div className="flex items-center gap-4">
              {(["draft", "running"] as const).map((s) => (
                <label key={s} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="exp-status"
                    value={s}
                    checked={status === s}
                    onChange={() => setStatus(s)}
                    className="accent-admin-accent"
                  />
                  <span className="text-sm text-admin-fg">
                    {s === "draft" ? "초안 (draft)" : "진행 중 (running)"}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* 제출 에러 */}
          {submitError && (
            <div className="rounded-lg bg-admin-danger/10 border border-admin-danger/20 px-3 py-2 text-sm text-admin-danger">
              {submitError}
            </div>
          )}

          {/* 버튼 */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="text-sm text-admin-muted border border-admin-border rounded-lg px-4 py-2 hover:bg-admin-surface-2 transition-colors disabled:opacity-40"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !isRatioValid}
              className="text-sm font-medium bg-admin-accent text-white rounded-lg px-5 py-2 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? "생성 중..." : "실험 생성"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
