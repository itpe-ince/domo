"use client";

/**
 * PreviewPane — editor-responsive-redesign PDCA (#3, Step 2).
 *
 * Desktop-only side panel hosting the read-only PostPreviewCard. Always
 * mounted in the DOM (so React state — including the card subtree —
 * survives toggling). When `isVisible` is false the container collapses
 * to `width: 0` and is hidden from assistive tech via `aria-hidden`.
 *
 * Mobile (`< md`): caller is responsible for hiding this pane entirely
 * (e.g. via `hidden md:flex` on the wrapper). The wizard layout has no
 * preview pane.
 *
 * Pattern source: design §3.2 / §4.1 / OQ-2 = C / OQ-D-1 = A / OQ-D-4 = A.
 */

import { useI18n } from "@/i18n";
import { type ApiUser, type CreatePostMedia, type OEmbedData } from "@/lib/api";
import type { PostType } from "@/components/post-editor/PostTypeSelector";
import { PostPreviewCard } from "@/components/post-editor/PostPreviewCard";

export interface PreviewPaneProps {
  isVisible: boolean;
  type: PostType;
  title: string;
  content: string;
  media: CreatePostMedia[];
  embeds: OEmbedData[];
  tags: string[];
  genre: string;
  isAuction: boolean;
  isBuyNow: boolean;
  buyNowPrice: number | "";
  me: ApiUser | null;
}

export function PreviewPane({
  isVisible,
  type,
  title,
  content,
  media,
  embeds,
  tags,
  genre,
  isAuction,
  isBuyNow,
  buyNowPrice,
  me,
}: PreviewPaneProps) {
  const { t } = useI18n();
  return (
    <aside
      id="post-preview-pane"
      role="complementary"
      aria-label={t("post.editor.preview.title")}
      aria-hidden={!isVisible}
      className={
        isVisible
          ? // sticky: 스크롤 시 상단 고정. self-start + max-h-screen 으로 내부 스크롤 허용.
            // border-l 이 스크롤 위치마다 따라 그려져 border 끊김도 해소.
            "hidden md:block md:sticky md:top-0 md:self-start md:max-h-screen w-96 border-l border-border bg-background overflow-y-auto transition-[width] duration-150"
          : "hidden md:block w-0 overflow-hidden opacity-0 pointer-events-none border-l-0 transition-[width] duration-150"
      }
    >
      <div className="p-4 space-y-3 min-w-0">
        {/* OQ-D-1 = A : visible section header for clarity */}
        <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide">
          {t("post.editor.preview.title")}
        </h2>
        <PostPreviewCard
          type={type}
          title={title}
          content={content}
          media={media}
          embeds={embeds}
          tags={tags}
          genre={genre}
          isAuction={isAuction}
          isBuyNow={isBuyNow}
          buyNowPrice={buyNowPrice}
          me={me}
        />
      </div>
    </aside>
  );
}
