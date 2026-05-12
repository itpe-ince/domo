"use client";

import { useEffect, useState } from "react";
import { AICollection } from "@/lib/api";

interface CollectionEditModalProps {
  open: boolean;
  collection: AICollection | null;
  onClose: () => void;
  onSaved: (
    id: string,
    patch: { title?: string; description?: string },
    retranslate: boolean
  ) => Promise<void>;
}

export function CollectionEditModal({
  open,
  collection,
  onClose,
  onSaved,
}: CollectionEditModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [retranslate, setRetranslate] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (collection) {
      setTitle(collection.title ?? "");
      setDescription(collection.description ?? "");
      setRetranslate(true);
      setError(null);
    }
  }, [collection]);

  if (!open || !collection) return null;

  async function handleSave() {
    if (!collection) return;
    setSaving(true);
    setError(null);
    try {
      await onSaved(
        collection.id,
        {
          title: title.trim() || undefined,
          description: description.trim() || undefined,
        },
        retranslate
      );
      onClose();
    } catch {
      setError("저장 중 오류가 발생했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-admin-surface border border-admin-border rounded-lg shadow-xl w-full max-w-lg mx-4 flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-admin-border">
          <h2 className="text-sm font-semibold text-admin-fg">컬렉션 편집</h2>
          <button
            onClick={onClose}
            className="text-admin-muted hover:text-admin-fg transition-colors text-lg leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </div>

        {/* Modal Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-admin-fg mb-1">
              제목 (한국어)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              className="w-full border border-admin-border rounded px-3 py-2 text-sm text-admin-fg bg-admin-surface placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-admin-accent"
              placeholder="컬렉션 제목"
            />
            <div className="text-[11px] text-admin-muted mt-1 text-right">
              {title.length}/200
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-admin-fg mb-1">
              설명 (한국어)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={5}
              className="w-full border border-admin-border rounded px-3 py-2 text-sm text-admin-fg bg-admin-surface placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-admin-accent resize-none"
              placeholder="컬렉션 설명"
            />
            <div className="text-[11px] text-admin-muted mt-1 text-right">
              {description.length}/1000
            </div>
          </div>

          {/* Retranslate checkbox */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={retranslate}
              onChange={(e) => setRetranslate(e.target.checked)}
              className="rounded border-admin-border text-admin-accent focus:ring-admin-accent"
            />
            <span className="text-xs text-admin-fg">
              저장 후 5 locale 자동 재번역{" "}
              <span className="text-admin-muted">(권장 ON)</span>
            </span>
          </label>

          {error && (
            <p className="text-xs text-red-500">{error}</p>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-admin-border">
          <button
            onClick={onClose}
            disabled={saving}
            className="border border-admin-border text-admin-fg px-4 py-1.5 rounded text-xs hover:bg-admin-surface-2 transition-colors disabled:opacity-40"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={saving || title.trim().length === 0}
            className="bg-admin-accent text-white px-4 py-1.5 rounded text-xs hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
