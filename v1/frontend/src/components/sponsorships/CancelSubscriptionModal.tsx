"use client";

/**
 * CancelSubscriptionModal — B-3 + B-5 + G'-2 booster
 *
 * Confirm modal for cancelling a subscription. Steps:
 *   1. Reason + timing selection (B-3 original — unchanged)
 *   2. Win-back step — actual endpoint integration (G'-2, replaces "준비 중" badge)
 *
 * B-3 regression: Step 1 is preserved exactly — reason radio (4 options) +
 * immediate/period-end toggle. Only step 2 changed.
 * B-5 WinbackBanner regression: 0 — separate component untouched.
 *
 * Win-back offers (G'-2 actual endpoint):
 *   - too_expensive   → "월 50% 할인 1개월 적용" button → POST winback-coupon
 *   - changed_mind    → "30% 할인 1개월 적용" button → POST winback-coupon
 *   - not_satisfied   → "작가에게 메시지 보내기" link (DM placeholder) + "20% 할인" button
 *   - other           → "10% 할인 1회 적용" button → POST winback-coupon
 *
 * On coupon success: WinbackSuccessModal opens → user closes → page refresh.
 * "그래도 취소" skips winback → existing cancel flow.
 *
 * z-index: 60 (above BluebirdModal's z-50).
 */

import { useState, useEffect } from "react";
import { useI18n } from "@/i18n";
import type { CancelReason } from "@/lib/hooks/useMySponsorships";
import { captureEvent } from "@/lib/analytics/capture";
import { applyWinbackCoupon, type WinbackCouponResponse, type WinbackReason } from "@/lib/api";
import { WinbackSuccessModal } from "./WinbackSuccessModal";
import { MessageButton } from "@/components/messaging/MessageButton";

type ModalStep = "reason" | "winback";

type Props = {
  open: boolean;
  subscriptionId: string;
  artistName: string;
  /** Artist's user_id — required for the DM CTA on "not_satisfied" reason. */
  artistId?: string;
  currentPeriodEnd: string | null;
  cancelling: boolean;
  onConfirm: (reason: CancelReason, immediate: boolean, feedback?: string) => void;
  onClose: () => void;
};

const REASONS: CancelReason[] = [
  "too_expensive",
  "changed_mind",
  "not_satisfied",
  "other",
];

