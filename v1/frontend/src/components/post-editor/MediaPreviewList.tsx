"use client";

import { CreatePostMedia, OEmbedData } from "@/lib/api";
import { OEmbedCard } from "./OEmbedCard";

interface MediaPreviewListProps {
  media: CreatePostMedia[];
  embeds: OEmbedData[];
  onRemoveMedia: (index: number) => void;
  onRemoveEmbed: (index: number) => void;
}

export function MediaPreviewList({
  media,
  embeds,
  onRemoveMedia,
  onRemoveEmbed,
}: MediaPreviewListProps) {
  if (media.length === 0 && embeds.length === 0) return null;

  return (
    <div className="space-y-3">
      {media.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {media.map((m, i) => (
            <div key={i} className="relative group aspect-square rounded-lg overflow-hidden bg-surface-hover">
              {m.type === "image" ? (
                <img
                  src={m.url}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : m.type === "video" ? (
                <div className="w-full h-full flex items-center justify-center">
                  <video
                    src={m.url}
                    className="w-full h-full object-cover"
                    muted
                  />
                  <span className="absolute inset-0 flex items-center justify-center text-3xl text-white/80">
                    ▶
                  </span>
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-text-muted text-xs p-2">
                  {m.external_source || m.type}
                </div>
              )}
              <button
                onClick={() => onRemoveMedia(i)}
                className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
              >
                ✕
              </button>
              {m.is_making_video && (
                <span className="absolute bottom-1 left-1 bg-primary text-background text-[10px] px-1.5 py-0.5 rounded">
                  메이킹
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {embeds.map((embed, i) => (
        <OEmbedCard key={i} data={embed} onRemove={() => onRemoveEmbed(i)} />
      ))}
    </div>
  );
}
