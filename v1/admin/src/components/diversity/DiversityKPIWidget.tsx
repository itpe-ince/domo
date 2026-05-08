"use client";

import { DiversityConfigOut } from "@/lib/api";

interface DiversityKPIWidgetProps {
  config: DiversityConfigOut;
}

export function DiversityKPIWidget({ config }: DiversityKPIWidgetProps) {
  const posthogUrl = process.env.NEXT_PUBLIC_POSTHOG_HOST
    ? `${process.env.NEXT_PUBLIC_POSTHOG_HOST}/dashboard`
    : null;

  const isBoostActive = config.emerging_artist_boost > 1.0;

  return (
    <div className="w-72 flex-shrink-0 bg-admin-surface border border-admin-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-admin-border">
        <h2 className="text-sm font-semibold text-admin-fg">
          KPI 현황 (파라미터 기준 목표)
        </h2>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* 신진작가 부스팅 배지 */}
        {isBoostActive && (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-admin-accent/10 px-3 py-1 text-xs font-medium text-admin-accent border border-admin-accent/20">
            <span className="h-1.5 w-1.5 rounded-full bg-admin-accent" />
            신진작가 부스팅 활성 (×{config.emerging_artist_boost.toFixed(2)})
          </div>
        )}

        {/* KPI 행 */}
        <div className="space-y-3">
          <KpiRow
            label="신진작가 노출률"
            value="목표 ≥ 30%"
            description="emerging_artist_boost 파라미터 기준"
          />
          <KpiRow
            label="장르 다양성"
            value={`최소 ${config.genre_min_diversity}종`}
            description="genre_min_diversity 파라미터 기준"
          />
          <KpiRow
            label="지역 다양성"
            value={`최소 ${config.region_min_diversity}종`}
            description="region_min_diversity 파라미터 기준"
          />
          <KpiRow
            label="Top-K 윈도우"
            value={`${config.top_k_window}개`}
            description="다양성 제약 적용 대상 피드 수"
          />
        </div>

        {/* Redis 캐시 안내 */}
        <p className="text-xs text-admin-muted border-t border-admin-border pt-3">
          설정 저장 후 최대 5분 이내 피드에 반영됩니다.
        </p>

        {/* PostHog 링크 */}
        <div className="border-t border-admin-border pt-3">
          {posthogUrl ? (
            <a
              href={posthogUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-admin-accent hover:underline"
            >
              PostHog 대시보드에서 실측값 확인
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-3 w-3"
                aria-hidden="true"
              >
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          ) : (
            <p className="text-xs text-admin-muted">
              PostHog 대시보드 링크는 NEXT_PUBLIC_POSTHOG_HOST 환경변수 설정 후 표시됩니다.
            </p>
          )}
          <p className="text-[11px] text-admin-muted mt-1">
            Phase 12에서 실시간 측정값 API 연동 예정
          </p>
        </div>
      </div>
    </div>
  );
}

function KpiRow({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-admin-muted">{label}</span>
        <span className="text-sm font-semibold text-admin-fg">{value}</span>
      </div>
      <p className="text-[10px] text-admin-muted mt-0.5">{description}</p>
    </div>
  );
}