export function CancelSubscriptionModal({
  open,
  subscriptionId,
  artistName,
  artistId,
  currentPeriodEnd,
  cancelling,
  onConfirm,
  onClose,
}: Props) {
  const { t } = useI18n();
  const [step, setStep] = useState<ModalStep>("reason");
  const [reason, setReason] = useState<CancelReason>("changed_mind");
  const [immediate, setImmediate] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [winbackLoading, setWinbackLoading] = useState(false);
  const [winbackError, setWinbackError] = useState<string | null>(null);
  const [winbackResult, setWinbackResult] = useState<WinbackCouponResponse | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  // ESC key closes modal (a11y: keyboard navigation)
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !cancelling && !winbackLoading) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, cancelling, winbackLoading, onClose]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setStep("reason");
      setReason("changed_mind");
      setFeedback("");
      setWinbackError(null);
      setWinbackLoading(false);
      setWinbackResult(null);
      setShowSuccess(false);
    }
  }, [open]);

  if (!open) return null;

  const periodEndLabel = currentPeriodEnd
    ? new Date(currentPeriodEnd).toLocaleDateString()
    : null;

  function handleReasonNext() {
    // G'-2: fire offered event when entering winback step
    captureEvent({
      type: "winback_coupon_offered",
      reason,
    });
    setStep("winback");
  }

  function handleReconsider() {
    // User decided not to cancel — close modal without action
    onClose();
  }

  function handleConfirmCancel() {
    // User declines winback offer and proceeds with cancellation
    captureEvent({
      type: "winback_coupon_declined",
      reason,
    });
    // A-1: capture sponsor_cancel before delegating to parent
    captureEvent({
      type: "sponsor_cancel",
      reason,
      tier: "subscriber",
    });
    onConfirm(reason, immediate, feedback.trim() || undefined);
  }

  async function handleAcceptWinback() {
    setWinbackError(null);
    setWinbackLoading(true);
    try {
      const result = await applyWinbackCoupon(
        subscriptionId,
        reason as WinbackReason,
        feedback.trim() || undefined
      );
      setWinbackResult(result);
      // Fire accepted event with coupon_id
      captureEvent({
        type: "winback_coupon_accepted",
        reason,
        coupon_id: result.applied_coupon.stripe_coupon_id,
      });
      setShowSuccess(true);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("common.error");
      setWinbackError(msg);
    } finally {
      setWinbackLoading(false);
    }
  }

  function handleSuccessClose() {
    setShowSuccess(false);
    onClose();
    // Refresh page to reflect active subscription status
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  }

  // ── Step 1: Reason + timing ─────────────────────────────────────────────

  if (step === "reason") {
    return (
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center"
        role="dialog"
        aria-modal="true"
        aria-label={t("patronage.supporter.cancel.modal.title")}
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/60"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Panel */}
        <div className="relative z-10 card w-full max-w-md mx-4 p-6 space-y-5">
          <h2 className="text-lg font-bold text-text-primary">
            {t("patronage.supporter.cancel.modal.title")}
          </h2>
          <p className="text-sm text-text-secondary">
            <span className="font-medium text-text-primary">@{artistName}</span>
            {" "}{t("patronage.supporter.subscriptions.cancel")}
          </p>

          {/* Reason selector */}
          <fieldset className="space-y-2">
            <legend className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">
              {t("patronage.supporter.cancel.modal.title")}
            </legend>
            {REASONS.map((r) => (
              <label
                key={r}
                className="flex items-center gap-3 cursor-pointer rounded-lg px-3 py-2.5 hover:bg-surface-hover transition-colors"
              >
                <input
                  type="radio"
                  name="cancel-reason"
                  value={r}
                  checked={reason === r}
                  onChange={() => setReason(r)}
                  className="accent-primary"
                />
                <span className="text-sm text-text-primary">
                  {t(`patronage.supporter.cancel.modal.reason.${r}`)}
                </span>
              </label>
            ))}
          </fieldset>

          {/* Immediate vs period-end */}
          <div className="space-y-2 border-t border-border pt-4">
            <label className="flex items-center gap-3 cursor-pointer rounded-lg px-3 py-2.5 hover:bg-surface-hover transition-colors">
              <input
                type="radio"
                name="cancel-timing"
                value="period_end"
                checked={!immediate}
                onChange={() => setImmediate(false)}
                className="accent-primary"
              />
              <div>
                <span className="text-sm text-text-primary block">
                  {t("patronage.supporter.cancel.modal.confirmEnd")}
                </span>
                {periodEndLabel && (
                  <span className="text-xs text-text-muted">
                    {periodEndLabel}
                  </span>
                )}
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer rounded-lg px-3 py-2.5 hover:bg-surface-hover transition-colors">
              <input
                type="radio"
                name="cancel-timing"
                value="immediate"
                checked={immediate}
                onChange={() => setImmediate(true)}
                className="accent-primary"
              />
              <span className="text-sm text-text-primary">
                {t("patronage.supporter.cancel.modal.confirmImmediate")}
              </span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              disabled={cancelling}
              className="flex-1 btn-ghost border border-border"
            >
              {t("common.cancel")}
            </button>
            <button
              onClick={handleReasonNext}
              disabled={cancelling}
              className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-full px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-60"
            >
              {t("patronage.supporter.cancel.modal.cta")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Step 2: Win-back ────────────────────────────────────────────────────

  return (
    <>
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center"
        role="dialog"
        aria-modal="true"
        aria-label={t("retention.cancel.winback.title")}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/60" aria-hidden="true" />

        {/* Panel */}
        <div className="relative z-10 card w-full max-w-md mx-4 p-6 space-y-5">
          <h2 className="text-lg font-bold text-text-primary">
            {t("retention.cancel.winback.title")}
          </h2>

          {/* Reason-conditional offer — G'-2 real endpoint */}
          {reason === "too_expensive" && (
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
              <p className="text-sm font-semibold text-text-primary">
                {t("retention.winback.offer.discount50")}
              </p>
              <p className="text-xs text-text-muted">
                {t("retention.winback.offer.discount50Desc")}
              </p>
              <button
                onClick={handleAcceptWinback}
                disabled={winbackLoading}
                className="w-full btn-primary disabled:opacity-50 text-sm"
                aria-busy={winbackLoading}
              >
                {winbackLoading
                  ? t("common.loading")
                  : t("retention.winback.offer.discount50")}
              </button>
            </div>
          )}

          {reason === "changed_mind" && (
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
              <p className="text-sm font-semibold text-text-primary">
                {t("retention.winback.offer.discount30")}
              </p>
              <p className="text-xs text-text-muted">
                {t("retention.winback.offer.discount30Desc")}
              </p>
              <button
                onClick={handleAcceptWinback}
                disabled={winbackLoading}
                className="w-full btn-primary disabled:opacity-50 text-sm"
                aria-busy={winbackLoading}
              >
                {winbackLoading
                  ? t("common.loading")
                  : t("retention.winback.offer.discount30")}
              </button>
            </div>
          )}

          {reason === "not_satisfied" && (
            <div className="space-y-3">
              {/* DM CTA — Phase 8+ messaging now wired (was placeholder) */}
              <div className="rounded-xl border border-border bg-surface-hover p-4 space-y-3">
                <p className="text-sm text-text-secondary">
                  {t("retention.cancel.winback.offer.message")}
                </p>
                {artistId ? (
                  <MessageButton
                    userId={artistId}
                    size="sm"
                    variant="secondary"
                    label={t("messaging.compose.dmArtistCta", { artistName })}
                  />
                ) : (
                  <span className="text-xs text-text-muted italic">
                    {t("retention.winback.offer.dmComingSoon")}
                  </span>
                )}
              </div>
              {/* 20% discount fallback */}
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
                <p className="text-sm font-semibold text-text-primary">
                  {t("retention.winback.offer.discount20")}
                </p>
                <p className="text-xs text-text-muted">
                  {t("retention.winback.offer.discount20Desc")}
                </p>
                <div>
                  <label className="block text-xs text-text-muted mb-1.5">
                    {t("retention.cancel.winback.offer.feedback")}
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    rows={3}
                    maxLength={500}
                    placeholder={t("cancel_modal.feedbackPlaceholder")}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary outline-none resize-none"
                    aria-label={t("cancel_modal.feedbackAriaLabel")}
                  />
                </div>
                <button
                  onClick={handleAcceptWinback}
                  disabled={winbackLoading}
                  className="w-full btn-primary disabled:opacity-50 text-sm"
                  aria-busy={winbackLoading}
                >
                  {winbackLoading
                    ? t("common.loading")
                    : t("retention.winback.offer.discount20")}
                </button>
              </div>
            </div>
          )}

          {reason === "other" && (
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
              <p className="text-sm font-semibold text-text-primary">
                {t("retention.winback.offer.discount10")}
              </p>
              <p className="text-xs text-text-muted">
                {t("retention.winback.offer.discount10Desc")}
              </p>
              <div>
                <label className="block text-xs text-text-muted mb-1.5">
                  {t("retention.cancel.winback.offer.feedback")}{" "}
                  {t("cancel_modal.optionalSuffix")}
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={3}
                  maxLength={500}
                  placeholder={t("cancel_modal.otherFeedbackPlaceholder")}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary outline-none resize-none"
                  aria-label={t("cancel_modal.otherFeedbackAriaLabel")}
                />
              </div>
              <button
                onClick={handleAcceptWinback}
                disabled={winbackLoading}
                className="w-full btn-primary disabled:opacity-50 text-sm"
                aria-busy={winbackLoading}
              >
                {winbackLoading
                  ? t("common.loading")
                  : t("retention.winback.offer.discount10")}
              </button>
            </div>
          )}

          {/* Error feedback */}
          {winbackError && (
            <p className="text-sm text-red-500" role="alert">
              {winbackError}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleReconsider}
              disabled={cancelling || winbackLoading}
              className="flex-1 btn-primary disabled:opacity-50"
            >
              {t("retention.cancel.winback.reconsider")}
            </button>
            <button
              onClick={handleConfirmCancel}
              disabled={cancelling || winbackLoading}
              className="flex-1 text-red-500 hover:text-red-600 border border-red-300 hover:border-red-500 rounded-full px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-60"
              aria-busy={cancelling}
            >
              {cancelling
                ? t("common.loading")
                : t("retention.cancel.winback.confirmCancel")}
            </button>
          </div>
        </div>
      </div>

      {/* Success modal — z-[70] above this modal */}
      <WinbackSuccessModal
        open={showSuccess}
        couponResponse={winbackResult}
        onClose={handleSuccessClose}
      />
    </>
  );
}
