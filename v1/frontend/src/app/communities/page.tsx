"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/lib/api";
import { useMe } from "@/lib/useMe";

type Community = {
  id: string;
  name: string;
  type: string;
  description: string | null;
  cover_image_url: string | null;
  member_count: number;
};

const TYPE_LABELS: Record<string, string> = {
  school: "🏫",
  genre: "🎨",
  country: "🌍",
  custom: "💬",
};

export default function CommunitiesPage() {
  const { t } = useI18n();
  const { me } = useMe();
  const [communities, setCommunities] = useState<Community[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, [typeFilter]);

  async function load() {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (typeFilter) qs.set("type", typeFilter);
      qs.set("limit", "50");
      const res = await apiFetch<Community[]>(`/communities?${qs}`, { auth: false });
      setCommunities(res);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">커뮤니티</h1>
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto">
        {[null, "genre", "country", "school", "custom"].map((t) => (
          <button
            key={t ?? "all"}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-colors ${
              typeFilter === t
                ? "bg-primary text-background font-semibold"
                : "bg-surface text-text-secondary hover:bg-surface-hover"
            }`}
          >
            {t ? `${TYPE_LABELS[t] || ""} ${t}` : "전체"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="h-5 w-1/3 bg-surface-hover rounded mb-2" />
              <div className="h-3 w-2/3 bg-surface-hover rounded" />
            </div>
          ))}
        </div>
      ) : communities.length === 0 ? (
        <div className="card p-12 text-center text-text-muted">커뮤니티가 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {communities.map((c) => (
            <Link
              key={c.id}
              href={`/communities/${c.id}`}
              className="card p-4 flex items-center gap-4 hover:bg-surface-hover/30 transition-colors"
            >
              <div className="w-12 h-12 rounded-lg bg-surface-hover flex items-center justify-center text-2xl flex-shrink-0">
                {TYPE_LABELS[c.type] || "💬"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold truncate">{c.name}</div>
                {c.description && (
                  <div className="text-xs text-text-muted truncate">{c.description}</div>
                )}
              </div>
              <div className="text-xs text-text-muted flex-shrink-0">
                {c.member_count} members
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
