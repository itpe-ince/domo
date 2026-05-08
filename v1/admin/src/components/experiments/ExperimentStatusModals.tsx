"use client";

/**
 * 실험 상태 변경 Confirm 모달 — Phase 12 A-2
 *
 * PauseConfirmModal   — running → paused (재개 가능, 기존 assignments 보존)
 * CompleteConfirmModal — * → completed (되돌릴 수 없음)
 */

interface PauseConfirmModalProps {
  open: boolean;
  experimentName: string;
  onConfirm: () => void;
  onCancel: () => void;
}

interface CompleteConfirmModalProps {
  open: boolean;
  experimentName: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ModalBackdrop({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 bg-black/50 z-40"
      onClick={onClose}
      aria-hidden="true"
    />
  );
}

export function PauseConfirmModal({
  open,
  experimentName,
  onConfirm,
  onCancel,
}: PauseConfirmModalProps) {
  if (!open) return null;

  return (
    <>
      <ModalBackdrop onClose={onCancel} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pause-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div className="bg-admin-surface border border-admin-border rounded-xl shadow-2xl w-full max-w-md p-6">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <h2
              id="pause-modal-title"
              className="text-base font-semibold text-admin-fg"
            >
              실험을 일시정지하시겠습니까?
            </h2>
            <button
              onClick={onCancel}
              aria-label="닫기"
              className="text-admin-muted hover:text-admin-fg transition-colors ml-4 flex-shrink-0"
            >
              ✕
            </button>
          </div>

          {/* 본문 */}
          <div className="space-y-3 text-sm text-admin-fg-soft mb-6">
            <p>
              <span className="font-semibold text-admin-fg">
                &ldquo;{experimentName}&rdquo;
              </span>{" "}
              실험이 일시정지됩니다.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>새 사용자 variant 할당이 중단됩니다.</li>
              <li>기존 사용자의 variant는 유지됩니다. (분석 데이터 보존)</li>
              <li>재개(running)로 다시 활성화할 수 있습니다.</li>
            </ul>
          </div>

          {/* 버튼 */}
          <div className="flex justify-end gap-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-admin-muted border border-admin-border rounded-lg hover:bg-admin-surface-2 transition-colors"
            >
              취소
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 text-sm font-medium text-orange-600 border border-orange-500/40 rounded-lg hover:bg-orange-500/10 transition-colors"
            >
              일시정지
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export function CompleteConfirmModal({
  open,
  experimentName,
  onConfirm,
  onCancel,
}: CompleteConfirmModalProps) {
  if (!open) return null;

  return (
    <>
      <ModalBackdrop onClose={onCancel} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="complete-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div className="bg-admin-surface border border-admin-border rounded-xl shadow-2xl w-full max-w-md p-6">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <h2
              id="complete-modal-title"
              className="text-base font-semibold text-admin-fg"
            >
              실험을 종료하시겠습니까?
            </h2>
            <button
              onClick={onCancel}
              aria-label="닫기"
              className="text-admin-muted hover:text-admin-fg transition-colors ml-4 flex-shrink-0"
            >
              ✕
            </button>
          </div>

          {/* 경고 배너 */}
          <div className="bg-admin-danger/10 border border-admin-danger/30 rounded-lg px-4 py-3 mb-4 flex items-start gap-2">
            <span className="text-admin-danger font-bold text-base leading-none mt-0.5">
              ⚠
            </span>
            <p className="text-sm text-admin-danger font-medium">
              이 작업은 되돌릴 수 없습니다. completed 상태는 재개되지 않습니다.
            </p>
          </div>

          {/* 본문 */}
          <div className="space-y-3 text-sm text-admin-fg-soft mb-6">
            <p>
              <span className="font-semibold text-admin-fg">
                &ldquo;{experimentName}&rdquo;
              </span>{" "}
              실험이 영구 종료됩니다.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>ended_at이 현재 시각으로 기록됩니다.</li>
              <li>PostHog feature flag가 비활성화됩니다.</li>
              <li>실험 데이터는 영구 보존됩니다.</li>
            </ul>
          </div>

          {/* 버튼 */}
          <div className="flex justify-end gap-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-admin-muted border border-admin-border rounded-lg hover:bg-admin-surface-2 transition-colors"
            >
              취소
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 text-sm font-medium bg-admin-danger text-white rounded-lg hover:opacity-90 transition-opacity"
            >
              실험 종료
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
