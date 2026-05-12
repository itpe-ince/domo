"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AuditLogFilter } from "@/lib/hooks/useAuditLogs";

interface AuditLogFiltersProps {
  filter: AuditLogFilter;
  onFilterChange: (f: AuditLogFilter) => void;
}

const TARGET_TYPE_OPTIONS = [
  "user",
  "post",
  "auction",
  "featured_artist_candidate",
  "ai_collection",
  "experiment",
  "diversity_config",
];

const DEBOUNCE_MS = 300;

export function AuditLogFilters({ filter, onFilterChange }: AuditLogFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [local, setLocal] = useState<AuditLogFilter>(filter);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // filter prop 변경 시 local 동기화 (초기화 버튼 눌렀을 때 등)
  useEffect(() => {
    setLocal(filter);
  }, [filter]);

  const emitChange = useCallback(
    (next: AuditLogFilter) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onFilterChange(next);
      }, DEBOUNCE_MS);
    },
    [onFilterChange]
  );

  function handleField(key: keyof AuditLogFilter, value: string) {
    const next = { ...local, [key]: value || undefined };
    setLocal(next);
    emitChange(next);
  }

  function handleReset() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const empty: AuditLogFilter = {};
    setLocal(empty);
    onFilterChange(empty);
  }

  const hasAnyFilter = Object.values(local).some(Boolean);

  return (
    <div className="mb-4">
      {/* 토글 버튼 */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsOpen((o) => !o)}
          className="flex items-center gap-1.5 text-[12px] font-medium text-admin-accent border border-admin-accent/40 rounded-md px-3 py-1.5 hover:bg-admin-accent/5 transition-colors"
          aria-expanded={isOpen}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="h-3.5 w-3.5"
          >
            <path d="M1 3h14a1 1 0 1 1 0 2H1a1 1 0 0 1 0-2zm2 4h10a1 1 0 1 1 0 2H3a1 1 0 0 1 0-2zm2 4h6a1 1 0 1 1 0 2H5a1 1 0 0 1 0-2z" />
          </svg>
          {isOpen ? "필터 숨기기" : "필터 표시"}
        </button>
        {hasAnyFilter && (
          <button
            onClick={handleReset}
            className="text-[11px] text-admin-muted hover:text-admin-danger transition-colors underline underline-offset-2"
          >
            필터 초기화
          </button>
        )}
      </div>

      {/* 필터 패널 */}
      {isOpen && (
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4 bg-admin-surface border border-admin-border rounded-lg">
          {/* Actor UUID */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              Actor (UUID)
            </label>
            <input
              type="text"
              value={local.actor_id ?? ""}
              onChange={(e) => handleField("actor_id", e.target.value)}
              placeholder="actor UUID 입력"
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-admin-accent"
            />
          </div>

          {/* Action */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              Action
            </label>
            <input
              type="text"
              value={local.action ?? ""}
              onChange={(e) => handleField("action", e.target.value)}
              placeholder="예: admin.create_user"
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-admin-accent"
            />
          </div>

          {/* Target 유형 */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              Target 유형
            </label>
            <select
              value={local.target_type ?? ""}
              onChange={(e) => handleField("target_type", e.target.value)}
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
            >
              <option value="">전체</option>
              {TARGET_TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Target ID */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              Target ID (UUID)
            </label>
            <input
              type="text"
              value={local.target_id ?? ""}
              onChange={(e) => handleField("target_id", e.target.value)}
              placeholder="target UUID 입력"
              disabled={!local.target_type}
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-admin-accent disabled:opacity-40 disabled:cursor-not-allowed"
            />
          </div>

          {/* 기간 시작 */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              기간 시작
            </label>
            <input
              type="date"
              value={local.period_start ?? ""}
              onChange={(e) => handleField("period_start", e.target.value)}
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
            />
          </div>

          {/* 기간 종료 */}
          <div>
            <label className="block text-[11px] font-medium text-admin-muted mb-1">
              기간 종료
            </label>
            <input
              type="date"
              value={local.period_end ?? ""}
              onChange={(e) => handleField("period_end", e.target.value)}
              min={local.period_start}
              className="w-full rounded-md border border-admin-border bg-admin-bg px-3 py-1.5 text-[12px] text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
            />
          </div>
        </div>
      )}
    </div>
  );
}
