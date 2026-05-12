"use client";

/**
 * BluebirdModal — 5-step Blue Bird 후원 플로우.
 *
 * Steps:
 *   1. intro     — 일회/정기 선택 + 작가 소개
 *   2. amount    — 금액 선택 (preset chips + custom)
 *   3. payment   — Stripe Elements 카드 입력 (또는 mock 모드)
 *   4. confirm   — 후원 요약 + 최종 확인
 *   5. success   — 완료 + tier 안내
 *
 * Mock 모드: NEXT_PUBLIC_STRIPE_PUBLIC_KEY 미설정 시 자동 활성화.
 *   - SetupIntent API 호출 없이 mock 플로우로 진행.
 *   - Stripe Elements 렌더링 없이 mock 카드 입력 표시.
 *
 * PCI-DSS: 실제 카드번호는 Stripe Elements가 처리 — 우리 서버 직접 거치 안 함.
 * R-4 idempotency: 이중 클릭 방지 (submitting state → button disabled).
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { captureEvent } from "@/lib/analytics/capture";
import {
  ApiClientError,
  createSetupIntent,
  createSponsorship,
  confirmSponsorship,
  createSubscription,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { ArtistTierBenefitsView } from "@/components/tier-benefits/ArtistTierBenefitsView";

// ─── Constants ────────────────────────────────────────────────────────────

const UNIT_PRICE_USD = 1; // $1 per bluebird (kept for reference)
void UNIT_PRICE_USD;

const PRESET_AMOUNTS = [1, 5, 10, 25]; // USD

function isMockMode(): boolean {
  if (typeof window === "undefined") return true;
  return !process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY;
}

// ─── Types ────────────────────────────────────────────────────────────────

type Mode = "one_time" | "recurring";
type Step = "intro" | "amount" | "payment" | "confirm" | "success";

export interface BluebirdModalProps {
  artistId: string;
  artistName: string;
  postId?: string;
  onClose: () => void;
  onSuccess: (kind: Mode, amount: number) => void;
}

// ─── Stripe lazy loader ────────────────────────────────────────────────────

let _stripePromise: Promise<unknown> | null = null;

function getStripePromise(): Promise<unknown> | null {
  if (isMockMode()) return null;
  if (!_stripePromise) {
    _stripePromise = import(
      /* @vite-ignore */ /* webpackIgnore: true */ "@stripe/stripe-js" as string
    ).then((m: unknown) =>
      (m as { loadStripe: (key: string) => Promise<unknown> }).loadStripe(
        process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY!
      )
    );
  }
  return _stripePromise;
}

// ─── Step dots ────────────────────────────────────────────────────────────

