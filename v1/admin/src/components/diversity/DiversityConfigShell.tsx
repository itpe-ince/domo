"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, ApiUser, DiversityConfigPatch } from "@/lib/api";
import { useDiversityConfig } from "@/lib/hooks/useDiversityConfig";
import { DiversityConfigForm } from "./DiversityConfigForm";
import { DiversityKPIWidget } from "./DiversityKPIWidget";

function formatUpdatedAt(isoStr: string): string {
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

export function DiversityConfigShell() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const { feedDefault, loading, error, load, patch, patching } = useDiversityConfig();

  useEffect(() => {
    void fetchMe()
      .then((user: ApiUser) => {
        if (user.role !== "admin") {
          router.replace("/");
          return;
        }
        // 2FA 미완료 admin → TOTP 설정 페이지로
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

  useEffect(() => {
    if (authChecked) {
      void load();
    }
  }, [authChecked, load]);

  if (!authChecked || loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-admin-muted text-sm">불러오는 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-8">
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!feedDefault) {
    return (
      <div className="px-4 py-8">
        <div className="rounded-md border border-admin-border bg-admin-surface px-4 py-3 text-sm text-admin-muted">
          feed_default 설정을 찾을 수 없습니다. 백엔드 seed 데이터를 확인하세요.
        </div>
      </div>
    );
  }

  async function handleSave(patchBody: DiversityConfigPatch): Promise<void> {
    await patch("feed_default", patchBody);
  }

  return (
    <div className="px-6 py-8 max-w-6xl">
      {/* 페이지 헤더 */}
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-admin-fg">
          다양성 설정 (Diversity Config)
        </h1>
        <p className="mt-1 text-sm text-admin-muted">
          {feedDefault.name} · 최종 수정: {formatUpdatedAt(feedDefault.updated_at)}
        </p>
      </header>

      {/* 2열 레이아웃 (xl 이상) / 1열 스택 (xl 미만) */}
      <div className="flex flex-col xl:flex-row gap-6 items-start">
        <DiversityConfigForm
          config={feedDefault}
          onSave={handleSave}
        />
        <DiversityKPIWidget config={feedDefault} />
      </div>

      {/* 저장 중 오버레이 표시는 DiversityConfigForm 내부에서 처리하므로
          patching prop은 향후 UX 개선 시 활용 가능 */}
      {patching && (
        <div aria-live="polite" className="sr-only">
          저장 중...
        </div>
      )}
    </div>
  );
}
