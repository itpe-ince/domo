"use client";

import { useState } from "react";
import { RepresentativeWork, uploadMediaFile } from "@/lib/api";

interface WorkCardProps {
  index: number;
  work: RepresentativeWork;
  onChange: (partial: Partial<RepresentativeWork>) => void;
  onRemove?: () => void;
}

export function WorkCard({ index, work, onChange, onRemove }: WorkCardProps) {
  const [uploading, setUploading] = useState(false);

  async function handleImage(file: File) {
    setUploading(true);
    try {
      const res = await uploadMediaFile(file, false);
      onChange({ image_url: res.url });
    } catch { /* ignore */ }
    finally { setUploading(false); }
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">작품 {index + 1}</span>
        {onRemove && (
          <button onClick={onRemove} className="text-xs text-danger hover:underline">삭제</button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <input type="text" value={work.title} onChange={(e) => onChange({ title: e.target.value })}
            placeholder="작품명 *"
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
        </div>
        <div className="col-span-2">
          {work.image_url ? (
            <div className="relative">
              <img src={work.image_url} alt="" className="w-full h-32 object-cover rounded-lg" />
              <button onClick={() => onChange({ image_url: "" })}
                className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">✕</button>
            </div>
          ) : (
            <label className="flex items-center justify-center h-32 border border-dashed border-border rounded-lg cursor-pointer hover:border-primary text-text-muted text-sm">
              {uploading ? "업로드 중..." : "📷 이미지 업로드 *"}
              <input type="file" accept="image/*" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImage(f); e.target.value = ""; }} />
            </label>
          )}
        </div>
        <input type="text" value={work.dimensions ?? ""} onChange={(e) => onChange({ dimensions: e.target.value })}
          placeholder="크기 (50x70cm)"
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
        <input type="text" value={work.medium ?? ""} onChange={(e) => onChange({ medium: e.target.value })}
          placeholder="매체 (Oil on canvas)"
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
        <textarea value={work.description ?? ""} onChange={(e) => onChange({ description: e.target.value })}
          placeholder="작품 설명" rows={2}
          className="col-span-2 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none resize-none" />
      </div>
    </div>
  );
}
