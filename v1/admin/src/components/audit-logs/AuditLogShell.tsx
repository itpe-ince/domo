"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiUser, fetchMe } from "@/lib/api";
import { AuditLogFilter } from "@/lib/hooks/useAuditLogs";
import { AuditLogFilters } from "./AuditLogFilters";
import { AuditLogList } from "./AuditLogList";

export function AuditLogShell() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [filter, setFilter] = useState<AuditLogFilter>({});

  useEffect(() => {
    void fetchMe()
      .then((user: ApiUser) => {
        if (user.role !== "admin") {
          router.replace("/");
          return;
        }
        setAuthChecked(true);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  if (!authChecked) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-admin-muted text-sm">로딩 중...</div>
      </div>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-6xl mx-auto px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-admin-fg">감사 로그</h1>
        <p className="text-admin-muted text-sm mt-1">운영자 액션 이력 추적</p>
      </header>
      <AuditLogFilters filter={filter} onFilterChange={setFilter} />
      <AuditLogList filter={filter} />
    </main>
  );
}
