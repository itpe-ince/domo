"use client";

import { GalleryView } from "@/components/GalleryView";
import { useI18n } from "@/i18n";

export default function HomePage() {
  const { t } = useI18n();

  return (
    <main className="flex-1 min-w-0">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">{t("home.title")}</h1>
        <p className="text-xs text-text-muted mt-0.5">{t("home.subtitle")}</p>
      </div>
      <GalleryView />
    </main>
  );
}
