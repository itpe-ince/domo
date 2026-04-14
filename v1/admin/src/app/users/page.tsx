"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  role: string;
  status: string;
  country_code: string | null;
  warning_count: number;
  created_at: string;
};

const ROLES = [null, "user", "artist", "admin"];
const STATUSES = [null, "active", "suspended", "deleted"];

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, roleFilter, statusFilter, offset]);

  async function load() {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (query) qs.set("q", query);
      if (roleFilter) qs.set("role", roleFilter);
      if (statusFilter) qs.set("status", statusFilter);
      qs.set("limit", String(limit));
      qs.set("offset", String(offset));
      const res = await apiFetch<{ data: AdminUser[]; pagination: { total: number } }>(`/admin/users?${qs}`, { raw: true });
      setUsers((res as any).data);
      setTotal((res as any).pagination.total);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function updateUser(id: string, patch: Record<string, string>) {
    try {
      await apiFetch(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
      void load();
    } catch { /* ignore */ }
  }

  return (
    <main className="flex-1 min-w-0 max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">유저 관리</h1>

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text" placeholder="이름/이메일 검색" value={query}
          onChange={(e) => { setQuery(e.target.value); setOffset(0); }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none w-64"
        />
        <select value={roleFilter ?? ""} onChange={(e) => { setRoleFilter(e.target.value || null); setOffset(0); }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm">
          <option value="">역할 전체</option>
          {ROLES.filter(Boolean).map((r) => <option key={r} value={r!}>{r}</option>)}
        </select>
        <select value={statusFilter ?? ""} onChange={(e) => { setStatusFilter(e.target.value || null); setOffset(0); }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm">
          <option value="">상태 전체</option>
          {STATUSES.filter(Boolean).map((s) => <option key={s} value={s!}>{s}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="card p-4 animate-pulse"><div className="h-4 w-2/3 bg-surface-hover rounded" /></div>
        ))}</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted text-left">
              <tr>
                <th className="px-4 py-3">이름</th>
                <th className="px-4 py-3">이메일</th>
                <th className="px-4 py-3">역할</th>
                <th className="px-4 py-3">상태</th>
                <th className="px-4 py-3">경고</th>
                <th className="px-4 py-3">조치</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-surface-hover/30">
                  <td className="px-4 py-3 font-medium">@{u.display_name}</td>
                  <td className="px-4 py-3 text-text-muted">{u.email}</td>
                  <td className="px-4 py-3"><span className="badge-primary text-xs">{u.role}</span></td>
                  <td className="px-4 py-3">
                    <span className={u.status === "active" ? "text-primary" : "text-danger"}>{u.status}</span>
                  </td>
                  <td className="px-4 py-3">{u.warning_count}</td>
                  <td className="px-4 py-3">
                    {u.status === "active" ? (
                      <button onClick={() => updateUser(u.id, { status: "suspended" })}
                        className="text-xs text-danger hover:underline">정지</button>
                    ) : u.status === "suspended" ? (
                      <button onClick={() => updateUser(u.id, { status: "active" })}
                        className="text-xs text-primary hover:underline">복구</button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0}
            className="text-sm px-3 py-1 rounded bg-surface hover:bg-surface-hover disabled:opacity-30">← 이전</button>
          <span className="text-sm text-text-muted py-1">{Math.floor(offset / limit) + 1} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setOffset(offset + limit)} disabled={offset + limit >= total}
            className="text-sm px-3 py-1 rounded bg-surface hover:bg-surface-hover disabled:opacity-30">다음 →</button>
        </div>
      )}
    </main>
  );
}
