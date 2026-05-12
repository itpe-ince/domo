"use client";

import { useEffect, useState } from "react";
import { apiFetch, fetchMe, ApiUser, ApiClientError } from "@/lib/api";
import CreateUserModal from "@/components/CreateUserModal";

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
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [me, setMe] = useState<ApiUser | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const limit = 20;

  // 본인 정보 로드 (자가 role 변경 차단용)
  useEffect(() => {
    void fetchMe().then(setMe).catch(() => {});
  }, []);

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
      const res = await apiFetch<{ data: AdminUser[]; pagination: { total: number } }>(
        `/admin/users?${qs}`,
        { raw: true }
      );
      setUsers((res as any).data);
      setTotal((res as any).pagination.total);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  async function updateUser(id: string, patch: Record<string, string>) {
    try {
      await apiFetch(`/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      void load();
    } catch {
      /* ignore */
    }
  }

  async function handleRoleChange(user: AdminUser, newRole: string) {
    if (user.role === newRole) return;

    // admin으로 승격 또는 admin에서 강등 시 confirm
    if (newRole === "admin" || user.role === "admin") {
      const ok = window.confirm(
        newRole === "admin"
          ? `@${user.display_name} 를 관리자로 승격하시겠습니까? 모든 세션이 즉시 로그아웃되며 2FA 등록이 강제됩니다.`
          : `@${user.display_name} 의 관리자 권한을 해제하시겠습니까? 모든 세션이 즉시 로그아웃됩니다.`
      );
      if (!ok) return;
    }

    try {
      await apiFetch(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      showToast("권한이 변경되었습니다.");
      void load();
    } catch (e: any) {
      if (e?.code === "SELF_MODIFY_FORBIDDEN") {
        alert("자신의 권한은 변경할 수 없습니다.");
      } else {
        alert("권한 변경에 실패했습니다.");
      }
    }
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  return (
    <main className="flex-1 min-w-0 max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">유저 관리</h1>

      {/* 검색 / 필터 / 신규 등록 버튼 */}
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input
          type="text"
          placeholder="이름/이메일 검색"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOffset(0);
          }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none w-64"
        />
        <select
          value={roleFilter ?? ""}
          onChange={(e) => {
            setRoleFilter(e.target.value || null);
            setOffset(0);
          }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">역할 전체</option>
          {ROLES.filter(Boolean).map((r) => (
            <option key={r} value={r!}>
              {r}
            </option>
          ))}
        </select>
        <select
          value={statusFilter ?? ""}
          onChange={(e) => {
            setStatusFilter(e.target.value || null);
            setOffset(0);
          }}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">상태 전체</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s!}>
              {s}
            </option>
          ))}
        </select>

        {/* 신규 사용자 등록 버튼 */}
        <button
          onClick={() => setCreateModalOpen(true)}
          className="ml-auto bg-admin-accent text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-admin-accent-hover transition-colors"
        >
          + 신규 사용자 등록
        </button>
      </div>

      {/* 토스트 알림 */}
      {toast && (
        <div className="mb-3 px-4 py-2 rounded-lg bg-admin-success/10 border border-admin-success/30 text-admin-success text-sm font-medium">
          {toast}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="h-4 w-2/3 bg-surface-hover rounded" />
            </div>
          ))}
        </div>
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

                  {/* role 변경 드롭다운 */}
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      disabled={u.id === me?.id}
                      onChange={(e) => handleRoleChange(u, e.target.value)}
                      className="bg-admin-surface border border-admin-border rounded px-2 py-1 text-xs text-admin-fg disabled:opacity-40 disabled:cursor-not-allowed transition-colors hover:border-admin-accent/50 focus:border-admin-accent focus:ring-1 focus:ring-admin-accent outline-none"
                    >
                      <option value="user">user</option>
                      <option value="artist">artist</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>

                  <td className="px-4 py-3">
                    <span
                      className={
                        u.status === "active" ? "text-primary" : "text-danger"
                      }
                    >
                      {u.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">{u.warning_count}</td>
                  <td className="px-4 py-3">
                    {u.status === "active" ? (
                      <button
                        onClick={() => updateUser(u.id, { status: "suspended" })}
                        className="text-xs text-danger hover:underline"
                      >
                        정지
                      </button>
                    ) : u.status === "suspended" ? (
                      <button
                        onClick={() => updateUser(u.id, { status: "active" })}
                        className="text-xs text-primary hover:underline"
                      >
                        복구
                      </button>
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
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="text-sm px-3 py-1 rounded bg-surface hover:bg-surface-hover disabled:opacity-30"
          >
            ← 이전
          </button>
          <span className="text-sm text-text-muted py-1">
            {Math.floor(offset / limit) + 1} / {Math.ceil(total / limit)}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
            className="text-sm px-3 py-1 rounded bg-surface hover:bg-surface-hover disabled:opacity-30"
          >
            다음 →
          </button>
        </div>
      )}

      {/* 신규 사용자 등록 모달 */}
      <CreateUserModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={() => {
          showToast("사용자가 등록되었습니다.");
          void load();
        }}
      />
    </main>
  );
}
