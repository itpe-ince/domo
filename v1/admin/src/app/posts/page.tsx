"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type AdminPost = {
  id: string; title: string | null; type: string; genre: string | null;
  status: string; like_count: number; view_count: number;
  author_name: string; thumbnail_url: string | null; created_at: string;
};

export default function AdminPostsPage() {
  const [posts, setPosts] = useState<AdminPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => { void load(); }, [query, statusFilter, offset]);

  async function load() {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (query) qs.set("q", query);
      if (statusFilter) qs.set("status", statusFilter);
      qs.set("limit", "20"); qs.set("offset", String(offset));
      const res = await apiFetch<any>(`/admin/posts/list?${qs}`, { raw: true });
      setPosts(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function changeStatus(id: string, status: string) {
    try {
      await apiFetch(`/admin/posts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
      void load();
    } catch { /* ignore */ }
  }

  return (
    <main className="flex-1 min-w-0 max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">콘텐츠 관리</h1>
      <div className="flex gap-3 mb-4">
        <input type="text" placeholder="제목/내용 검색" value={query}
          onChange={(e) => { setQuery(e.target.value); setOffset(0); }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none w-64" />
        <select value={statusFilter ?? ""} onChange={(e) => { setStatusFilter(e.target.value || null); setOffset(0); }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm">
          <option value="">상태 전체</option>
          <option value="published">공개</option><option value="pending_review">심사중</option>
          <option value="hidden">숨김</option><option value="scheduled">예약</option>
        </select>
      </div>
      {loading ? <div className="animate-pulse card p-8" /> : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted text-left">
              <tr>
                <th className="px-4 py-3">썸네일</th><th className="px-4 py-3">제목</th>
                <th className="px-4 py-3">작가</th><th className="px-4 py-3">상태</th>
                <th className="px-4 py-3">좋아요</th><th className="px-4 py-3">조치</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {posts.map((p) => (
                <tr key={p.id} className="hover:bg-surface-hover/30">
                  <td className="px-4 py-3">
                    {p.thumbnail_url ? <img src={p.thumbnail_url} alt="" className="w-10 h-10 rounded object-cover" /> : <div className="w-10 h-10 bg-surface-hover rounded" />}
                  </td>
                  <td className="px-4 py-3 font-medium">{p.title ?? "무제"}</td>
                  <td className="px-4 py-3 text-text-muted">@{p.author_name}</td>
                  <td className="px-4 py-3"><span className="badge-primary text-xs">{p.status}</span></td>
                  <td className="px-4 py-3">♥ {p.like_count}</td>
                  <td className="px-4 py-3 space-x-2">
                    {p.status === "published" && <button onClick={() => changeStatus(p.id, "hidden")} className="text-xs text-danger hover:underline">숨김</button>}
                    {p.status === "hidden" && <button onClick={() => changeStatus(p.id, "published")} className="text-xs text-primary hover:underline">공개</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setOffset(Math.max(0, offset - 20))} disabled={offset === 0} className="text-sm px-3 py-1 rounded bg-surface disabled:opacity-30">← 이전</button>
          <span className="text-sm text-text-muted py-1">{Math.floor(offset / 20) + 1} / {Math.ceil(total / 20)}</span>
          <button onClick={() => setOffset(offset + 20)} disabled={offset + 20 >= total} className="text-sm px-3 py-1 rounded bg-surface disabled:opacity-30">다음 →</button>
        </div>
      )}
    </main>
  );
}
