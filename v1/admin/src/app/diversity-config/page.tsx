import { Suspense } from "react";
import { DiversityConfigShell } from "@/components/diversity/DiversityConfigShell";

export const metadata = {
  title: "다양성 설정 — Domo Admin",
};

export default function DiversityConfigPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-sm" style={{ color: "var(--admin-muted, #6b7280)" }}>
          불러오는 중...
        </div>
      }
    >
      <DiversityConfigShell />
    </Suspense>
  );
}
