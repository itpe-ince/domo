/**
 * OnboardingStep1Follow — Step 1 of the growth-funnel wizard.
 *
 * Shows 5 recommended artists as a selectable grid. User can toggle
 * follow selections and confirm, or skip the step entirely.
 *
 * Analytics:
 *   - captureEvent onboarding_step { step: 1 } on mount
 *   - captureEvent first_action { action: "follow" } per artist followed
 *   - captureEvent onboarding_skip { step: 1 } on skip
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { fetchRecommendedArtists, RecommendedArtist } from "@/lib/api";
import { useFollowing } from "@/lib/FollowingContext";

interface OnboardingStep1FollowProps {
  onNext: (followedCount: number) => void;
  onSkip: () => void;
}

export function OnboardingStep1Follow({ onNext, onSkip }: OnboardingStep1FollowProps) {
  const { t } = useI18n();
  // FollowingContext 경유로 따라가서 onboarding 직후 다른 화면(FollowButton)에서도 즉시 반영
  const { follow } = useFollowing();
  const [artists, setArtists] = useState<RecommendedArtist[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fire step event on mount
  useEffect(() => {
    captureEvent({ type: "onboarding_step", step: 1 });
    void loadArtists();
  }, []);

  async function loadArtists() {
    try {
      const data = await fetchRecommendedArtists(5);
      setArtists(data);
    } catch {
      // Non-fatal: if the endpoint isn't ready, show empty state gracefully
      setArtists([]);
    } finally {
      setLoading(false);
    }
  }

  const toggleArtist = useCallback((userId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selected.size === artists.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(artists.map((a) => a.user_id)));
    }
  }, [artists, selected.size]);

  const handleConfirm = useCallback(async () => {
    if (selected.size === 0) {
      onNext(0);
      return;
    }
    setSubmitting(true);
    setError(null);
    let followedCount = 0;
    for (const userId of selected) {
      try {
        await follow(userId);
        followedCount++;
        captureEvent({ type: "first_action", action: "follow" });
      } catch {
        // Partial failure is acceptable — continue for remaining
      }
    }
    setSubmitting(false);
    onNext(followedCount);
  }, [selected, onNext, follow]);

  const handleSkip = useCallback(() => {
    captureEvent({ type: "onboarding_skip", step: 1 });
    onSkip();
  }, [onSkip]);

  const allSelected = artists.length > 0 && selected.size === artists.length;

  return (
    <div className="space-y-5">
      <div className="text-center space-y-1">
        <p className="text-3xl" aria-hidden="true">🎨</p>
        <h2 className="text-xl font-bold text-text-primary">
          {t("onboarding.step1.title")}
        </h2>
        <p className="text-sm text-text-secondary">
          {t("onboarding.step1.subtitle")}
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-surface-hover/40 animate-pulse"
              aria-hidden="true"
            />
          ))}
        </div>
      ) : artists.length === 0 ? (
        <div className="text-center py-6 text-text-muted text-sm">
          {t("onboarding.step1.noArtists")}
        </div>
      ) : (
        <>
          {/* Select-all toggle */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted">
              {selected.size > 0
                ? t("onboarding.step1.selectedCount").replace(
                    "{{count}}",
                    String(selected.size)
                  )
                : t("onboarding.step1.selectPrompt")}
            </span>
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-primary hover:underline"
            >
              {allSelected
                ? t("onboarding.step1.deselectAll")
                : t("onboarding.step1.selectAll")}
            </button>
          </div>

          {/* Artist grid */}
          <div className="space-y-2" role="group" aria-label={t("onboarding.step1.artistListAriaLabel")}>
            {artists.map((artist) => {
              const isSelected = selected.has(artist.user_id);
              return (
                <button
                  key={artist.user_id}
                  type="button"
                  onClick={() => toggleArtist(artist.user_id)}
                  aria-pressed={isSelected}
                  className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-colors text-left ${
                    isSelected
                      ? "border-primary bg-primary/8"
                      : "border-border bg-background hover:bg-surface-hover"
                  }`}
                >
                  {/* Avatar */}
                  <div className="w-10 h-10 rounded-full bg-surface-hover flex-shrink-0 overflow-hidden flex items-center justify-center">
                    {artist.avatar_url ? (
                      <img
                        src={artist.avatar_url}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span className="text-primary font-bold text-sm">
                        {artist.username.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-sm text-text-primary truncate">
                        @{artist.username}
                      </span>
                      {artist.tier_default && artist.tier_default !== "free" && (
                        <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary capitalize">
                          {artist.tier_default}
                        </span>
                      )}
                    </div>
                    {artist.bio_short && (
                      <p className="text-xs text-text-muted truncate mt-0.5">
                        {artist.bio_short}
                      </p>
                    )}
                    <p className="text-xs text-text-muted mt-0.5">
                      {t("onboarding.step1.worksCount").replace(
                        "{{count}}",
                        String(artist.recent_works_count)
                      )}
                    </p>
                  </div>

                  {/* Check indicator */}
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center border-2 flex-shrink-0 transition-colors ${
                      isSelected
                        ? "bg-primary border-primary text-background"
                        : "border-border"
                    }`}
                    aria-hidden="true"
                  >
                    {isSelected && (
                      <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                        <path
                          d="M2 6l3 3 5-5"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}

      {error && (
        <div className="card border-danger p-3 text-danger text-sm" role="alert">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-2 pt-1">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={submitting}
          className="btn-primary w-full disabled:opacity-50"
        >
          {submitting
            ? t("common.loading")
            : selected.size > 0
            ? t("onboarding.step1.followSelected").replace(
                "{{count}}",
                String(selected.size)
              )
            : t("onboarding.step1.skipAndNext")}
        </button>
        <button
          type="button"
          onClick={handleSkip}
          className="text-sm text-text-muted hover:text-text-primary transition-colors py-1"
        >
          {t("onboarding.common.skip")}
        </button>
      </div>
    </div>
  );
}
