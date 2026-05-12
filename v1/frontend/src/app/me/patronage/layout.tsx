"use client";

/**
 * Patronage dashboard layout — artist-only auth gate.
 *
 * Redirects non-artists and unauthenticated users to the home page.
 * Artist check is client-side via useMe(); the backend also enforces
 * role='artist' on every endpoint (403 ARTIST_ONLY).
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMe } from "@/lib/useMe";

export default function PatronageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { me, loading } = useMe();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!me || me.role !== "artist")) {
      router.replace("/");
    }
  }, [me, loading, router]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!me || me.role !== "artist") return null;

  return <>{children}</>;
}
