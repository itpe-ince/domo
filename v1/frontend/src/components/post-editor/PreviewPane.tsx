"use client";

/**
 * PreviewPane — editor-responsive-redesign PDCA (#3, Step 2).
 *
 * ① layout-improvement: 우측 sticky pane → 편집 영역 하단(single-column)으로 이동.
 * 이제 가로가 아닌 세로 stack 형태로 배치. 호출자(page.tsx)가 `hidden md:block`
 * wrapper 안에서 렌더링하므로 모바일에서는 숨겨짐.
 *
 * isVisible=false 시 높이 0 + overflow-hidden 으로 접힘.
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
          ? // 좌우 split 배치: 상단 border 제거 (편집 영역과 grid gap으로 구분).
            "bg-background overflow-hidden transition-[max-height] duration-200 max-h-[9999px]"
          : "overflow-hidden max-h-0 pointer-events-none transition-[max-height] duration-150"
      }
    >
      <div className="p-4 space-y-3 min-w-0">
        {/* OQ-D-1 = A : visible section header for clarity */}
        <h2 className="text-sm font-semibold text-text-secondary">
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
