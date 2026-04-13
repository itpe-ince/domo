"use client";

import { GalleryView } from "@/components/GalleryView";

export default function HomePage() {
  return (
    <main className="flex-1 min-w-0">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">Domo Lounge</h1>
        <p className="text-xs text-text-muted mt-0.5">큐레이션 갤러리</p>
      </div>
      <GalleryView />
    </main>
  );
}
