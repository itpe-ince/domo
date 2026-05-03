"use client";

/**
 * MediaPreviewList — editor-media-ux PDCA #4 (Step 4, full rewrite).
 *
 * Wraps the media grid in `DndContext` + `SortableContext` so cards become
 * drag-orderable on desktop (mouse) and mobile (200ms long-press) plus
 * keyboard (Tab → Space → Arrow → Space). MediaUploadProgress is mounted
 * just above the grid (OQ-7 = A — "MediaToolbar 직후" effectively means
 * "first child of the preview list", so the toolbar stays where it is and
 * this component owns the upload pill).
 *
 * Backwards-compatible props:
 *   - media, embeds, onRemoveMedia, onRemoveEmbed (unchanged signatures)
 *
 * New props (PDCA #4):
 *   - onReorder(activeId, overId): caller applies arrayMove to formState
 *   - onCaptionChange(id, caption): caller updates media[i].caption
 *   - uploadQueue: live UploadTask[] from useMediaUploadQueue
 *
 * The caller is responsible for assigning `_clientId` to every CreatePostMedia
 * (useMediaUploadQueue does this for new uploads; legacy drafts loaded from
 * localStorage need a one-time backfill — see MediaPreviewList itself for
 * the index-based fallback id).
 */
import { useMemo } from "react";
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";

import type { CreatePostMedia, OEmbedData } from "@/lib/api";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";
import { MediaUploadProgress } from "./MediaUploadProgress";
import { OEmbedCard } from "./OEmbedCard";
import { SortableMediaCard } from "./SortableMediaCard";

interface MediaPreviewListProps {
  media: CreatePostMedia[];
  embeds: OEmbedData[];
  onRemoveMedia: (index: number) => void;
  onRemoveEmbed: (index: number) => void;
  // PDCA #4 new
  onReorder: (activeId: string, overId: string) => void;
  onCaptionChange: (id: string, caption: string) => void;
  uploadQueue: UploadTask[];
  // editor-image-studio PDCA #6-image — Step 6 props drilling
  onEditMedia?: (id: string) => void;
}

/**
 * Stable identifier for a media item: prefers _clientId, falls back to
 * `legacy-{index}-{url-hash}` so legacy localStorage drafts (no _clientId)
 * still participate in dnd-kit without crashing. The fallback is purely
 * client-side; the backend never sees these.
 */
function mediaId(m: CreatePostMedia, index: number): string {
  if (m._clientId) return m._clientId;
  // Use url + index for a deterministic id during a single render pass.
  return `legacy-${index}-${m.url.length}-${m.url.slice(-12)}`;
}

export function MediaPreviewList({
  media,
  embeds,
  onRemoveMedia,
  onRemoveEmbed,
  onReorder,
  onCaptionChange,
  uploadQueue,
  onEditMedia,
}: MediaPreviewListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      // 8px move threshold prevents accidental drag-on-click
      activationConstraint: { distance: 8 },
    }),
    useSensor(TouchSensor, {
      // 200ms long-press = OQ-4 = A; 5px tolerance accommodates finger jitter
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Items array drives SortableContext; useMemo prevents identity churn on
  // unrelated re-renders.
  const itemIds = useMemo(() => media.map((m, i) => mediaId(m, i)), [media]);

  // Map clientId → upload task for O(1) per-card lookup
  const taskById = useMemo(() => {
    const m = new Map<string, UploadTask>();
    for (const t of uploadQueue) m.set(t.id, t);
    return m;
  }, [uploadQueue]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    onReorder(String(active.id), String(over.id));
  }

  if (media.length === 0 && embeds.length === 0 && uploadQueue.length === 0) {
    return null;
  }

  // We pass index-aware remove handlers to keep the existing onRemoveMedia
  // signature stable. The card emits its `id` for caption changes, but
  // remove resolves to the current index from itemIds.
  function handleRemoveById(id: string) {
    const idx = itemIds.indexOf(id);
    if (idx >= 0) onRemoveMedia(idx);
  }

  return (
    <div className="space-y-3">
      <MediaUploadProgress queue={uploadQueue} />

      {media.length > 0 && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={itemIds} strategy={rectSortingStrategy}>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {media.map((m, i) => {
                const id = itemIds[i];
                return (
                  <SortableMediaCard
                    key={id}
                    id={id}
                    media={m}
                    index={i}
                    uploadTask={taskById.get(id)}
                    onRemove={handleRemoveById}
                    onCaptionChange={onCaptionChange}
                    onEditMedia={onEditMedia}
                  />
                );
              })}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {embeds.map((embed, i) => (
        <OEmbedCard key={i} data={embed} onRemove={() => onRemoveEmbed(i)} />
      ))}
    </div>
  );
}