function StepDots({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-1.5" aria-hidden="true">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`block rounded-full transition-all ${
            i === current
              ? "w-4 h-2 bg-primary"
              : i < current
              ? "w-2 h-2 bg-primary/40"
              : "w-2 h-2 bg-border"
          }`}
        />
      ))}
    </div>
  );
}

// ─── Mock card input ──────────────────────────────────────────────────────

function MockCardInput({ onReady }: { onReady: (complete: boolean) => void }) {
  const { t } = useI18n();
  const [val, setVal] = useState("");
  useEffect(() => {
    onReady(val.trim().length > 0);
  }, [val, onReady]);

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border bg-surface-hover/20 p-3 text-xs text-text-muted text-center">
        {t("bluebird_modal.mockDevBanner")}
      </div>
      <input
        type="text"
        placeholder={t("bluebird_modal.mockCardPlaceholder")}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm text-text-primary focus:border-primary outline-none"
        aria-label={t("bluebird_modal.mockCardAriaLabel")}
      />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function BluebirdModal({
  artistId,
  artistName,
  postId,
  onClose,
  onSuccess,
}: BluebirdModalProps) {
  const { t } = useI18n();
  const mock = isMockMode();

  // ── Flow state ─────────────────────────────────────────────────────────
  const [step, setStep] = useState<Step>("intro");
  const [mode, setMode] = useState<Mode>("one_time");
  const [selectedPreset, setSelectedPreset] = useState<number | null>(5);
  const [customAmount, setCustomAmount] = useState("");
  const [message, setMessage] = useState("");
  const [visibility, setVisibility] = useState<
    "public" | "artist_only" | "private"
  >("public");
  const [anonymous, setAnonymous] = useState(false);

  // ── Payment state ──────────────────────────────────────────────────────
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [cardComplete, setCardComplete] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stripe refs (real mode only)
  const stripeRef = useRef<unknown>(null);
  const elementsRef = useRef<unknown>(null);
  const cardElementRef = useRef<unknown>(null);
  const cardMountRef = useRef<HTMLDivElement>(null);

  // ── Derived ────────────────────────────────────────────────────────────
  const amount = selectedPreset ?? Math.max(1, Number(customAmount) || 0);
  const bluebirdCount = amount; // 1 bluebird = $1 USD

  const STEP_ORDER: Step[] = ["intro", "amount", "payment", "confirm", "success"];
  const stepIdx = STEP_ORDER.indexOf(step);

  // ── Stripe Elements: mount on payment step (real mode) ─────────────────
  useEffect(() => {
    if (step !== "payment" || mock || !clientSecret) return;

    let cancelled = false;

    void (async () => {
      const sp = getStripePromise();
      if (!sp) return;
      const stripe = await sp;
      if (cancelled || !stripe) return;
      stripeRef.current = stripe;

      // Use PaymentElement (supports cards + more) with SetupIntent client_secret
      const stripeAny = stripe as { elements: (opts: { clientSecret: string }) => { create: (kind: string) => { mount: (el: HTMLElement) => void; on: (evt: string, cb: (e: { complete: boolean }) => void) => void } } };
      const elements = stripeAny.elements({ clientSecret });
      elementsRef.current = elements;

      const card = elements.create("payment");
      cardElementRef.current = card;

      if (cardMountRef.current) {
        card.mount(cardMountRef.current);
        card.on("change", (evt: { complete: boolean }) => {
          setCardComplete(evt.complete);
          if (evt.complete) setError(null);
        });
      }
    })();

    return () => {
      cancelled = true;
      if (cardElementRef.current) {
        // @ts-expect-error stripe types not installed
        cardElementRef.current.unmount?.();
        cardElementRef.current = null;
      }
    };
  }, [step, clientSecret, mock]);

  // ── ESC close ──────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && step !== "success") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [step, onClose]);

  // ── Step handlers ──────────────────────────────────────────────────────

  const goToPayment = useCallback(async () => {
    if (amount < 1) {
      setError(t("bluebird_modal.minAmountError"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      if (mock) {
        setClientSecret("mock_seti_placeholder_secret");
      } else {
        const si = await createSetupIntent({ purpose: mode });
        setClientSecret(si.client_secret);
      }
      setStep("payment");
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? e.message
          : t("bluebird_modal.setupInitError")
      );
    } finally {
      setSubmitting(false);
    }
  }, [amount, mode, mock, t]);

  const goToConfirm = useCallback(() => {
    if (!mock && !cardComplete) {
      setError(t("bluebird_modal.cardInfoRequiredError"));
      return;
    }
    setError(null);
    setStep("confirm");
  }, [mock, cardComplete, t]);

  const handleConfirm = useCallback(async () => {
    setSubmitting(true);
    setError(null);

    try {
      if (!mock && stripeRef.current && elementsRef.current) {
        // Real Stripe: confirm SetupIntent, then proceed to payment
        // @ts-expect-error stripe types not installed
        const { error: stripeErr } = await stripeRef.current.confirmSetup({
          elements: elementsRef.current,
          redirect: "if_required",
        });
        if (stripeErr) {
          setError(_mapStripeError(stripeErr.code, t));
          setStep("payment");
          setSubmitting(false);
          return;
        }
      }

      if (mode === "one_time") {
        const created = await createSponsorship({
          artist_id: artistId,
          post_id: postId ?? null,
          bluebird_count: bluebirdCount,
          is_anonymous: anonymous,
          visibility,
          message: message.trim() || undefined,
        });
        await confirmSponsorship(created.sponsorship.id);
      } else {
        await createSubscription({
          artist_id: artistId,
          monthly_bluebird: bluebirdCount,
        });
      }

      setStep("success");
      // A-1: sponsor_success
      captureEvent({
        type: "sponsor_success",
        mode,
        amount_cents: amount * 100,
        artist_id: artistId,
      });
      onSuccess(mode, amount);
    } catch (e) {
      const msg =
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
          ? e.message
          : t("bluebird_modal.unknownError");
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }, [
    mock,
    mode,
    artistId,
    postId,
    bluebirdCount,
    anonymous,
    visibility,
    message,
    amount,
    onSuccess,
    t,
  ]);

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("bluebird.modal.title")}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && step !== "success") onClose();
      }}
    >
      <div
        className="card w-full max-w-md p-6 space-y-5 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ──────────────────────────────────────────────── */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-primary text-2xl" aria-hidden="true">🕊</span>
            <div>
              <h2 className="text-lg font-bold text-text-primary">
                {t("bluebird.modal.title")}
              </h2>
              <p className="text-xs text-text-muted">@{artistName}</p>
            </div>
          </div>
          {step !== "success" && (
            <button
              onClick={onClose}
              aria-label={t("bluebird_modal.closeAriaLabel")}
              className="text-text-muted hover:text-text-primary transition-colors text-lg focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
            >
              ✕
            </button>
          )}
        </header>

        {/* ── Step dots ───────────────────────────────────────────── */}
        {step !== "success" && (
          <StepDots current={stepIdx} total={STEP_ORDER.length - 1} />
        )}

        {/* ── Step 1: Intro ────────────────────────────────────────── */}
        {step === "intro" && (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary leading-relaxed">
              {t("bluebird.intro")}
            </p>

            <div
              role="radiogroup"
              aria-label={t("bluebird_modal.typeSelectAriaLabel")}
              className="flex bg-background rounded-full p-1 border border-border"
            >
              {(["one_time", "recurring"] as const).map((m) => (
                <button
                  key={m}
                  role="radio"
                  aria-checked={mode === m}
                  onClick={() => setMode(m)}
                  className={`flex-1 py-2 rounded-full text-sm transition-colors ${
                    mode === m
                      ? "bg-primary text-background font-medium"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {m === "one_time"
                    ? t("bluebird.type.oneTime")
                    : t("bluebird.type.subscription")}
                </button>
              ))}
            </div>

            {/* B-4: Artist tier benefits preview */}
            <ArtistTierBenefitsView
              artistId={artistId}
              collapsible
              highlightTier={mode === "recurring" ? "subscriber" : "sponsor"}
            />

            <button
              onClick={() => {
                // A-1: sponsor_start — user confirmed intent by proceeding from intro
                captureEvent({
                  type: "sponsor_start",
                  mode,
                  amount_cents: amount * 100,
                  artist_id: artistId,
                });
                setStep("amount");
              }}
              className="btn-primary w-full"
            >
              {t("common.next")} →
            </button>
          </div>
        )}

        {/* ── Step 2: Amount ──────────────────────────────────────── */}
        {step === "amount" && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-text-primary">
              {t("bluebird.amount.label")}
            </h3>

            {/* Preset chips */}
            <div className="grid grid-cols-4 gap-2" role="group" aria-label={t("bluebird_modal.amountSelectAriaLabel")}>
              {PRESET_AMOUNTS.map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setSelectedPreset(p);
                    setCustomAmount("");
                    setError(null);
                  }}
                  aria-pressed={selectedPreset === p}
                  className={`py-2 rounded-lg text-sm font-medium border transition-colors ${
                    selectedPreset === p
                      ? "bg-primary text-background border-primary"
                      : "bg-background border-border text-text-secondary hover:border-primary hover:text-primary"
                  }`}
                >
                  ${p}
                </button>
              ))}
            </div>

            {/* Custom amount */}
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">
                $
              </span>
              <input
                type="number"
                min={1}
                max={10000}
                value={customAmount}
                onChange={(e) => {
                  setCustomAmount(e.target.value);
                  setSelectedPreset(null);
                  setError(null);
                }}
                placeholder={t("bluebird.amount.customPlaceholder")}
                aria-label={t("bluebird.amount.custom")}
                className="w-full bg-background border border-border rounded-lg pl-7 pr-4 py-2 text-sm text-text-primary focus:border-primary outline-none"
              />
            </div>

            {/* Total */}
            {amount > 0 && (
              <div className="text-right text-primary font-semibold text-sm">
                {mode === "one_time"
                  ? t("bluebird.amount.total").replace("{{amount}}", String(amount))
                  : t("bluebird.amount.totalMonthly").replace("{{amount}}", String(amount))}
              </div>
            )}

            {/* One-time extras */}
            {mode === "one_time" && (
              <>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    {t("bluebird_modal.messageLabel")}
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={2}
                    maxLength={300}
                    placeholder={t("bluebird_modal.messagePlaceholder")}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary outline-none resize-none"
                    aria-label={t("bluebird_modal.messageAriaLabel")}
                  />
                </div>

                <div role="radiogroup" aria-label={t("bluebird_modal.visibilityAriaLabel")}>
                  <p className="text-xs text-text-secondary mb-2">{t("bluebird_modal.visibilityLabel")}</p>
                  <div className="space-y-1.5 text-sm">
                    {(
                      [
                        ["public", t("bluebird_modal.visibilityPublic")],
                        ["artist_only", t("bluebird_modal.visibilityArtistOnly")],
                        ["private", t("bluebird_modal.visibilityPrivate")],
                      ] as const
                    ).map(([v, label]) => (
                      <label key={v} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="visibility"
                          checked={visibility === v}
                          onChange={() => setVisibility(v)}
                          className="accent-primary"
                        />
                        <span>{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <label className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={anonymous}
                    onChange={(e) => setAnonymous(e.target.checked)}
                    className="accent-primary"
                  />
                  <span>{t("bluebird_modal.anonymousLabel")}</span>
                </label>
              </>
            )}

            {error && (
              <div className="card border-danger p-3 text-danger text-sm" role="alert">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep("intro")}
                className="btn-secondary flex-1"
              >
                ← {t("common.back")}
              </button>
              <button
                onClick={goToPayment}
                disabled={amount < 1 || submitting}
                className="btn-primary flex-1 disabled:opacity-50"
              >
                {submitting ? t("common.loading") : t("common.next") + " →"}
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Payment ─────────────────────────────────────── */}
        {step === "payment" && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-text-primary">
              {t("bluebird.payment.title")}
            </h3>

            {mock ? (
              <MockCardInput onReady={setCardComplete} />
            ) : (
              <div className="space-y-2">
                <div
                  ref={cardMountRef}
                  className="min-h-[120px] rounded-lg border border-border bg-background p-3"
                  aria-label={t("bluebird_modal.cardInputAriaLabel")}
                />
                <p className="text-xs text-text-muted">
                  {t("bluebird.payment.hint")}
                </p>
              </div>
            )}

            {error && (
              <div className="card border-danger p-3 text-danger text-sm" role="alert">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep("amount")}
                className="btn-secondary flex-1"
              >
                ← {t("common.back")}
              </button>
              <button
                onClick={goToConfirm}
                disabled={(!mock && !cardComplete) || submitting}
                className="btn-primary flex-1 disabled:opacity-50"
              >
                {t("common.next")} →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 4: Confirm ─────────────────────────────────────── */}
        {step === "confirm" && (
          <div className="space-y-4">
            {/* Summary card */}
            <div className="card bg-surface-hover/20 p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">{t("bluebird.confirm.summary.artist")}</span>
                <span className="font-medium text-text-primary">@{artistName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">{t("bluebird.confirm.summary.type")}</span>
                <span className="font-medium text-text-primary">
                  {mode === "one_time"
                    ? t("bluebird.type.oneTime")
                    : t("bluebird.type.subscription")}
                </span>
              </div>
              <div className="flex justify-between border-t border-border pt-3">
                <span className="text-text-muted font-medium">{t("bluebird.confirm.summary.amount")}</span>
                <span className="font-bold text-primary text-base">
                  ${amount}
                  {mode === "recurring" && (
                    <span className="text-xs font-normal text-text-muted">{t("common_ui.perMonth")}</span>
                  )}
                </span>
              </div>
            </div>

            {error && (
              <div className="card border-danger p-3 text-danger text-sm" role="alert">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep("payment")}
                disabled={submitting}
                className="btn-secondary flex-1 disabled:opacity-50"
              >
                ← {t("common.back")}
              </button>
              <button
                onClick={handleConfirm}
                disabled={submitting}
                className="btn-primary flex-1 disabled:opacity-50"
                aria-busy={submitting}
              >
                {submitting
                  ? t("bluebird.confirm.processing")
                  : mode === "one_time"
                  ? t("bluebird.confirm.button").replace("{{amount}}", `$${amount}`)
                  : t("bluebird.confirm.buttonMonthly").replace(
                      "{{amount}}",
                      `$${amount}`
                    )}
              </button>
            </div>
          </div>
        )}

        {/* ── Step 5: Success (B-5 enhanced thank-you flow) ─────── */}
        {step === "success" && (
          <div className="text-center space-y-5 py-2">
            <div className="text-5xl mb-1" aria-hidden="true">🕊</div>
            <div>
              <h3 className="text-xl font-bold text-text-primary">
                {t("retention.thankyou.title")}
              </h3>
              <p className="text-sm text-text-secondary mt-1">
                {mode === "one_time"
                  ? t("bluebird.success.message").replace("{{artistName}}", artistName)
                  : t("bluebird.success.messageMonthly").replace(
                      "{{artistName}}",
                      artistName
                    )}
              </p>
            </div>

            {/* Platform default welcome message (B-4 artist custom message fallback) */}
            <div className="card border-primary/20 bg-primary/5 p-4 text-sm text-left space-y-2">
              <p className="text-xs text-text-muted italic leading-relaxed">
                "{t("retention.thankyou.welcomeMessageDefault").replace("{{artistName}}", artistName)}"
              </p>
            </div>

            {/* Tier activation hint */}
            <div className="card border-primary/30 bg-primary/5 p-4 text-sm text-left">
              <div className="font-semibold text-primary mb-1">
                🎖{" "}
                {t("bluebird.success.tier").replace(
                  "{{tier}}",
                  mode === "recurring" ? "Subscriber" : "Sponsor"
                )}
              </div>
              <div className="text-text-secondary text-xs leading-relaxed">
                {t("bluebird.success.tierHint")}
              </div>
            </div>

            {/* Next steps — B-5 */}
            <div className="text-left space-y-2">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                {t("bluebird_modal.nextStepsLabel")}
              </p>
              <div className="space-y-1.5">
                <a
                  href={`/users/${artistId}`}
                  className="flex items-center gap-2 text-sm text-text-secondary hover:text-primary transition-colors"
                  onClick={onClose}
                >
                  <span aria-hidden="true">→</span>
                  <span>{t("retention.thankyou.nextSteps.seeWorks").replace("{{artistName}}", artistName)}</span>
                </a>
                <a
                  href="/explore"
                  className="flex items-center gap-2 text-sm text-text-secondary hover:text-primary transition-colors"
                  onClick={onClose}
                >
                  <span aria-hidden="true">→</span>
                  <span>{t("retention.thankyou.nextSteps.exploreSimilar")}</span>
                </a>
                <a
                  href="/me/sponsorships"
                  className="flex items-center gap-2 text-sm text-text-secondary hover:text-primary transition-colors"
                  onClick={onClose}
                >
                  <span aria-hidden="true">→</span>
                  <span>{t("retention.thankyou.nextSteps.seeHistory")}</span>
                </a>
              </div>
            </div>

            <button onClick={onClose} className="btn-primary w-full">
              {t("bluebird.success.close")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Error mapping ────────────────────────────────────────────────────────

function _mapStripeError(
  code: string | undefined,
  t: (key: string) => string
): string {
  switch (code) {
    case "card_declined":
      return t("bluebird_modal.stripeError.cardDeclined");
    case "insufficient_funds":
      return t("bluebird_modal.stripeError.insufficientFunds");
    case "authentication_required":
    case "payment_intent_authentication_failure":
      return t("bluebird_modal.stripeError.authRequired");
    default:
      return t("bluebird_modal.stripeError.unknown");
  }
}
