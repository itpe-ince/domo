"use client";

/**
 * useDraftAutosave — editor-draft-autosave PDCA (#2 sub-PDCA).
 *
 * Dual-layer persistence:
 *   1) localStorage debounced write (default 2s after last input edit)
 *   2) saveToServer() — explicit "임시저장" button → POST /v1/posts/drafts
 *
 * The hook is decoupled from posts/new/page.tsx — it accepts a serializable
 * formState snapshot and a storage key. Caller (page) is responsible for:
 *   - building the formState object on every render
 *   - listening to status / lastSavedAt for UI indicators
 *   - calling clearDraft() after successful publish
 *   - handling DraftRestoreDialog with loadLocalDraft() on mount
 *
 * Q-3 = 2s debounce. Q-5 timestamp comparison uses StoredDraft.savedAt.
 */
import { useEffect, useRef, useState } from "react";

import {
  type CreatePostMedia,
  type DraftPayload,
  type OEmbedData,
  saveDraft,
} from "@/lib/api";

// ─── Form state shape ─────────────────────────────────────────────────────
// 18 fields from posts/new/page.tsx — UI-only state (uploading, error, etc.)
// is excluded.

export type DraftState = {
  type: "general" | "product";
  title: string;
  content: string;
  genre: string;
  tags: string[];
  media: CreatePostMedia[];
  embeds: OEmbedData[];
  isMakingVideo: boolean;
  scheduledAt: string;
  locationName: string;
  locationLat: number | null;
  locationLng: number | null;
  isAuction: boolean;
  isBuyNow: boolean;
  buyNowPrice: number | "";
  dimensions: string;
  medium: string;
  year: number | "";
};

interface StoredDraft {
  state: DraftState;
  savedAt: string; // ISO 8601 — Q-5 timestamp comparison anchor
}

export interface UseDraftAutosaveOptions {
  formState: DraftState;
  /** Storage key — recommend `domo-draft-{userId|guest}-{new|draftId}` */
  storageKey: string;
  /** Debounce window in ms before writing to localStorage. Default 2000. */
  debounceMs?: number;
  /** Existing server draft id when re-opening via `?draft=xxx`. */
  draftId?: string;
  /** When false, hook is a no-op (no localStorage, no server). Default true. */
  enabled?: boolean;
}

export type DraftSaveStatus = "idle" | "saving" | "saved" | "error";

export interface UseDraftAutosaveReturn {
  status: DraftSaveStatus;
  lastSavedAt: Date | null;
  /** Persist current formState to server. Returns the server draft id. */
  saveToServer: () => Promise<string | null>;
  /** Wipe localStorage entry + reset internal id/status. Server draft is NOT
   *  deleted — caller must do that explicitly when appropriate. */
  clearDraft: () => void;
  /** True if a localStorage entry currently exists for this storageKey. */
  hasLocalDraft: boolean;
  /** Read-only loader for restoration UI. Returns null if nothing stored. */
  loadLocalDraft: () => DraftState | null;
  /** Read full StoredDraft (state + savedAt) for timestamp comparison. */
  loadStoredDraft: () => StoredDraft | null;
  /** Discard the localStorage entry without touching server. */
  discardLocalDraft: () => void;
}

// ─── localStorage helpers ─────────────────────────────────────────────────

function writeLocalStorage(key: string, state: DraftState): void {
  if (typeof window === "undefined") return;
  try {
    const payload: StoredDraft = {
      state,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(key, JSON.stringify(payload));
  } catch (e) {
    // QuotaExceededError, private mode, etc. — silent fallback (memory only).
    // eslint-disable-next-line no-console
    console.warn("[useDraftAutosave] localStorage write failed:", e);
  }
}

export function readLocalStorageDraft(key: string): StoredDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as StoredDraft;
  } catch {
    return null;
  }
}

function removeLocalStorage(key: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(key);
  } catch {
    /* silent */
  }
}

// ─── Convert DraftState ↔ Draft API payload ───────────────────────────────

