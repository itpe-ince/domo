"use client";

/**
 * /me/settings/sponsor-validity — D'-1 carry-over.
 * Artist-only page for configuring sponsor_validity_days.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { SponsorValiditySettings } from "@/components/sponsorships/SponsorValiditySettings";

export default function SponsorValidityPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { me, loading } = useMe();

  useEffect(() => {
    if (!loading && !me) {
      router.push("/");
    }
  }, [me, loading, router]);

  if (loading || !me) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        {t("common.loading")}
      </main>
    );
  }

  if (me.role !== "artist") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-text-secondary">작가 전용 설정입니다.</p>
        <Link href="/" className="btn-secondary text-sm">
          홈으로
        </Link>
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-6 py-8 space-y-6">
      <div>
        <Link href="/me/tier-benefits" className="text-text-secondary text-sm hover:text-primary">
          ← 후원 혜택 설정으로
        </Link>
        <h1 className="text-2xl font-bold mt-4">
          {t("me.settings.sponsorValidity.title")}
        </h1>
        <p className="text-text-muted text-sm mt-1">
          {t("me.settings.sponsorValidity.hint")}
        </p>
      </div>

      <SponsorValiditySettings />
    </main>
  );
}
