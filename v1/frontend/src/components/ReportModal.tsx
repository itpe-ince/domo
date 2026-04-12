"use client";

import { useState } from "react";
import { ApiClientError, createReport, ReportTargetType } from "@/lib/api";

const REASONS = [
  { value: "spam", label: "스팸/광고" },
  { value: "abusive", label: "욕설/비방" },
  { value: "inappropriate", label: "부적절한 콘텐츠" },
  { value: "copyright", label: "저작권 침해" },
  { value: "ai_generated", label: "AI 생성 의심" },
  { value: "other", label: "기타" },
];

export function ReportModal({
  targetType,
  targetId,
  targetLabel,
  onClose,
  onSuccess,
}: {
  targetType: ReportTargetType;
  targetId: string;
  targetLabel?: string;
  onClose: () => void;
  onSuccess?: () => void;
}) {
  const [reason, setReason] = useState(REASONS[0].value);
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await createReport({
        target_type: targetType,
        target_id: targetId,
        reason,
        description: description.trim() || undefined,
      });
      setDone(true);
      onSuccess?.();
      setTimeout(onClose, 1500);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Report failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">⚠ 신고하기</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary"
          >
            ✕
          </button>
        </header>

        {targetLabel && (
          <p className="text-text-secondary text-sm">대상: {targetLabel}</p>
        )}

        <div>
          <label className="block text-sm text-text-secondary mb-2">
            신고 사유
          </label>
          <div className="space-y-2 text-sm">
            {REASONS.map((r) => (
              <label
                key={r.value}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="radio"
                  name="reason"
                  value={r.value}
                  checked={reason === r.value}
                  onChange={() => setReason(r.value)}
                  className="accent-primary"
                  disabled={done}
                />
                <span>{r.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm text-text-secondary mb-1">
            상세 설명 (선택)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none resize-none"
            disabled={done}
          />
        </div>

        {error && (
          <div className="card border-danger p-3 text-danger text-sm">
            {error}
          </div>
        )}

        {done ? (
          <div className="card border-primary p-3 text-primary text-sm text-center">
            ✓ 신고가 접수되었습니다. 관리자가 검토합니다.
          </div>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? "제출 중..." : "신고 제출"}
          </button>
        )}
      </div>
    </div>
  );
}
