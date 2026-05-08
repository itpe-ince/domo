"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AICollection,
  archiveCollection,
  fetchAICollectionsQueue,
  patchCollection,
  publishCollection,
  rejectCollection,
} from "@/lib/api";

// Returns the Monday of the current week as "YYYY-MM-DD"
function currentWeekStart(): string {
  const now = new Date();
  const day = now.getUTCDay(); // 0=Sun, 1=Mon, ...
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setUTCDate(now.getUTCDate() + diffToMonday);
  return monday.toISOString().slice(0, 10);
}

export function useAICollectionsQueue() {
  const [selectedWeek, setSelectedWeek] = useState<string>(currentWeekStart());
  const [collections, setCollections] = useState<AICollection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (weekStart: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAICollectionsQueue(weekStart);
      setCollections(data.items);
    } catch {
      setError("목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(selectedWeek);
  }, [selectedWeek, load]);

  const handlePublish = async (id: string) => {
    await publishCollection(id);
    setCollections((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "published" as const } : c))
    );
  };

  const handleArchive = async (id: string) => {
    await archiveCollection(id);
    setCollections((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "archived" as const } : c))
    );
  };

  const handlePatch = async (
    id: string,
    patch: { title?: string; description?: string },
    retranslate = true
  ) => {
    const updated = await patchCollection(id, patch, retranslate);
    setCollections((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              ...(updated.title !== undefined && { title: updated.title }),
              ...(updated.description !== undefined && {
                description: updated.description,
              }),
              ...(updated.title_translations && {
                title_translations: updated.title_translations,
              }),
              ...(updated.description_translations && {
                description_translations: updated.description_translations,
              }),
            }
          : c
      )
    );
  };

  const handleReject = async (id: string, reason: string) => {
    await rejectCollection(id, reason);
    setCollections((prev) => prev.filter((c) => c.id !== id));
  };

  return {
    selectedWeek,
    setSelectedWeek,
    collections,
    loading,
    error,
    handlePublish,
    handleArchive,
    handlePatch,
    handleReject,
  };
}
