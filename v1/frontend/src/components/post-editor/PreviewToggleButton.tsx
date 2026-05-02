"use client";

/**
 * PreviewToggleButton — editor-responsive-redesign PDCA (#3, Step 2).
 *
 * Compact icon button that toggles the desktop PreviewPane visibility.
 * Renders only on `md` and up (caller is responsible for `hidden md:block`
 * wrapping if needed).
 *
 * Pattern source: design §3.2 (Desktop 2-pane).
 */

import { useI18n } from "@/i18n";
import { EyeIcon, EyeOffIcon } from "@/components/icons";

export interface PreviewToggleButtonProps {
  isVisible: boolean;
  onToggle: () => void;
}

export function PreviewToggleButton({
  isVisible,
  onToggle,
}: PreviewToggleButtonProps) {
  const { t } = useI18n();
  const label = isVisible
    ? t("post.editor.preview.toggleHide")
    : t("post.editor.preview.toggleShow");
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={isVisible}
      aria-controls="post-preview-pane"
      title={label}
      className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded-md hover:bg-surface-hover transition-colors"
    >
      {isVisible ? <EyeIcon size={16} /> : <EyeOffIcon size={16} />}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
