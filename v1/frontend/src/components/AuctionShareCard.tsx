"use client";

// auction-promotion-suite PDCA #11 — F-2 AuctionShareCard modal
// z-[60] matches SignatureUploadModal pattern
// R-FE-3: clipboard fallback via execCommand
// R-FE-4: URL ?t={generated_at} cache busting

import { useEffect, useRef, useState, useCallback } from "react";
import { ApiClientError, generateAuctionShareCard } from "@/lib/api";
import { ShareIcon } from "@/components/icons";
import { useI18n } from "@/i18n";

interface AuctionShareCardProps {
  auctionId: string;
  /** Only render share trigger if owner (backend enforces 403 anyway) */
  isOwner: boolean;
  /** Pre-populated from auction.share_card_url (OQ-D-5=A: all viewers see CDN URL) */
  cachedUrl?: string | null;
  /** ISO8601 timestamp of when cachedUrl was generated */
  cachedAt?: string | null;
}

/** Check if cachedUrl is still within 1h TTL */
function isCacheValid(cachedAt: string | null | undefined): boolean {
  if (!cachedAt) return false;
  const age = (Date.now() - new Date(cachedAt).getTime()) / 1000;
  return age < 3600;
}

/** Append cache-busting query param to image URL */
function bustUrl(url: string, generatedAt: string): string {
  const t = encodeURIComponent(generatedAt);
  return url.includes("?") ? `${url}&t=${t}` : `${url}?t=${t}`;
}

export function AuctionShareCard({
  auctionId,
  isOwner,
  cachedUrl,
  cachedAt,
}: AuctionShareCardProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [cardUrl, setCardUrl] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // Do not render at all for non-owners
  if (!isOwner) return null;

  const handleOpen = useCallback(async () => {
    setOpen(true);
    setError(null);

    // Use cached URL if still within TTL
    if (cachedUrl && isCacheValid(cachedAt)) {
      setCardUrl(bustUrl(cachedUrl, cachedAt!));
      setGeneratedAt(cachedAt!);
      return;
    }

    // Generate via API
    setLoading(true);
    try {
      const result = await generateAuctionShareCard(auctionId);
      const busted = bustUrl(result.share_card_url, result.generated_at);
      setCardUrl(busted);
      setGeneratedAt(result.generated_at);
    } catch (e) {
      if (e instanceof ApiClientError) {
        switch (e.code) {
          case "UNAUTHORIZED":
            setError(t("share.errorUnauthorized") || "로그인이 필요합니다.");
            break;
          case "FORBIDDEN":
            setError(t("share.errorOwnerOnly"));
            break;
          case "AUCTION_NOT_ACTIVE":
            setError(t("share.errorActiveOnly"));
            break;
          case "RATE_LIMITED":
            setError(t("share.errorRateLimit"));
            break;
          default:
            setError(t("share.errorGenerate"));
        }
      } else {
        setError(t("share.errorGenerate"));
      }
    } finally {
      setLoading(false);
    }
  }, [auctionId, cachedUrl, cachedAt, t]);

  const handleRegenerate = useCallback(async () => {
    setError(null);
    setCardUrl(null);
    setLoading(true);
    try {
      const result = await generateAuctionShareCard(auctionId);
      const busted = bustUrl(result.share_card_url, result.generated_at);
      setCardUrl(busted);
      setGeneratedAt(result.generated_at);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : t("share.errorGenerate"));
    } finally {
      setLoading(false);
    }
  }, [auctionId, t]);

  const handleClose = useCallback(() => {
    if (loading) return; // Block close during generation
    setOpen(false);
    setCopied(false);
  }, [loading]);

  const handleCopyLink = useCallback(async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // R-FE-3: execCommand fallback
      try {
        const ta = document.createElement("textarea");
        ta.value = url;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      } catch {
        // Silently fail — nothing we can do
      }
    }
  }, []);

  // Focus trap: move focus to close button when modal opens
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => closeBtnRef.current?.focus());
    }
  }, [open]);

  // ESC key handler
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, handleClose]);

  return (
    <>
      {/* Trigger button */}
      <button
        type="button"
        onClick={handleOpen}
        className="btn-secondary w-full text-sm flex items-center justify-center gap-2"
        aria-haspopup="dialog"
      >
        <ShareIcon size={16} />
        {t("share.generate")}
      </button>

      {/* Modal */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("share.title")}
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70"
            onClick={handleClose}
            aria-hidden="true"
          />

          {/* Panel */}
          <div className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="font-semibold text-text-primary">
                {t("share.title")}
              </h2>
              <button
                ref={closeBtnRef}
                onClick={handleClose}
                disabled={loading}
                className="text-text-muted hover:text-text-primary disabled:opacity-50 transition-colors"
                aria-label="닫기"
              >
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="p-4 space-y-4">
              {/* Loading state */}
              {loading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <p className="text-text-muted text-sm animate-pulse">
                    {t("share.loading")}
                  </p>
                </div>
              )}

              {/* Error state */}
              {error && !loading && (
                <div className="card border-danger p-3 text-sm text-danger">
                  {error}
                </div>
              )}

              {/* Image preview (1200x630 scaled to modal width) */}
              {cardUrl && !loading && (
                <div className="rounded-lg overflow-hidden border border-border">
                  <img
                    src={cardUrl}
                    alt={t("share.title")}
                    className="w-full object-cover max-h-[315px]"
                    style={{ aspectRatio: "1200/630" }}
                  />
                </div>
              )}

              {/* Actions */}
              {cardUrl && !loading && (
                <div className="flex flex-col gap-2">
                  {/* Download */}
                  <a
                    href={cardUrl}
                    download={`domo-auction-${auctionId}.png`}
                    className="btn-primary text-sm text-center"
                  >
                    {t("share.download")}
                  </a>

                  {/* Copy link */}
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="btn-secondary text-sm"
                  >
                    {copied ? t("share.copied") : t("share.copyLink")}
                  </button>

                  {/* Regenerate */}
                  <button
                    type="button"
                    onClick={handleRegenerate}
                    className="text-xs text-text-muted hover:text-text-secondary transition-colors"
                  >
                    ↺ 공유 카드 새로 만들기
                  </button>
                </div>
              )}

              {/* Error-only actions */}
              {error && !loading && !cardUrl && (
                <button
                  type="button"
                  onClick={handleRegenerate}
                  className="btn-secondary text-sm w-full"
                >
                  다시 시도
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
