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
          ? "hidden md:block w-96 border-l border-border bg-background overflow-y-auto transition-[width] duration-150"
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
