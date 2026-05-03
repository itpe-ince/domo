"use client";

import { useState, useRef, useEffect } from "react";
import { useI18n } from "@/i18n";

export interface SignatureUploadModalProps {
  open: boolean;
  uploading: boolean;
  /** Called with the selected file when user clicks Upload. */
  onUpload: (file: File) => Promise<void>;
  onClose: () => void;
  /** Optional inline error from useSignature (i18n key or raw msg). */
  errorKey?: string | null;
}

export function SignatureUploadModal({
  open,
  uploading,
  onUpload,
  onClose,
  errorKey,
}: SignatureUploadModalProps) {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // Reset state on open + focus close button
  useEffect(() => {
    if (open) {
      setFile(null);
      setPreviewUrl(null);
      // Defer to let the dialog render before shifting focus
      requestAnimationFrame(() => closeBtnRef.current?.focus());
    }
  }, [open]);

  // Manage blob URL lifecycle — revoke on file change to prevent leaks
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // ESC closes (blocked while upload in progress to prevent gap)
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !uploading) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, uploading, onClose]);

  if (!open) return null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    try {
      await onUpload(file);
      // Parent closes on success
    } catch {
      // useSignature already set errorKey — nothing to do here
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t(
        "post.editor.media.studio.image.tool.watermark.signature.modal.title"
      )}
      // z-[60] renders above the ImageEditor modal (z-50)
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading) onClose();
      }}
    >
      <div className="relative w-full max-w-md rounded-lg bg-surface p-6 m-4 flex flex-col gap-4">
        <header className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {t(
              "post.editor.media.studio.image.tool.watermark.signature.modal.title"
            )}
          </h3>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            disabled={uploading}
            aria-label={t("common.cancel")}
            className="p-1 hover:bg-surface-hover rounded disabled:opacity-50"
          >
            ✕
          </button>
        </header>

        <p className="text-sm text-text-muted">
          {t(
            "post.editor.media.studio.image.tool.watermark.signature.modal.hint"
          )}
        </p>

        {/* File input */}
        <div className="flex flex-col gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/webp"
            onChange={handleFileChange}
            aria-label={t(
              "post.editor.media.studio.image.tool.watermark.signature.modal.title"
            )}
            className="text-sm"
          />
          <span className="text-xs text-text-muted">
            {t(
              "post.editor.media.studio.image.tool.watermark.signature.modal.requirements"
            )}
          </span>
        </div>

        {/* Preview */}
        {previewUrl && (
          <div className="border border-border rounded p-2 bg-surface-alt flex items-center justify-center min-h-[120px]">
            <img src={previewUrl} alt="" className="max-h-32 object-contain" />
          </div>
        )}

        {/* Inline error */}
        {errorKey && (
          <div role="alert" className="text-sm text-red-500">
            {t(errorKey)}
          </div>
        )}

        {/* Footer */}
        <footer className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="px-4 py-2 text-sm rounded hover:bg-surface-hover disabled:opacity-50"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-4 py-2 text-sm rounded bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
          >
            {uploading
              ? t(
                  "post.editor.media.studio.image.tool.watermark.signature.modal.uploading"
                )
              : t(
                  "post.editor.media.studio.image.tool.watermark.signature.modal.upload"
                )}
          </button>
        </footer>
      </div>
    </div>
  );
}
