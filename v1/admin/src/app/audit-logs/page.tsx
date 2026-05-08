import { Suspense } from "react";
import { AuditLogShell } from "@/components/audit-logs/AuditLogShell";

export const metadata = {
  title: "감사 로그 — Domo Admin",
};

export default function AuditLogsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-sm" style={{ color: "var(--admin-muted, #6b7280)" }}>
          로딩 중...
        </div>
      }
    >
      <AuditLogShell />
    </Suspense>
  );
}
