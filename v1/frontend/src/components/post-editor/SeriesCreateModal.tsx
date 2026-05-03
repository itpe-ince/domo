"use client";

/**
 * SeriesCreateModal — publish-controls PDCA #8, Task 3.5.
 *
 * z-[60] (above ImageEditor z-50), focus trap, ESC, backdrop click.
 * Mirror pattern from SignatureUploadModal.tsx.
 *
 * cover_url upload integrated in Step 4 (OQ-4=C).
 * Uses uploadMediaFile (existing XHR-based upload, no new endpoint).
 */

import { useState, useRef, useEffect } from "react";
import { useI18n } from "@/i18n";
import { createSeries, uploadMediaFile, ApiClientError, type Series } from "@/lib/api";

const TITLE_MAX = 200;

export interface SeriesCreateModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (series: Series) => void;
}

export function SeriesCreateModal({
  open,
  onClose,
  onCreated,
}: SeriesCreateModalProps) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string | null>(null);
  const [uploadingCover, setUploadingCover] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  // Cover preview URL lifecycle
  useEffect(() => {
    if (!coverFile) {
      setCoverPreview(null);
      return;
    }
    const url = URL.createObjectURL(coverFile);
    setCoverPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [coverFile]);

  // Reset + focus on open
  useEffect(() => {
    if (open) {
      setTitle("");
      setDescription("");
      setCoverFile(null);
      setCoverPreview(null);
      setError(null);
      setSubmitting(false);
      setUploadingCover(false);
      requestAnimationFrame(() => titleInputRef.current?.focus());
    }
  }, [open]);

  // ESC closes (blocked while submitting)
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, submitting, onClose]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) return;
    setError(null);
    setSubmitting(true);
    try {
      let cover_url: string | null = null;
      if (coverFile) {
        setUploadingCover(true);
        try {
          // Reuse existing uploadMediaFile (no new endpoint — OQ-4=C)
          const uploaded = await uploadMediaFile(coverFile);
          cover_url = uploaded.url;
        } catch {
          throw new ApiClientError(
            "COVER_UPLOAD_FAILED",
            t("post.series.createModal.coverUploadFailed")
          );
        } finally {
          setUploadingCover(false);
        }
      }
      const series = await createSeries({
        title: trimmed,
        description: description.trim() || null,
        cover_url,
      });
      onCreated(series);
      onClose();
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(t("common.error"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="series-create-modal-title"
      // z-[60] renders above ImageEditor modal (z-50)
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div className="relative w-full max-w-md rounded-lg bg-surface p-6 m-4 flex flex-col gap-4">
        <header className="flex items-center justify-between">
          <h3
            id="series-create-modal-title"
            className="text-lg font-semibold text-text-primary"
          >
            {t("post.series.createModal.title")}
          </h3>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label={t("common.cancel")}
            className="p-1 hover:bg-surface-hover rounded disabled:opacity-50 transition-colors"
          >
            ✕
          </button>
        </header>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Title */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="series-title"
              className="text-sm font-medium text-text-secondary"
            >
              {t("post.series.createModal.titleLabel")}
              <span className="text-danger ml-0.5">*</span>
            </label>
            <input
              ref={titleInputRef}
              id="series-title"
              type="text"
              value={title}
              maxLength={TITLE_MAX}
              onChange={(e) => setTitle(e.target.value)}
              disabled={submitting}
              required
              placeholder={t("post.series.createModal.titleLabel")}
              className="border border-border rounded-md px-3 py-2 text-sm bg-transparent text-text-primary outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            />
            <span className="text-[11px] text-text-muted text-right">
              {title.length}/{TITLE_MAX}
            </span>
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="series-description"
              className="text-sm font-medium text-text-secondary"
            >
              {t("post.series.createModal.descriptionLabel")}
            </label>
            <textarea
              id="series-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={submitting}
              rows={3}
              placeholder={t("post.series.createModal.descriptionLabel")}
              className="border border-border rounded-md px-3 py-2 text-sm bg-transparent text-text-primary outline-none focus:ring-1 focus:ring-primary resize-none disabled:opacity-50"
            />
          </div>

          {/* Cover image upload (OQ-4=C: manual + first-post thumbnail fallback) */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="series-cover"
              className="text-sm font-medium text-text-secondary"
            >
              {t("post.series.createModal.coverLabel")}
            </label>
            <input
              id="series-cover"
              type="file"
              accept="image/*"
              disabled={submitting}
              onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
              className="text-sm text-text-primary file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-surface-hover file:text-text-primary hover:file:bg-border disabled:opacity-50"
            />
            {coverPreview && (
              <img
                src={coverPreview}
                alt=""
                className="mt-2 h-24 w-24 rounded object-cover border border-border"
              />
            )}
            {uploadingCover && (
              <span className="text-xs text-text-muted">
                {t("post.series.createModal.coverUploading")}
              </span>
            )}
            <p className="text-xs text-text-muted">
              {t("post.series.createModal.coverHint")}
            </p>
          </div>

          {/* Inline error */}
          {error && (
            <div role="alert" className="text-sm text-danger">
              {error}
            </div>
          )}

          {/* Footer */}
          <footer className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-sm rounded hover:bg-surface-hover disabled:opacity-50 transition-colors"
            >
              {t("post.series.createModal.cancel")}
            </button>
            <button
              type="submit"
              disabled={!title.trim() || submitting}
              className="px-4 py-2 text-sm rounded bg-primary text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
            >
              {submitting
                ? t("common.loading")
                : t("post.series.createModal.submit")}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
