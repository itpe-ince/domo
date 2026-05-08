"use client";

import { useState } from "react";
import { AuditLogItem } from "@/lib/api";
import { AuditLogFilter, useAuditLogs } from "@/lib/hooks/useAuditLogs";
import { AuditLogDetailModal } from "./AuditLogDetailModal";

interface AuditLogListProps {
  filter: AuditLogFilter;
}

function formatDateTime(isoStr: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(isoStr));
  } catch {
    return isoStr;
  }
}

function ActorBadge({ role }: { role: string | null }) {
  const isAdmin = role === "admin";
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold ${
        isAdmin
          ? "bg-blue-100 text-blue-700 border border-blue-200"
          : "bg-gray-100 text-gray-600 border border-gray-200"
      }`}
    >
      {role ?? "—"}
    </span>
  );
}

function ActionBadge({ action }: { action: string }) {
  const isAdmin = action.startsWith("admin.");
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium font-mono ${
        isAdmin
          ? "bg-blue-50 text-blue-700 border border-blue-200"
          : "bg-gray-50 text-gray-600 border border-gray-200"
      }`}
    >
      {action}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    success: "bg-green-500",
    failure: "bg-red-500",
    error: "bg-orange-400",
  };
  const cls = colorMap[status] ?? "bg-gray-400";
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${cls}`} />;
}

function SkeletonRow() {
  return (
    <tr className="border-b border-admin-border">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-admin-surface-2 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

export function AuditLogList({ filter }: AuditLogListProps) {
  const { items, pagination, isLoading, error, loadNext, loadPrev, hasPrev } =
    useAuditLogs(filter);
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center justify-between">
        <span>{error}</span>
        <button
          onClick={() => window.location.reload()}
          className="text-[12px] underline hover:no-underline"
        >
          재시도
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-lg border border-admin-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-admin-surface-2 border-b border-admin-border">
              <tr>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  Actor
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  Action
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  Target
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  상태
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  IP
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-admin-fg-soft">
                  시간
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => <SkeletonRow key={i} />)
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-admin-muted text-[13px]"
                  >
                    감사 로그가 없습니다
                  </td>
                </tr>
              ) : (
                items.map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    className="border-b border-admin-border hover:bg-admin-surface-2 cursor-pointer transition-colors"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") setSelectedLog(log);
                    }}
                  >
                    {/* Actor */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <ActorBadge role={log.actor_role} />
                        {log.actor_id && (
                          <span className="text-admin-muted font-mono text-[10px]">
                            {log.actor_id.slice(0, 8)}
                          </span>
                        )}
                      </div>
                    </td>
                    {/* Action */}
                    <td className="px-4 py-3">
                      <ActionBadge action={log.action} />
                    </td>
                    {/* Target */}
                    <td className="px-4 py-3">
                      {log.target_type ? (
                        <div className="flex flex-col gap-0.5">
                          <span className="text-admin-fg">{log.target_type}</span>
                          {log.target_id && (
                            <span className="text-admin-muted font-mono text-[10px]">
                              {log.target_id.slice(0, 8)}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-admin-muted">—</span>
                      )}
                    </td>
                    {/* Status */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <StatusDot status={log.status} />
                        <span className="text-admin-fg">{log.status}</span>
                      </div>
                    </td>
                    {/* IP */}
                    <td className="px-4 py-3 font-mono text-admin-muted">
                      {log.ip_address ?? "—"}
                    </td>
                    {/* Time */}
                    <td className="px-4 py-3 text-admin-muted whitespace-nowrap">
                      {formatDateTime(log.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 페이지네이션 */}
        {!isLoading && items.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-admin-border bg-admin-surface-2">
            <button
              onClick={loadPrev}
              disabled={!hasPrev}
              className="text-[12px] font-medium text-admin-fg border border-admin-border rounded-md px-3 py-1.5 hover:bg-admin-surface transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              이전 페이지
            </button>
            <span className="text-[11px] text-admin-muted">
              {items.length}건 표시
              {pagination?.has_more && (
                <span className="ml-1 text-admin-accent">• 다음 페이지 있음</span>
              )}
            </span>
            <button
              onClick={loadNext}
              disabled={!pagination?.has_more}
              className="text-[12px] font-medium text-admin-fg border border-admin-border rounded-md px-3 py-1.5 hover:bg-admin-surface transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              다음 페이지
            </button>
          </div>
        )}
      </div>

      <AuditLogDetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
    </>
  );
}
