"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, ApiUser } from "@/lib/api";
import { FeaturedArtistQueue } from "./FeaturedArtistQueue";

export function FeaturedArtistQueueShell() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    void fetchMe()
      .then((user: ApiUser) => {
        if (user.role !== "admin") {
          router.replace("/");
          return;
        }
        setAuthChecked(true);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  if (!authChecked) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-admin-muted text-sm">로딩 중...</div>
      </div>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-admin-fg">Featured Artist 검수</h1>
        <p className="text-admin-muted text-sm mt-1">주간 자동 선정 후보</p>
      </div>
      <FeaturedArtistQueue />
    </main>
  );
}
