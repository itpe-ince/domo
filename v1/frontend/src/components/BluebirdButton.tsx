"use client";

/**
 * BluebirdButton — reusable trigger for the BluebirdModal.
 *
 * Renders a "Blue Bird 후원" button. When clicked, opens the BluebirdModal
 * for the target artist. Integrates at:
 *   - app/users/[id]/page.tsx (artist profile header)
 *   - app/posts/[id]/page.tsx (post detail)
 *   - components/PostCard.tsx (card hover mini-button, optional)
 *
 * Props:
 *   artistId    — UUID of the target artist
 *   artistName  — display name (shown inside the modal)
 *   postId      — optional post UUID (pre-fills post_id in sponsorship)
 *   variant     — 'full' (default) shows icon+label, 'compact' shows icon only
 *   className   — extra Tailwind classes
 */

import { useState } from "react";
import { BluebirdModal } from "./BluebirdModal";
import { useI18n } from "@/i18n";

type Variant = "full" | "compact";
type SponsorMode = "one_time" | "recurring";

interface BluebirdButtonProps {
  artistId: string;
  artistName: string;
  postId?: string;
  variant?: Variant;
  className?: string;
  onSuccess?: (kind: SponsorMode, amount: number) => void;
}

export function BluebirdButton({
  artistId,
  artistName,
  postId,
  variant = "full",
  className = "",
  onSuccess,
}: BluebirdButtonProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label={t("bluebird.button.label")}
        className={`
          inline-flex items-center gap-1.5 rounded-full
          bg-primary/10 border border-primary/30 text-primary
          hover:bg-primary hover:text-background
          transition-colors px-3 py-1.5 text-sm font-medium
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60
          ${className}
        `.trim()}
      >
        <span aria-hidden="true">🕊</span>
        {variant === "full" && (
          <span>{t("bluebird.button.label")}</span>
        )}
      </button>

      {open && (
        <BluebirdModal
          artistId={artistId}
          artistName={artistName}
          postId={postId}
          onClose={() => setOpen(false)}
          onSuccess={(kind, amount) => {
            setOpen(false);
            onSuccess?.(kind, amount);
          }}
        />
      )}
    </>
  );
}
