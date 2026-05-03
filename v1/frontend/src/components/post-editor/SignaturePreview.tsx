"use client";

import { useI18n } from "@/i18n";

export interface SignaturePreviewProps {
  signatureUrl: string;
  loading: boolean;
  onChange: () => void;
  onDelete: () => void;
}

export function SignaturePreview({
  signatureUrl,
  loading,
  onChange,
  onDelete,
}: SignaturePreviewProps) {
  const { t } = useI18n();

  function handleDelete() {
    if (
      window.confirm(
        t(
          "post.editor.media.studio.image.tool.watermark.signature.removeConfirm"
        )
      )
    ) {
      onDelete();
    }
  }

  return (
    <div className="flex items-center gap-2 pt-2 border-t border-border">
      <span className="text-xs text-text-muted">
        {t(
          "post.editor.media.studio.image.tool.watermark.signature.current"
        )}
        :
      </span>
      <img
        src={signatureUrl}
        alt={t(
          "post.editor.media.studio.image.tool.watermark.signature.label"
        )}
        className="h-8 w-auto bg-checker rounded border border-border"
      />
      <button
        type="button"
        onClick={onChange}
        disabled={loading}
        className="px-2 py-1 text-xs rounded hover:bg-surface-hover disabled:opacity-50"
      >
        {t(
          "post.editor.media.studio.image.tool.watermark.signature.change"
        )}
      </button>
      <button
        type="button"
        onClick={handleDelete}
        disabled={loading}
        className="px-2 py-1 text-xs rounded text-red-500 hover:bg-red-500/10 disabled:opacity-50"
      >
        {t(
          "post.editor.media.studio.image.tool.watermark.signature.remove"
        )}
      </button>
    </div>
  );
}
