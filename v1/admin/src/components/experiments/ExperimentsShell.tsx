"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ExperimentStatus, tokenStore } from "@/lib/api";
import { useExperiments, usePatchExperiment } from "@/lib/hooks/useExperiments";
import { CreateExperimentModal } from "./CreateExperimentModal";
import { ExperimentsList, FilterTabs } from "./ExperimentsList";

export function ExperimentsShell() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState<ExperimentStatus | "all">("all");

  // auth gate — hooks rule 준수, AdminShell이 상위에서 처리하나 방어적으로 유지
  useEffect(() => {
    if (!tokenStore.get()) {
      router.replace("/login");
    }
  }, [router]);

  const { experiments, isLoading, error, refetch } = useExperiments();

  // 실험 상태 변경 뮤테이션 (Phase 12 A-2)
  const { patch: patchExp } = usePatchExperiment(() => {
    void refetch();
  });

  // 클라이언트 사이드 필터링
  const filtered = useMemo(() => {
    if (filterStatus === "all") return experiments;
    return experiments.filter((e) => e.status === filterStatus);
  }, [experiments, filterStatus]);

  // 상태별 카운트
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const exp of experiments) {
      c[exp.status] = (c[exp.status] ?? 0) + 1;
    }
    return c;
  }, [experiments]);

  // 상태 변경 핸들러 — PATCH /admin/experiments/{name} (Phase 12 A-2)
  async function handleStatusChange(
    name: string,
    status: "paused" | "completed" | "running"
  ): Promise<void> {
    await patchExp(name, { status });
  }

  return (
    <div className="flex flex-col h-full">
      {/* 페이지 헤더 */}
      <div className="border-b border-admin-border px-6 py-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-admin-fg">A/B 테스트 관리</h1>
            <p className="text-[12px] text-admin-muted mt-0.5">
              ML 실험 생성 · 조회 · 결과 분석 (K-8 / A-2)
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            aria-label="새 A/B 실험 생성"
            className="inline-flex items-center gap-1.5 text-sm font-medium bg-admin-accent text-white rounded-lg px-4 py-2 hover:opacity-90 transition-opacity whitespace-nowrap"
          >
            + 신규 실험 생성
          </button>
        </div>

        {/* 필터 탭 */}
        <div className="mt-4">
          <FilterTabs
            current={filterStatus}
            onChange={setFilterStatus}
            counts={counts}
          />
        </div>
      </div>

      {/* 콘텐츠 */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-admin-surface rounded-xl border border-admin-border h-48 animate-pulse"
              />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-admin-danger mb-3">{error}</p>
            <button
              onClick={refetch}
              className="text-sm text-admin-accent border border-admin-accent/30 rounded-lg px-4 py-2 hover:bg-admin-accent/5"
            >
              다시 불러오기
            </button>
          </div>
        ) : (
          <ExperimentsList
            experiments={filtered}
            onCreateClick={() => setIsModalOpen(true)}
            onStatusChange={handleStatusChange}
          />
        )}
      </div>

      {/* 신규 실험 생성 모달 */}
      <CreateExperimentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={() => {
          void refetch();
        }}
      />
    </div>
  );
}
