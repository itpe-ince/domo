"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getMySignature,
  uploadMySignature,
  deleteMySignature,
} from "@/lib/api";

export interface UseSignatureReturn {
  /** Current signature URL, or null if user hasn't uploaded one. */
  signatureUrl: string | null;
  /** True while the initial GET is in flight. */
  loading: boolean;
  /** True while a POST or DELETE is in flight. */
  mutating: boolean;
  /** Last error message (i18n key or human-readable), null when none. */
  error: string | null;
  /**
   * Upload a new signature. Returns the new URL on success, throws on
   * fatal error so the caller can present a localized message. The hook
   * also updates `error` for components that read it directly.
   */
  upload: (file: File) => Promise<string>;
  /** Delete the current signature (204). */
  remove: () => Promise<void>;
  /** Manually re-fetch (e.g., after Save) — usually not needed. */
  refresh: () => Promise<void>;
}

const SIGNATURE_MAX_BYTES = 2 * 1024 * 1024;
const SIGNATURE_MIME = ["image/png", "image/webp"];

export function useSignature(): UseSignatureReturn {
  const [signatureUrl, setSignatureUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getMySignature();
      setSignatureUrl(r.signature_url);
    } catch (e: unknown) {
      // GET errors are non-fatal — treat as "no signature"
      setSignatureUrl(null);
      const msg = e instanceof Error ? e.message : "fetch_failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function upload(file: File): Promise<string> {
    setError(null);

    // Client-side validation FIRST (avoid pointless network round-trip)
    if (!SIGNATURE_MIME.includes(file.type)) {
      const msg =
        "post.editor.media.studio.image.tool.watermark.signature.unsupportedType";
      setError(msg);
      throw new Error(msg);
    }
    if (file.size > SIGNATURE_MAX_BYTES) {
      const msg =
        "post.editor.media.studio.image.tool.watermark.signature.tooLarge";
      setError(msg);
      throw new Error(msg);
    }

    setMutating(true);
    try {
      const r = await uploadMySignature(file);
      setSignatureUrl(r.signature_url);
      return r.signature_url!; // backend always returns a URL on 200
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "upload_failed";
      // Heuristic: map backend error messages to i18n keys
      const i18nKey = msg.includes("UNSUPPORTED")
        ? "post.editor.media.studio.image.tool.watermark.signature.unsupportedType"
        : msg.includes("TOO_LARGE")
        ? "post.editor.media.studio.image.tool.watermark.signature.tooLarge"
        : "post.editor.media.studio.image.tool.watermark.signature.uploadFailed";
      setError(i18nKey);
      throw new Error(i18nKey);
    } finally {
      setMutating(false);
    }
  }

  async function remove(): Promise<void> {
    setError(null);
    setMutating(true);
    try {
      await deleteMySignature();
      setSignatureUrl(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "delete_failed";
      setError(msg);
      throw new Error(msg);
    } finally {
      setMutating(false);
    }
  }

  return { signatureUrl, loading, mutating, error, upload, remove, refresh };
}
