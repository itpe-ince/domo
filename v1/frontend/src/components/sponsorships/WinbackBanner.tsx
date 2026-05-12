"use client";

/**
 * WinbackBanner — B-5 patronage-retention-ux
 *                  A-8 booster: cancellation_reason-based conditional message
 *
 * Shown on an artist's profile page when the visitor previously supported
 * this artist but no longer has an active subscription.
 *
 * 7-day dismiss cooldown is managed by useWinbackBanner (localStorage).
 * Resubscribe action uses useResubscribe hook.
 *
 * A-8 booster: optional cancellation_reason prop enables context-aware message:
 *   - too_expensive → coupon hint (D'-3 coupon system)
 *   - not_satisfied → "new series" prompt
 *   - default        → generic win-back message
 *
 * PostHog events: winback_banner_view, winback_banner_resubscribe_click
 */

import { useEffect } from "react";
import { useI18n } from "@/i18n";
import { useResubscribe } from "@/lib/hooks/useResubscribe";
import { captureEvent } from "@/lib/analytics/capture";
import type { CancellationReason } from "@/lib/api";

type Props = {
  artistId: string;
  artistName: string;
  onDismiss: () => void;
  onSuccess?: () => void;
  /** A-8 booster: last known cancellation reason for conditional message (optional) */
  cancellationReason?: CancellationReason | null;
};

export function WinbackBanner({
  artistId,
  artistName,
  onDismiss,
  onSuccess,
  cancellationReason,
}: Props) {
  const { t } = useI18n();
  const { resubscribe, subscribing, error, success } = useResubscribe();

  // PostHog: fire view event on mount
  useEffect(() => {
    captureEvent({
      type: "winback_banner_view",
      artist_id: artistId,
      ...(cancellationReason ? { cancellation_reason: cancellationReason } : {}),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artistId]);

  async function handleResubscribe() {
    captureEvent({
      type: "winback_banner_resubscribe_click",
      artist_id: artistId,
    });
    const ok = await resubscribe({ artistId });
    if (ok && onSuccess) {
      onSuccess();
    }
  }

  /** A-8: pick subtitle based on cancellation reason */
  function getSubtitle(): string {
    if (cancellationReason === "too_expensive") {
      return t("retention.winback.conditional.tooExpensive").replace(
        "{{artistName}}",
        artistName
      );
    }
    if (cancellationReason === "not_satisfied") {
      return t("retention.winback.conditional.notSatisfied").replace(
        "{{artistName}}",
        artistName
      );
    }
    return t("retention.winback.banner.subtitle").replace("{{artistName}}", artistName);
  }

  if (success) {
    return (
      <div
        role="status"
        className="rounded-xl border border-primary/30 bg-primary/5 px-5 py-4 flex items-center gap-4"
      >
        <span className="text-2xl" aria-hidden="true">🕊</span>
        <p className="text-sm font-medium text-primary">
          {t("retention.resubscribe.success")}
        </p>
      </div>
    );
  }

  return (
    <div
      role="region"
      aria-label={t("retention.winback.banner.title")}
      className="rounded-xl border border-primary/20 bg-primary/5 px-5 py-4 flex items-start gap-4"
    >
      <span className="text-2xl flex-shrink-0 mt-0.5" aria-hidden="true">🕊</span>

      <div className="flex-1 min-w-0 space-y-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            {t("retention.winback.banner.title")}
          </p>
          <p className="text-xs text-text-muted mt-0.5">
            {getSubtitle()}
          </p>
        </div>

        {error && (
          <p className="text-xs text-red-500" role="alert">{error}</p>
        )}

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleResubscribe}
            disabled={subscribing}
            className="px-4 py-1.5 bg-primary text-background rounded-full text-xs font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            aria-busy={subscribing}
          >
            {subscribing
              ? t("retention.resubscribe.confirming")
              : t("retention.winback.banner.resubscribeCta")}
          </button>

          <button
            onClick={onDismiss}
            className="text-xs text-text-muted hover:text-text-primary transition-colors"
            aria-label={t("retention.winback.banner.dismiss")}
          >
            {t("retention.winback.banner.dismiss")}
          </button>
        </div>
      </div>
    </div>
  );
}
