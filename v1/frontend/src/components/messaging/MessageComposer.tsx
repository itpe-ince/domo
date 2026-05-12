"use client";

import { useState, useRef } from "react";
import { useI18n } from "@/i18n";
import { SendIcon } from "@/components/icons";

interface MessageComposerProps {
  onSend: (body: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  initialValue?: string;
  onCancel?: () => void;
  submitLabel?: string;
}

const MAX_CHARS = 2000;

export function MessageComposer({
  onSend,
  disabled,
  placeholder,
  initialValue = "",
  onCancel,
  submitLabel,
}: MessageComposerProps) {
  const { t } = useI18n();
  const [body, setBody] = useState(initialValue);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const remaining = MAX_CHARS - body.length;
  const canSend = body.trim().length > 0 && !sending && !disabled && remaining >= 0;

  async function handleSend() {
    if (!canSend) return;
    setSending(true);
    setError(null);
    try {
      await onSend(body.trim());
      setBody("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.error"));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setBody(e.target.value);
    // Auto-resize
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      {error && (
        <p className="text-xs text-danger mb-2">{error}</p>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={body}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder ?? t("messaging.composer.placeholder")}
            disabled={disabled || sending}
            rows={1}
            maxLength={MAX_CHARS}
            aria-label={t("messaging.composer.ariaLabel")}
            className="w-full resize-none rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 transition-colors"
            style={{ minHeight: 40, maxHeight: 160 }}
          />
          {body.length > MAX_CHARS * 0.8 && (
            <span
              className={`absolute bottom-2 right-3 text-xs ${
                remaining < 0 ? "text-danger" : "text-text-muted"
              }`}
            >
              {remaining}
            </span>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <button
            onClick={() => void handleSend()}
            disabled={!canSend}
            aria-label={submitLabel ?? t("messaging.composer.send")}
            className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center disabled:opacity-40 hover:bg-primary/90 transition-colors flex-shrink-0"
          >
            {sending ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <SendIcon className="w-5 h-5" />
            )}
          </button>
          {onCancel && (
            <button
              onClick={onCancel}
              className="text-xs text-text-muted hover:text-text-primary transition-colors"
            >
              {t("common.cancel")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
