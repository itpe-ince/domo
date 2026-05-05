"use client";

import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n";

interface SchedulePickerProps {
  open: boolean;
  onClose: () => void;
  value: string; // ISO string or ""
  onChange: (iso: string) => void;
}

export function SchedulePicker({ open, onClose, value, onChange }: SchedulePickerProps) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [open, onClose]);

  if (!open) return null;

  // Min: now + 5 minutes
  const now = new Date();
  now.setMinutes(now.getMinutes() + 5);
  const minValue = now.toISOString().slice(0, 16);

  // Convert ISO to datetime-local format
  const localValue = value ? new Date(value).toISOString().slice(0, 16) : "";

  return (
    <div
      ref={ref}
      className="absolute bottom-full mb-2 left-0 card p-4 z-40 shadow-xl w-72 space-y-3"
    >
      <p role="heading" aria-level={2} className="text-sm font-semibold">{t("post.editor.schedulePicker.title")}</p>
      <p className="text-xs text-text-muted">{t("post.editor.schedulePicker.hint")}</p>

      <input
        type="datetime-local"
        value={localValue}
        min={minValue}
        onChange={(e) => {
          if (e.target.value) {
            onChange(new Date(e.target.value).toISOString());
          } else {
            onChange("");
          }
        }}
        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
      />

      {value && (
        <button
          onClick={() => {
            onChange("");
            onClose();
          }}
          className="text-xs text-danger hover:underline"
        >
          {t("post.editor.schedulePicker.cancel")}
        </button>
      )}
    </div>
  );
}
