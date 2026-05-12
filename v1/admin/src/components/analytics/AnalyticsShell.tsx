"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, tokenStore, AnalyticsPeriod } from "@/lib/api";
import { PeriodSelector } from "./PeriodSelector";
import { CohortRetentionCard } from "./CohortRetentionCard";
import { NewsletterOpenRateCard } from "./NewsletterOpenRateCard";
import { FeedCTRCard } from "./FeedCTRCard";
import { AIFeaturesUsageCard } from "./AIFeaturesUsageCard";

export function AnalyticsShell() {
  const router = useRouter();
  const [period, setPeriod] = useState<AnalyticsPeriod>("30d");
  const [bust, setBust] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  // auth gate
  useEffect(() => {
    if (!tokenStore.get()) {
      router.replace("/login");
      return;
    }
    void fetchMe()
      .then((user) => {
        if (user.role !== "admin") {
          router.replace("/login");
          return;
        }
        // 2FA 완료 여부 확인
        const hasTotp = !!user.totp_enabled_at;
        const hasPasskey =
          typeof user.passkey_count === "number" && user.passkey_count > 0;
        const secondFactorEnrolled =
          typeof user.second_factor_enrolled === "boolean"
            ? user.second_factor_enrolled
            : hasTotp || hasPasskey;
        if (!secondFactorEnrolled) {
          router.replace("/settings/totp-setup");
          return;
        }
        setAuthChecked(true);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  function handleRefresh() {
    // bust 토글로 각 카드 강제 갱신
    setBust((b) => !b);
  }

  function handlePeriodChange(p: AnalyticsPeriod) {
    setPeriod(p);
    setBust(false);
  }

  if (!authChecked) {
    return (
      <div className="flex items-center justify-center h-64 text-admin-muted text-[13px]">
        인증 확인 중...
      </div>
    );
  }

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-lg font-semibold text-admin-fg">분석 대시보드</h1>
          <p className="text-[12px] text-admin-muted mt-0.5">
            코호트 retention · newsletter · feed CTR · AI 사용률 통합 조회
          </p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodSelector value={period} onChange={handlePeriodChange} />
          <button
            type="button"
            onClick={handleRefresh}
            aria-label="데이터 새로고침"
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] border border-admin-border rounded-md text-admin-muted hover:text-admin-fg hover:bg-admin-surface-2 transition-colors"
          >
            <RefreshIcon />
            새로고침
          </button>
        </div>
      </div>

      {/* 카드 그리드 — xl: 2열, mobile: 1열 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CohortRetentionCard period={period} bust={bust} />
        <NewsletterOpenRateCard period={period} bust={bust} />
        <FeedCTRCard period={period} bust={bust} />
        <AIFeaturesUsageCard period={period} bust={bust} />
      </div>
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-3.5 w-3.5"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.389zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
        clipRule="evenodd"
      />
    </svg>
  );
}
