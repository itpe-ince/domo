"use client";

/**
 * useArtistGate — editor-responsive-redesign PDCA (#3, Step 1).
 *
 * Encapsulates two effects from posts/new/page.tsx:
 *   1) Auto-fallback non-artist users from `type=product` to `type=general`.
 *      The PostTypeSelector already blocks switching to product UI, but a user
 *      can still land on `/posts/new?type=product` directly. This effect keeps
 *      the form state honest.
 *   2) Fetch the latest artist application status for non-artist users so the
 *      PostTypeSelector can render the correct disabled-with-hint variant
 *      (pending vs rejected vs none).
 *
 * Both effects are silent on failure — the hint is non-essential and the
 * fallback is defensive. Caller passes `setType` (stable React setter) to let
 * the hook drive the form state.
 *
 * Pattern source: design §4.2, §5.5.
 */
import { useEffect, useState } from "react";

import { fetchMyApplications, type ApiUser } from "@/lib/api";
import type { ArtistApplicationStatus } from "@/components/post-editor/PostTypeSelector";

export interface UseArtistGateOptions {
  me: ApiUser | null;
  type: "general" | "product";
  onTypeChange: (v: "general" | "product") => void;
}

export interface UseArtistGateReturn {
  userRole: ApiUser["role"] | undefined;
  applicationStatus: ArtistApplicationStatus | undefined;
}

export function useArtistGate({
  me,
  type,
  onTypeChange,
}: UseArtistGateOptions): UseArtistGateReturn {
  const [applicationStatus, setApplicationStatus] = useState<
    ArtistApplicationStatus | undefined
  >(undefined);

  // (1) Non-artist auto-fallback to "general" when landing on product.
  useEffect(() => {
    if (
      me &&
      type === "product" &&
      me.role !== "artist" &&
      me.role !== "admin"
    ) {
      onTypeChange("general");
    }
    // onTypeChange is a stable React setter — intentionally omitted to match
    // original page.tsx behavior. Including it would risk re-runs if the
    // caller forgot to memoize.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role, type]);

  // (2) Fetch latest application status — only for non-artist logged-in users.
  useEffect(() => {
    let cancelled = false;
    if (!me || me.role === "artist" || me.role === "admin") {
      setApplicationStatus(undefined);
      return;
    }
    fetchMyApplications()
      .then((apps) => {
        if (cancelled) return;
        if (!apps || apps.length === 0) {
          setApplicationStatus(undefined);
          return;
        }
        const latest = apps[0]?.status;
        if (latest === "pending" || latest === "rejected") {
          setApplicationStatus(latest);
        } else {
          setApplicationStatus(undefined);
        }
      })
      .catch(() => {
        if (!cancelled) setApplicationStatus(undefined);
      });
    return () => {
      cancelled = true;
    };
  }, [me?.id, me?.role]);

  return {
    userRole: me?.role,
    applicationStatus,
  };
}
