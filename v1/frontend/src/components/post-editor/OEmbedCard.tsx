"use client";

import { OEmbedData } from "@/lib/api";

interface OEmbedCardProps {
  data: OEmbedData;
  onRemove: () => void;
}

const PROVIDER_COLORS: Record<string, string> = {
  youtube: "text-red-500",
  instagram: "text-pink-500",
  tiktok: "text-text-primary",
  x: "text-text-primary",
};

export function OEmbedCard({ data, onRemove }: OEmbedCardProps) {
  return (
    <div className="card p-3 flex gap-3 relative group">
      {data.thumbnail_url && (
        <img
          src={data.thumbnail_url}
          alt=""
          className="w-20 h-14 rounded object-cover flex-shrink-0"
        />
      )}
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-semibold uppercase ${PROVIDER_COLORS[data.provider] || ""}`}>
          {data.provider}
        </div>
        <div className="text-sm font-medium truncate">{data.title}</div>
        {data.author_name && (
          <div className="text-xs text-text-muted">{data.author_name}</div>
        )}
      </div>
      <button
        onClick={onRemove}
        className="absolute top-2 right-2 text-text-muted hover:text-danger text-xs opacity-0 group-hover:opacity-100 transition-opacity"
      >
        ✕
      </button>
    </div>
  );
}
