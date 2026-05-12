"use client";

/**
 * SeriesDetailPage — publish-controls PDCA #8, Task 4.2.
 *
 * /series/[id]: shows series cover, title, description, and post grid.
 * Owner-only edit mode with dnd-kit drag-reorder (OQ-5=A).
 * OQ-D-3=A: explicit "Save" button only calls API.
 *
 * Reorder save limitation (Step 4 carry-over):
 *   The existing setPostSeriesIds endpoint replaces a post's entire series list,
 *   which would drop other series memberships. A dedicated backend reorder
 *   endpoint is needed for safe persistence. For Step 4, reorder is local-only:
 *   the "Save" button exits edit mode but does not persist order to the server.
 *   This will be addressed in a future PDCA step.
 */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  fetchMe,
  getSeriesWithPosts,
  deleteSeries,
  type SeriesWithPosts,
  type ApiUser,
} from "@/lib/api";
import { useI18n } from "@/i18n";

export default function SeriesDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { t } = useI18n();

  const [me, setMe] = useState<ApiUser | null>(null);
  const [data, setData] = useState<SeriesWithPosts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit mode — owner only
  const [editMode, setEditMode] = useState(false);
  const [orderedPosts, setOrderedPosts] = useState<
    { id: string; title: string | null }[]
  >([]);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  // dnd-kit sensors — mirror MediaPreviewList.tsx pattern
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [meRes, dataRes] = await Promise.all([
        fetchMe().catch(() => null),
        getSeriesWithPosts(id),
      ]);
      setMe(meRes);
      setData(dataRes);
      setOrderedPosts(dataRes.posts ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "load_failed");
    } finally {
      setLoading(false);
    }
  }

  const isOwner =
    me !== null && data !== null && me.id === data.author_id;

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIndex = orderedPosts.findIndex((p) => p.id === active.id);
    const newIndex = orderedPosts.findIndex((p) => p.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    setOrderedPosts(arrayMove(orderedPosts, oldIndex, newIndex));
    setDirty(true);
  }

  async function handleSave() {
    if (!data) return;
    setSaving(true);
    try {
      // Step 4 carry-over: local-only reorder. Backend reorder endpoint
      // not yet available. Save just clears dirty state and exits edit mode.
      // See module-level comment for full explanation.
      setDirty(false);
      setEditMode(false);
    } finally {
      setSaving(false);
    }
  }

  function handleCancelEdit() {
    // Reset to server order
    setOrderedPosts(data?.posts ?? []);
    setDirty(false);
    setEditMode(false);
  }

  async function handleDelete() {
    if (!data) return;
    if (!window.confirm(t("post.series.deleteConfirm"))) return;
    try {
      await deleteSeries(data.id);
      router.push(`/users/${data.author_id}/series`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "delete_failed");
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        {t("common.loading")}
      </main>
    );
  }
  if (error) {
    return (
      <main className="p-4 text-danger">
        {error}
      </main>
    );
  }
  if (!data) {
    return (
      <main className="p-4 text-text-muted">
        {t("post.series.notFound")}
      </main>
    );
  }

  const cover = data.cover_url ?? null;

  return (
    <main className="max-w-5xl mx-auto p-4">
      {/* Back link */}
      <div className="mb-4">
        <Link
          href={`/users/${data.author_id}/series`}
          className="text-sm text-text-muted hover:underline"
        >
          &larr; {t("post.series.viewAll")}
        </Link>
      </div>

      {/* Header */}
      <header className="flex items-start gap-4 mb-6">
        <div className="w-32 h-32 flex-shrink-0 bg-surface-hover rounded-lg overflow-hidden">
          {cover ? (
            <img src={cover} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-4xl text-text-muted font-bold">
              {data.title.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold">{data.title}</h1>
          <p className="text-sm text-text-muted mt-1">
            {t("post.series.postCount", {
              count: String(data.post_count),
            })}
          </p>
          {data.description && (
            <p className="text-sm mt-2 text-text-secondary">
              {data.description}
            </p>
          )}
        </div>
        {isOwner && (
          <div className="flex gap-2 flex-shrink-0">
            {editMode ? (
              <>
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  disabled={saving}
                  className="px-3 py-1.5 text-sm rounded border border-border hover:bg-surface-hover disabled:opacity-50"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!dirty || saving}
                  className="px-3 py-1.5 text-sm rounded bg-primary text-white disabled:opacity-50"
                >
                  {saving ? t("common.loading") : t("common.save")}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setEditMode(true)}
                className="px-3 py-1.5 text-sm rounded border border-border hover:bg-surface-hover"
              >
                {t("post.series.edit")}
              </button>
            )}
          </div>
        )}
      </header>

      {/* Inline error */}
      {error && (
        <div role="alert" className="mb-4 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Empty state */}
      {orderedPosts.length === 0 && (
        <div className="p-8 text-center text-text-muted bg-surface rounded-lg border border-border">
          {t("post.series.empty")}
        </div>
      )}

      {/* Gallery — drag-reorder enabled in edit mode */}
      {orderedPosts.length > 0 && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={editMode ? handleDragEnd : undefined}
        >
          <SortableContext
            items={orderedPosts.map((p) => p.id)}
            strategy={rectSortingStrategy}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {orderedPosts.map((p) => (
                <SortablePostCard
                  key={p.id}
                  postId={p.id}
                  title={p.title}
                  editMode={editMode}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {/* Owner danger zone */}
      {isOwner && !editMode && (
        <div className="mt-8 pt-4 border-t border-border">
          <button
            type="button"
            onClick={handleDelete}
            className="text-sm text-danger hover:underline"
          >
            {t("post.series.delete")}
          </button>
        </div>
      )}
    </main>
  );
}

// ─── SortablePostCard ─────────────────────────────────────────────────────────

interface SortablePostCardProps {
  postId: string;
  title: string | null;
  editMode: boolean;
}

function SortablePostCard({ postId, title, editMode }: SortablePostCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: postId });

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: prefersReducedMotion ? "none" : transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="rounded-lg border border-border bg-surface overflow-hidden"
    >
      <a href={`/posts/${postId}`} className="block p-3 hover:bg-surface-hover transition-colors">
        <span className="text-sm text-text-primary line-clamp-2">
          {title ?? postId}
        </span>
      </a>
      {editMode && (
        <button
          type="button"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
          className="w-full text-xs text-center text-text-muted bg-surface-hover py-1.5 cursor-grab active:cursor-grabbing border-t border-border"
        >
          ⋮⋮
        </button>
      )}
    </div>
  );
}
