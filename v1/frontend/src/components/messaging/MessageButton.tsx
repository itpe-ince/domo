"use client";

/**
 * MessageButton — start (or resume) a DM conversation with a target user.
 *
 * Behaviors:
 *  - Hides itself for the current user's own ID (cannot DM self).
 *  - Not logged in → opens LoginModal.
 *  - Click → POST /v1/conversations (idempotent: returns existing if any)
 *           → router.push(`/me/messages/{conv.id}`).
 *  - Loading + error states inline.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { ApiClientError, startConversation } from "@/lib/api";
import { LoginModal } from "../LoginModal";

type Size = "sm" | "md";
type Variant = "primary" | "secondary" | "ghost";

type Props = {
  userId: string;
  size?: Size;
  variant?: Variant;
  className?: string;
  /** Optional override for the button label (defaults to i18n messaging.compose.button). */
  label?: string;
  /** Hide the leading icon (default: shown). */
  hideIcon?: boolean;
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-4 py-2",
};

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost:
    "border border-border text-text-primary bg-surface hover:bg-surface-hover rounded-full font-medium",
};

export function MessageButton({
  userId,
  size = "md",
  variant = "secondary",
  className = "",
  label,
  hideIcon,
}: Props) {
  const router = useRouter();
  const { t } = useI18n();
  const { me } = useMe();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);

  // 본인에게 메시지 X
  if (me?.id === userId) return null;

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!me) {
      setLoginOpen(true);
      return;
    }
    setPending(true);
    setError(null);
    try {
      const conv = await startConversation(userId);
      router.push(`/me/messages/${conv.id}`);
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : t("messaging.compose.failed")
      );
      setPending(false);
    }
  }

  const text = pending
    ? t("messaging.compose.starting")
    : label ?? t("messaging.compose.button");

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        aria-label={text}
        className={`${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center justify-center gap-1.5 ${className}`}
      >
        {!hideIcon && <span aria-hidden="true">✉</span>}
        <span>{text}</span>
      </button>

      {error && (
        <div role="alert" className="text-xs text-danger mt-1">
          {error}
        </div>
      )}

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
