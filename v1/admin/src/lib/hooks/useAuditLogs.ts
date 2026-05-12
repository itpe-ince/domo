"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AuditLogFilter, AuditLogItem, fetchAuditLogs } from "@/lib/api";

export type { AuditLogFilter, AuditLogItem };

interface AuditLogPagination {
  next_cursor: string | null;
  has_more: boolean;
}

interface UseAuditLogsReturn {
  items: AuditLogItem[];
  pagination: AuditLogPagination | null;
  isLoading: boolean;
  error: string | null;
  loadNext: () => void;
  loadPrev: () => void;
  hasPrev: boolean;
}

const DEFAULT_LIMIT = 50;

export function useAuditLogs(filter: AuditLogFilter): UseAuditLogsReturn {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [pagination, setPagination] = useState<AuditLogPagination | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // cursor 히스토리: 이전 페이지 복원에 사용.
  // 인덱스 0 = 첫 페이지(cursor 없음), 이후 = 각 페이지의 시작 cursor
  const cursorHistory = useRef<Array<string | undefined>>([undefined]);
  const currentPageIdx = useRef<number>(0);

  // 현재 필터를 ref로 유지해 fetchPage 클로저에서 항상 최신 값 참조
  const filterRef = useRef<AuditLogFilter>(filter);
  filterRef.current = filter;

  const fetchPage = useCallback(async (cursor: string | undefined) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AuditLogFilter & { cursor?: string; limit?: number } = {
        ...filterRef.current,
        limit: DEFAULT_LIMIT,
      };
      if (cursor) params.cursor = cursor;

      const res = await fetchAuditLogs(params);
      setItems(res.data);
      setPagination(res.pagination);
    } catch {
      setError("감사 로그를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  }, []); // fetchPage는 filterRef.current를 통해 항상 최신 필터 접근

  // filter 변경 감지 — key 비교 방식으로 안정적 트리거
  const filterKey = JSON.stringify(filter);
  const prevFilterKey = useRef<string>(filterKey);

  useEffect(() => {
    if (prevFilterKey.current !== filterKey) {
      prevFilterKey.current = filterKey;
    }
    // filter 변경 시 cursor 히스토리 초기화 + 첫 페이지
    cursorHistory.current = [undefined];
    currentPageIdx.current = 0;
    void fetchPage(undefined);
    // filterKey가 바뀔 때만 재실행 — fetchPage는 stable ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  const loadNext = useCallback(() => {
    if (!pagination?.has_more || !pagination.next_cursor) return;
    const nextCursor = pagination.next_cursor;
    if (cursorHistory.current.length <= currentPageIdx.current + 1) {
      cursorHistory.current.push(nextCursor);
    }
    currentPageIdx.current += 1;
    void fetchPage(nextCursor);
  }, [pagination, fetchPage]);

  const loadPrev = useCallback(() => {
    if (currentPageIdx.current === 0) return;
    currentPageIdx.current -= 1;
    const prevCursor = cursorHistory.current[currentPageIdx.current];
    void fetchPage(prevCursor);
  }, [fetchPage]);

  const hasPrev = currentPageIdx.current > 0;

  return {
    items,
    pagination,
    isLoading,
    error,
    loadNext,
    loadPrev,
    hasPrev,
  };
}
