"use client";

import { HistoryEntry } from "@/lib/api";

interface HistoryEntryRowProps {
  entry: HistoryEntry;
  onChange: (partial: Partial<HistoryEntry>) => void;
  onRemove: () => void;
  placeholder: string;
}

export function HistoryEntryRow({ entry, onChange, onRemove, placeholder }: HistoryEntryRowProps) {
  return (
    <div className="flex gap-2 mb-2">
      <input type="text" value={entry.title}
        onChange={(e) => onChange({ title: e.target.value })}
        placeholder={placeholder}
        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
      <input type="number" value={entry.year ?? ""}
        onChange={(e) => onChange({ year: Number(e.target.value) || undefined })}
        placeholder="연도"
        className="w-20 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
      <button onClick={onRemove} className="text-danger text-xs hover:underline">삭제</button>
    </div>
  );
}
