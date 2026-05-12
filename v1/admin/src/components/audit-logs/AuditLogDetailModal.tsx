"use client";

import { useEffect } from "react";
import { AuditLogItem } from "@/lib/api";

interface AuditLogDetailModalProps {
  log: AuditLogItem | null;
  onClose: () => void;
}

const MAX_JSON_CHARS = 5120;

function formatDateTime(isoStr: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(isoStr));
  } catch {
    return isoStr;
  }
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    success: "bg-green-100 text-green-700 border-green-200",
    failure: "bg-red-100 text-red-700 border-red-200",
    error: "bg-orange-100 text-orange-700 border-orange-200",
  };
  const cls = colorMap[status] ?? "bg-gray-100 text-gray-700 border-gray-200";
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-semibold ${cls}`}>
      {status}
    </span>
  );
}

export function AuditLogDetailModal({ log, onClose }: AuditLogDetailModalProps) {
  // ESC 키로 닫기
  useEffect(() => {
    if (!log) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [log, onClose]);

  if (!log) return null;

  const metaJson = log.audit_metadata != null
    ? JSON.stringify(log.audit_metadata, null, 2)
    : null;
  const isTruncated = metaJson != null && metaJson.length > MAX_JSON_CHARS;
  const displayJson = isTruncated ? metaJson.slice(0, MAX_JSON_CHARS) + "\n..." : metaJson;

  function handleCopyFull() {
    if (metaJson == null) return;
    void navigator.clipboard.writeText(metaJson);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="감사 로그 상세"
    >
      <div
        className="relative w-full max-w-xl mx-4 bg-admin-surface rounded-lg border border-admin-border shadow-xl flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-admin-border flex-shrink-0">
          <h2 className="text-sm font-semibold text-admin-fg">감사 로그 상세</h2>
          <button
            onClick={onClose}
            className="text-admin-muted hover:text-admin-fg transition-colors text-lg leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </div>

        {/* 본문 */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">
          {/* 기본 정보 */}
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-[12px]">
            <dt className="text-admin-muted font-medium">Action</dt>
            <dd className="text-admin-fg font-mono break-all">{log.action}</dd>

            <dt className="text-admin-muted font-medium">Actor Role</dt>
            <dd className="text-admin-fg">{log.actor_role ?? "—"}</dd>

            <dt className="text-admin-muted font-medium">Actor ID</dt>
            <dd className="text-admin-fg font-mono break-all">{log.actor_id ?? "—"}</dd>

            <dt className="text-admin-muted font-medium">Target 유형</dt>
            <dd className="text-admin-fg">{log.target_type ?? "—"}</dd>

            <dt className="text-admin-muted font-medium">Target ID</dt>
            <dd className="text-admin-fg font-mono break-all">{log.target_id ?? "—"}</dd>

            <dt className="text-admin-muted font-medium">상태</dt>
            <dd><StatusBadge status={log.status} /></dd>

            <dt className="text-admin-muted font-medium">IP</dt>
            <dd className="text-admin-fg font-mono">{log.ip_address ?? "—"}</dd>

            <dt className="text-admin-muted font-medium">시간</dt>
            <dd className="text-admin-fg">{formatDateTime(log.created_at)}</dd>
          </dl>

          {/* 메타데이터 */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-admin-fg-soft mb-2">
              메타데이터 (audit_metadata)
            </p>
            {displayJson != null ? (
              <>
                <pre className="bg-admin-bg rounded border border-admin-border p-3 text-[11px] font-mono text-admin-fg overflow-x-auto whitespace-pre-wrap break-all">
                  {displayJson}
                </pre>
                {isTruncated && (
                  <button
                    onClick={handleCopyFull}
                    className="mt-2 text-[11px] text-admin-accent hover:underline"
                  >
                    전체 내용 클립보드 복사 ({(metaJson!.length / 1024).toFixed(1)}KB)
                  </button>
                )}
              </>
            ) : (
              <p className="text-[12px] text-admin-muted">메타데이터 없음</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
