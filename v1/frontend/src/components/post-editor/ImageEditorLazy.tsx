"use client";

/**
 * ImageEditorLazy — SSR-safe wrapper for ImageEditor.
 *
 * Konva (and react-konva) require browser globals (window, HTMLCanvasElement)
 * and cannot run during Next.js SSR. dynamic({ ssr: false }) ensures the
 * actual ImageEditor chunk only executes in the browser.
 *
 * The loading fallback is null because the modal is only mounted when
 * editingMediaId is set — there is no layout to shift while waiting for
 * the lazy chunk.
 *
 * All callers must import from this file, never from ImageEditor directly.
 */

import dynamic from "next/dynamic";
import type { ImageEditorProps } from "./ImageEditor";

export const ImageEditorLazy = dynamic<ImageEditorProps>(
  () => import("./ImageEditor").then((m) => ({ default: m.ImageEditor })),
  {
    ssr: false,
    loading: () => null,
  }
);
