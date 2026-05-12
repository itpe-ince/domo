"use client";

import { useState } from "react";
import { AICollection } from "@/lib/api";
import { useAICollectionsQueue } from "@/lib/hooks/useAICollectionsQueue";
import { CollectionCard } from "./CollectionCard";
import { CollectionEditModal } from "./CollectionEditModal";
import { CollectionRejectModal } from "./CollectionRejectModal";

// Build the last N Monday dates as option objects
function buildLastNWeeks(n: number): { label: string; value: string }[] {
  const weeks: { label: string; value: string }[] = [];
  const now = new Date();
  const day = now.getUTCDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const thisMonday = new Date(now);
  thisMonday.setUTCDate(now.getUTCDate() + diffToMonday);
  thisMonday.setUTCHours(0, 0, 0, 0);

  for (let i = 0; i < n; i++) {
    const d = new Date(thisMonday);
    d.setUTCDate(thisMonday.getUTCDate() - i * 7);
    const value = d.toISOString().slice(0, 10);
    weeks.push({ label: value, value });
  }
  return weeks;
}

function computePublishRate(
  collections: AICollection[],
  weekStart: string
): number | null {
  // Only show publish rate if the week is older than 4 weeks
  const weekDate = new Date(weekStart);
  const fourWeeksAgo = new Date();
  fourWeeksAgo.setUTCDate(fourWeeksAgo.getUTCDate() - 28);
  if (weekDate > fourWeeksAgo) return null;

  const decided = collections.filter(
    (c) => c.status === "published" || c.status === "archived"
  );
  if (decided.length === 0) return null;
  const published = decided.filter((c) => c.status === "published").length;
  return Math.round((published / decided.length) * 100);
}

export function AICollectionsQueue() {
  const {
    selectedWeek,
    setSelectedWeek,
    collections,
    loading,
    error,
    handlePublish,
    handleArchive,
    handlePatch,
    handleReject,
  } = useAICollectionsQueue();

  const [editTarget, setEditTarget] = useState<AICollection | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState<string | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);

  const weeks = buildLastNWeeks(8);
  const publishRate = computePublishRate(collections, selectedWeek);

  function openEdit(collection: AICollection) {
    setEditTarget(collection);
    setEditOpen(true);
  }

  function openReject(id: string) {
    setRejectTargetId(id);
    setRejectOpen(true);
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-lg font-bold text-admin-fg">AI 컬렉션 검수 큐</h1>
        <p className="text-sm text-admin-muted mt-0.5">주간 자동 생성 컬렉션 검수</p>
      </div>

      {/* Week Selector + Publish Rate */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <label className="text-xs text-admin-muted">주간 선택</label>
          <select
            value={selectedWeek}
            onChange={(e) => setSelectedWeek(e.target.value)}
            className="text-xs border border-admin-border rounded px-2 py-1.5 bg-admin-surface text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
          >
            {weeks.map((w) => (
              <option key={w.value} value={w.value}>
                Week of {w.label}
              </option>
            ))}
          </select>
        </div>
        <span className="text-sm text-admin-muted">
          {publishRate !== null
            ? `발행률: ${publishRate}%`
            : "발행률: N/A (운영 4주 후)"}
        </span>
      </div>

      {/* Content */}
      {loading && (
        <div className="py-12 text-center text-sm text-admin-muted">
          불러오는 중...
        </div>
      )}

      {!loading && error && (
        <div className="py-8 text-center">
          <p className="text-sm text-red-500">{error}</p>
          <button
            onClick={() => setSelectedWeek(selectedWeek)}
            className="mt-3 text-xs text-admin-accent hover:underline"
          >
            다시 시도
          </button>
        </div>
      )}

      {!loading && !error && collections.length === 0 && (
        <div className="py-12 text-center text-sm text-admin-muted">
          이번 주 검수 대기 컬렉션이 없습니다.
        </div>
      )}

      {!loading && !error && collections.length > 0 && (
        <div className="space-y-4">
          {collections.map((collection) => (
            <CollectionCard
              key={collection.id}
              collection={collection}
              onPublish={handlePublish}
              onArchive={handleArchive}
              onEdit={openEdit}
              onReject={openReject}
            />
          ))}
        </div>
      )}

      {/* Edit Modal */}
      <CollectionEditModal
        open={editOpen}
        collection={editTarget}
        onClose={() => setEditOpen(false)}
        onSaved={handlePatch}
      />

      {/* Reject Modal */}
      <CollectionRejectModal
        open={rejectOpen}
        collectionId={rejectTargetId}
        onClose={() => setRejectOpen(false)}
        onRejected={handleReject}
      />
    </div>
  );
}
