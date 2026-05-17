"use client";

/**
 * FollowButton — reusable follow/unfollow toggle backed by FollowingContext.
 *
 * Behaviors:
 *  - Optimistic toggle; rolls back on API failure (handled by FollowingContext).
 *  - Hides itself for the current user's own profile (self-follow not allowed).
 *  - When not logged in, opens LoginModal instead of calling the API.
 *  - "Following" state shows "Unfollow" on hover for desktop affordance.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useFollowing } from "@/lib/FollowingContext";
import { LoginModal } from "./LoginModal";

type Size = "sm" | "md";

type FollowButtonProps = {
  userId: string;
  size?: Size;
  className?: string;
  /** Optional callback fired after a successful follow/unfollow. */
  onChange?: (isFollowing: boolean) => void;
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-4 py-2",
};

export function FollowButton({
  userId,
  size = "md",
  className = "",
  onChange,
}: FollowButtonProps) {
  const { t } = useI18n();
  const { me, loading: meLoading } = useMe();
  const { isFollowing, follow, unfollow, ready } = useFollowing();
  const [pending, setPending] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);

  // 본인 자기 자신은 팔로우 불가 → 버튼 미노출
  if (me?.id === userId) return null;

  const followed = isFollowing(userId);
  const disabled = pending || meLoading || (!!me && !ready);

  async function handleClick(e: React.MouseEvent) {
    // 카드 전체가 Link인 영역에 놓이는 경우가 있어 이벤트 전파 차단
    e.preventDefault();
    e.stopPropagation();

    if (!me) {
      setLoginOpen(true);
      return;
    }
    setPending(true);
    try {
      if (followed) {
        await unfollow(userId);
        onChange?.(false);
      } else {
        await follow(userId);
        onChange?.(true);
      }
    } catch {
      // FollowingContext가 롤백 처리 — 사용자에게 별도 토스트는 후속 PDCA
    } finally {
      setPending(false);
    }
  }

  const sizeCls = SIZE_CLASSES[size];

  // 상태별 스타일:
  //  - 미팔로우 → primary 강조
  //  - 팔로잉(hover X) → secondary 톤
  //  - 팔로잉(hover) → danger 톤 + "팔로우 취소" 라벨
  let label: string;
  let aria: string;
  let visualCls: string;

  if (!followed) {
    label = t("common.follow");
    aria = `${t("common.follow")}`;
    visualCls = "btn-primary";
  } else if (hovering) {
    label = t("common.unfollow");
    aria = t("common.unfollow");
    visualCls =
      "border border-danger/40 text-danger bg-danger/5 hover:bg-danger/10 rounded-full font-medium";
  } else {
    label = t("common.following");
    aria = t("common.following");
    visualCls =
      "border border-border text-text-primary bg-surface hover:bg-surface-hover rounded-full font-medium";
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onFocus={() => setHovering(true)}
        onBlur={() => setHovering(false)}
        disabled={disabled}
        aria-pressed={followed}
        aria-label={aria}
        className={`${visualCls} ${sizeCls} disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${className}`}
      >
        {pending ? "..." : label}
      </button>

      <LoginModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
      />
    </>
  );
}
