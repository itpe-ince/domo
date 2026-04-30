"use client";

import Link from "next/link";
import { useI18n } from "@/i18n";
import type { ApiUser } from "@/lib/api";

export type PostType = "general" | "product";

export type ArtistApplicationStatus = "pending" | "approved" | "rejected";

interface PostTypeSelectorProps {
  value: PostType;
  onChange: (value: PostType) => void;
  userRole: ApiUser["role"] | undefined;
  applicationStatus?: ArtistApplicationStatus;
  disabled?: boolean;
}

export function PostTypeSelector({
  value,
  onChange,
  userRole,
  applicationStatus,
  disabled = false,
}: PostTypeSelectorProps) {
  const { t } = useI18n();
  const canCreateProduct = userRole === "artist" || userRole === "admin";

  return (
    <div className="space-y-2">
      <div className="flex bg-surface rounded-full p-1 border border-border w-fit">
        <button
          type="button"
          onClick={() => onChange("general")}
          disabled={disabled}
          className={`px-5 py-2 rounded-full text-sm transition-colors disabled:opacity-60 ${
            value === "general"
              ? "bg-primary text-background"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {t("post.generalPost")}
        </button>
        <button
          type="button"
          onClick={() => canCreateProduct && onChange("product")}
          disabled={disabled || !canCreateProduct}
          aria-disabled={!canCreateProduct}
          title={
            !canCreateProduct ? t("post.type.product.disabledTitle") : undefined
          }
          className={`px-5 py-2 rounded-full text-sm transition-colors ${
            !canCreateProduct
              ? "opacity-60 cursor-not-allowed text-text-muted"
              : value === "product"
                ? "bg-primary text-background"
                : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {t("post.productPost")}
        </button>
      </div>

      {!canCreateProduct && userRole !== undefined && (
        <ProductDisabledHint applicationStatus={applicationStatus} />
      )}
    </div>
  );
}

function ProductDisabledHint({
  applicationStatus,
}: {
  applicationStatus?: ArtistApplicationStatus;
}) {
  const { t } = useI18n();

  if (applicationStatus === "pending") {
    return (
      <p
        role="note"
        className="text-xs text-text-muted flex items-center gap-1.5"
      >
        <span aria-hidden>⏳</span>
        {t("post.type.product.disabledHintPending")}
      </p>
    );
  }

  if (applicationStatus === "rejected") {
    return (
      <p
        role="note"
        className="text-xs text-text-muted flex items-center gap-1.5"
      >
        <span aria-hidden>↻</span>
        {t("post.type.product.disabledHintRejected")}
        {" "}
        <Link
          href="/artists/apply"
          className="text-primary underline hover:text-primary/80"
        >
          {t("post.type.product.applyAgainLink")}
        </Link>
      </p>
    );
  }

  // Default: not an applicant yet (or status unknown)
  return (
    <p
      role="note"
      className="text-xs text-text-muted flex items-center gap-1.5"
    >
      <span aria-hidden>🔒</span>
      {t("post.type.product.disabledHint")}
      {" "}
      <Link
        href="/artists/apply"
        className="text-primary underline hover:text-primary/80"
      >
        {t("post.type.product.applyLink")}
      </Link>
    </p>
  );
}
