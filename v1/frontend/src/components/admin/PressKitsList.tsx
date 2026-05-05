"use client";

/**
 * PressKitsList — C-2 press-kit-auto-export
 *
 * Admin: list of generated press kits for an artist, with download links.
 */

import { useI18n } from "@/i18n";
import type { PressKitOut } from "@/lib/api";

type Props = {
  pressKits: PressKitOut[];
  loading: boolean;
  error: string | null;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function PressKitsList({ pressKits, loading, error }: Props) {
  const { t } = useI18n();

  if (loading) {
    return (
      <div className="text-sm text-stone-500 py-6 text-center">
        {t("common.loading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 py-4">{t("common.error")}</div>
    );
  }

  if (pressKits.length === 0) {
    return (
      <div className="text-sm text-stone-400 py-6 text-center">
        {t("pressKit.noHistory")}
      </div>
    );
  }

  const now = new Date();

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-stone-700">
        {t("pressKit.history")}
      </h3>
      <ul className="space-y-2">
        {pressKits.map((kit) => {
          const expired = new Date(kit.expires_at) < now;
          return (
            <li
              key={kit.id}
              className={`border rounded-lg px-4 py-3 text-sm space-y-1 ${
                expired
                  ? "border-stone-200 bg-stone-50 opacity-60"
                  : "border-amber-200 bg-amber-50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-stone-800 uppercase text-xs tracking-wide">
                  {kit.locale}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    expired
                      ? "bg-stone-200 text-stone-500"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {expired ? "Expired" : "Active"}
                </span>
              </div>
              <div className="flex items-center gap-4 text-stone-500 text-xs">
                <span>
                  {t("pressKit.pages")}: {kit.page_count}
                </span>
                <span>
                  {t("pressKit.fileSize")}: {formatBytes(kit.file_size_bytes)}
                </span>
                <span>
                  {t("pressKit.createdAt")}: {formatDate(kit.created_at)}
                </span>
                <span>
                  {t("pressKit.expiresAt")}: {formatDate(kit.expires_at)}
                </span>
              </div>
              {kit.interview_id && (
                <span className="text-xs text-indigo-600">
                  Interview included
                </span>
              )}
              {!expired && (
                <a
                  href={kit.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-1 text-amber-600 underline font-medium text-xs"
                >
                  {t("pressKit.downloadBtn")}
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
