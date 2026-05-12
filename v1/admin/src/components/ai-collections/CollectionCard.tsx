"use client";

import { useState } from "react";
import { AICollection } from "@/lib/api";
import { LocalePreviewToggle } from "./LocalePreviewToggle";

type Locale = "ko" | "en" | "ja" | "zh" | "es";

interface CollectionCardProps {
  collection: AICollection;
  onPublish: (id: string) => void;
  onArchive: (id: string) => void;
  onEdit: (collection: AICollection) => void;
  onReject: (id: string) => void;
}

function statusBorderClass(status: AICollection["status"]): string {
  switch (status) {
    case "generating":
      return "border-yellow-500/50";
    case "published":
      return "border-blue-500";
    case "archived":
      return "border-border opacity-60";
    default:
      return "border-admin-border";
  }
}

function StatusBadge({ status }: { status: AICollection["status"] }) {
  if (status === "generating") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-yellow-600 font-medium">
        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        생성 중...
      </span>
    );
  }
  if (status === "published") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-blue-600 font-medium">
        <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414L8 15.414l-4.707-4.707a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        발행됨
      </span>
    );
  }
  if (status === "archived") {
    return (
      <span className="text-xs text-admin-muted font-medium">보관됨</span>
    );
  }
  return (
    <span className="text-xs text-admin-fg-soft font-medium">검수 대기</span>
  );
}

export function CollectionCard({
  collection,
  onPublish,
  onArchive,
  onEdit,
  onReject,
}: CollectionCardProps) {
  const [locale, setLocale] = useState<Locale>("ko");

  const isGenerating = collection.status === "generating";
  const isPublished = collection.status === "published";
  const isArchived = collection.status === "archived";
  const actionsDisabled = isGenerating || isPublished;

  const displayTitle =
    locale === "ko"
      ? collection.title
      : collection.title_translations[locale] ?? null;

  const displayDescription =
    locale === "ko"
      ? collection.description
      : collection.description_translations[locale] ?? null;

  const noTranslation = locale !== "ko" && displayTitle === null;

  // Show at most 10 thumbnails
  const thumbs = collection.posts.slice(0, 10);
  const remaining = collection.post_count - thumbs.length;

  return (
    <div
      className={`border rounded-lg bg-admin-surface p-4 flex flex-col gap-3 ${statusBorderClass(
        collection.status
      )}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-admin-muted">
            #{collection.theme}
          </span>
          <StatusBadge status={collection.status} />
        </div>
        <LocalePreviewToggle value={locale} onChange={setLocale} />
      </div>

      {/* Title & Description */}
      <div>
        <h3 className="text-sm font-semibold text-admin-fg leading-snug">
          {displayTitle ?? (
            <span className="text-admin-muted italic">
              {noTranslation ? "(번역 없음)" : "(제목 없음)"}
            </span>
          )}
        </h3>
        <p className="text-xs text-admin-muted mt-1 line-clamp-2">
          {displayDescription ?? (
            <span className="italic">
              {noTranslation ? "(번역 없음)" : "(설명 없음)"}
            </span>
          )}
        </p>
      </div>

      {/* Thumbnail Grid */}
      {thumbs.length > 0 && (
        <div className="grid grid-cols-5 gap-1">
          {thumbs.map((post, idx) => (
            <div
              key={post.post_id}
              className="relative aspect-square bg-admin-surface-2 rounded overflow-hidden"
            >
              {post.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={post.thumbnail_url}
                  alt=""
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-admin-muted text-[10px]">
                  no img
                </div>
              )}
              {/* Remaining count overlay on last visible thumb */}
              {idx === 9 && remaining > 0 && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-white text-xs font-semibold">
                  +{remaining}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Meta */}
      <div className="text-[11px] text-admin-muted space-y-0.5">
        <div>
          LLM: {collection.llm_model_version ?? "알 수 없음"} &nbsp;|&nbsp;{" "}
          {collection.generated_at
            ? new Date(collection.generated_at).toLocaleString("ko-KR", {
                timeZone: "UTC",
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              }) + " UTC"
            : "-"}
        </div>
        <div>
          cluster_k: {collection.cluster_k ?? "-"} &nbsp;&nbsp; 포스트:{" "}
          {collection.post_count}개
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-admin-border">
        <button
          onClick={() => onEdit(collection)}
          disabled={actionsDisabled}
          className="border border-admin-border text-admin-fg px-3 py-1.5 rounded text-xs disabled:opacity-40 disabled:cursor-not-allowed hover:bg-admin-surface-2 transition-colors"
        >
          편집
        </button>
        <button
          onClick={() => onPublish(collection.id)}
          disabled={actionsDisabled}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-xs disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
        >
          발행
        </button>
        <button
          onClick={() => onArchive(collection.id)}
          disabled={actionsDisabled}
          className="border border-admin-border text-admin-muted px-3 py-1.5 rounded text-xs disabled:opacity-40 disabled:cursor-not-allowed hover:bg-admin-surface-2 transition-colors"
        >
          아카이브
        </button>
        <button
          onClick={() => onReject(collection.id)}
          disabled={isGenerating || isPublished}
          className="text-red-500 hover:text-red-700 px-3 py-1.5 rounded text-xs disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          거부
        </button>
      </div>
    </div>
  );
}