function buildDraftPayload(
  state: DraftState,
  draftId: string | undefined,
  type: "general" | "product"
): DraftPayload {
  const product =
    type === "product"
      ? {
          is_auction: state.isAuction,
          is_buy_now: state.isBuyNow,
          buy_now_price:
            state.isBuyNow && typeof state.buyNowPrice === "number"
              ? state.buyNowPrice
              : null,
          currency: "KRW",
          dimensions: state.dimensions || null,
          medium: state.medium || null,
          year: typeof state.year === "number" ? state.year : null,
        }
      : null;

  return {
    draft_id: draftId,
    type,
    title: state.title || null,
    content: state.content || null,
    genre: type === "product" ? state.genre : null,
    tags: state.tags.length > 0 ? state.tags : null,
    language: "ko",
    media: state.media,
    product,
    scheduled_at: state.scheduledAt || null,
    location_name: state.locationName || null,
    location_lat: state.locationLat,
    location_lng: state.locationLng,
  };
}

// ─── Hook ─────────────────────────────────────────────────────────────────

export function useDraftAutosave({
  formState,
  storageKey,
  debounceMs = 2000,
  draftId,
  enabled = true,
}: UseDraftAutosaveOptions): UseDraftAutosaveReturn {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const formStateRef = useRef(formState);
  const currentDraftIdRef = useRef<string | undefined>(draftId);

  const [status, setStatus] = useState<DraftSaveStatus>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [hasLocalDraft, setHasLocalDraft] = useState<boolean>(() =>
    typeof window !== "undefined"
      ? readLocalStorageDraft(storageKey) !== null
      : false
  );

  // Keep refs in sync (used by beforeunload + saveToServer w/o stale closure)
  useEffect(() => {
    formStateRef.current = formState;
  }, [formState]);

  useEffect(() => {
    currentDraftIdRef.current = draftId;
  }, [draftId]);

  // Debounced localStorage write on formState change
  useEffect(() => {
    if (!enabled) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      writeLocalStorage(storageKey, formStateRef.current);
      setLastSavedAt(new Date());
      setStatus("saved");
      setHasLocalDraft(true);
    }, debounceMs);
    return () => clearTimeout(debounceRef.current);
  }, [formState, storageKey, debounceMs, enabled]);

  // Flush on page exit
  useEffect(() => {
    if (!enabled) return;
    function handleBeforeUnload() {
      clearTimeout(debounceRef.current);
      writeLocalStorage(storageKey, formStateRef.current);
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () =>
      window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [storageKey, enabled]);

  // Cleanup pending timeout on unmount (memory leak guard)
  useEffect(
    () => () => {
      clearTimeout(debounceRef.current);
    },
    []
  );

  async function saveToServer(): Promise<string | null> {
    setStatus("saving");
    try {
      const payload = buildDraftPayload(
        formStateRef.current,
        currentDraftIdRef.current,
        formStateRef.current.type
      );
      const saved = await saveDraft(payload);
      currentDraftIdRef.current = saved.id;
      setLastSavedAt(new Date());
      setStatus("saved");
      return saved.id;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[useDraftAutosave] saveToServer failed:", e);
      setStatus("error");
      return null;
    }
  }

  function clearDraft(): void {
    clearTimeout(debounceRef.current);
    removeLocalStorage(storageKey);
    currentDraftIdRef.current = undefined;
    setStatus("idle");
    setLastSavedAt(null);
    setHasLocalDraft(false);
  }

  function loadLocalDraft(): DraftState | null {
    const stored = readLocalStorageDraft(storageKey);
    return stored ? stored.state : null;
  }

  function loadStoredDraft(): StoredDraft | null {
    return readLocalStorageDraft(storageKey);
  }

  function discardLocalDraft(): void {
    removeLocalStorage(storageKey);
    setHasLocalDraft(false);
  }

  return {
    status,
    lastSavedAt,
    saveToServer,
    clearDraft,
    hasLocalDraft,
    loadLocalDraft,
    loadStoredDraft,
    discardLocalDraft,
  };
}
