"use client";

import { useEffect, useRef, useState } from "react";
import { fetchOEmbed, OEmbedData } from "@/lib/api";

interface OEmbedInputProps {
  open: boolean;
  onClose: () => void;
  onAdd: (data: OEmbedData) => void;
}

export function OEmbedInput({ open, onClose, onAdd }: OEmbedInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<OEmbedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      setUrl("");
      setPreview(null);
      setError(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [open, onClose]);

  async function handleFetch() {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOEmbed(url.trim());
      setPreview(data);
    } catch (e) {
      setError("지원하지 않는 URL이거나 가져올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div
      ref={ref}
      className="absolute bottom-full mb-2 left-0 card p-4 z-40 shadow-xl w-80 space-y-3"
    >
      <h4 className="text-sm font-semibold">외부 미디어 임베드</h4>
      <p className="text-xs text-text-muted">YouTube, Instagram, TikTok, X URL을 붙여넣으세요.</p>

      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleFetch()}
          placeholder="https://youtube.com/watch?v=..."
          className="flex-1 bg-background border border-border rounded-lg px-3 py-1.5 text-sm focus:border-primary outline-none"
          autoFocus
        />
        <button onClick={handleFetch} disabled={loading} className="btn-primary text-xs">
          {loading ? "..." : "확인"}
        </button>
      </div>

      {error && <p className="text-danger text-xs">{error}</p>}

      {preview && (
        <div className="card p-3 flex gap-3">
          {preview.thumbnail_url && (
            <img
              src={preview.thumbnail_url}
              alt=""
              className="w-16 h-16 rounded object-cover flex-shrink-0"
            />
          )}
          <div className="flex-1 min-w-0">
            <div className="text-xs text-primary font-semibold">{preview.provider}</div>
            <div className="text-sm font-medium truncate">{preview.title}</div>
            {preview.author_name && (
              <div className="text-xs text-text-muted">{preview.author_name}</div>
            )}
          </div>
        </div>
      )}

      {preview && (
        <button
          onClick={() => {
            onAdd(preview);
            onClose();
          }}
          className="btn-primary w-full text-sm"
        >
          임베드 추가
        </button>
      )}
    </div>
  );
}
