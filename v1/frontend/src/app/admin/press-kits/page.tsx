"use client";

/**
 * /admin/press-kits — C-2 press-kit-auto-export
 *
 * Admin-only: press kit PDF generation trigger + history view.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import dynamic from "next/dynamic";
import { useAdminPressKits } from "@/lib/hooks/useAdminPressKits";
import { PressKitsList } from "@/components/admin/PressKitsList";

// PressKitGenerator includes artist-search logic — defer until page mounts
const PressKitGenerator = dynamic(
  () => import("@/components/admin/PressKitGenerator").then((m) => ({ default: m.PressKitGenerator })),
  { ssr: false, loading: () => null }
);

export default function AdminPressKitsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const {
    pressKits,
    loading,
    error,
    generating,
    generateError,
    generate,
    loadHistory,
    currentArtistId,
    setCurrentArtistId,
  } = useAdminPressKits();

  // Auth gate — redirect non-admins
  useEffect(() => {
    fetchMe()
      .then((user) => {
        if (user.role !== "admin") {
          router.replace("/");
        } else {
          setIsAdmin(true);
        }
      })
      .catch(() => {
        router.replace("/login");
      })
      .finally(() => setAuthChecking(false));
  }, [router]);

  if (authChecking || !isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="text-stone-400">{t("common.loading")}</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-stone-900">
            {t("pressKit.pageTitle")}
          </h1>
          <p className="text-stone-500 mt-1 text-sm">
            {t("pressKit.pageSubtitle")}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Generator form */}
          <PressKitGenerator
            onGenerate={async (params) => {
              const kit = await generate(params);
              return kit;
            }}
            generating={generating}
            error={generateError}
            onArtistSelected={(artistId) => {
              setCurrentArtistId(artistId);
            }}
          />

          {/* Right: History */}
          <div className="bg-white rounded-xl border border-stone-200 p-6">
            {currentArtistId ? (
              <PressKitsList
                pressKits={pressKits}
                loading={loading}
                error={error}
              />
            ) : (
              <div className="text-sm text-stone-400 py-8 text-center">
                {t("pressKit.artistSearch")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
