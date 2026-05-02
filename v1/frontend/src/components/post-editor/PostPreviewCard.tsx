"use client";

/**
 * PostPreviewCard — editor-responsive-redesign PDCA (#3, Step 2).
 *
 * Renders a non-interactive preview of the in-progress post, visually aligned
 * with the production Feed card. Used inside PreviewPane (desktop only). No
 * click/like/comment handlers — this is read-only.
 *
 * Empty state: shown when there is no title, no body, no media, and no
 * embeds — i.e. the user has not entered anything yet.
 *
 * Pattern source: design §4.1 (PostPreviewCard).
 */

import { useI18n } from "@/i18n";
import { type ApiUser, type CreatePostMedia, type OEmbedData } from "@/lib/api";
import type { PostType } from "@/components/post-editor/PostTypeSelector";

export interface PostPreviewCardProps {
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

function isEmpty(p: PostPreviewCardProps): boolean {
  return (
    !p.title.trim() &&
    !p.content.trim() &&
    p.media.length === 0 &&
    p.embeds.length === 0
  );
}

export function PostPreviewCard(props: PostPreviewCardProps) {
  const { t } = useI18n();
  if (isEmpty(props)) {
    return (
      <div className="card p-6 text-center text-sm text-text-muted">
        {t("post.editor.preview.empty.title")}
        <br />
        {t("post.editor.preview.empty.hint")}
      </div>
    );
  }

  const {
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
  } = props;

  const showProductMeta = type === "product";

  return (
    <article className="card p-4 space-y-3">
      {/* Author row — minimal */}
      {me && (
        <header className="flex items-center gap-2">
          {me.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={me.avatar_url}
              alt=""
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-surface-hover" />
          )}
          <div className="text-sm">
            <div className="font-medium text-text-primary">@{me.display_name}</div>
            <div className="text-xs text-text-muted">{t("post.editor.preview.label")}</div>
          </div>
        </header>
      )}

      {title && <h2 className="text-lg font-bold text-text-primary">{title}</h2>}

      {/* Media thumbnails — square grid up to 4, more uses scroll */}
      {media.length > 0 && (
        <div
          className={
            media.length === 1
              ? "grid grid-cols-1"
              : "grid grid-cols-2 gap-2"
          }
        >
          {media.slice(0, 4).map((m, i) => (
            <div
              key={`${m.url}-${i}`}
              className="relative aspect-square overflow-hidden rounded-lg bg-surface-hover"
            >
              {m.type === "image" ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={m.thumbnail_url ?? m.url}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : m.type === "video" ? (
                <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">
                  {t("post.editor.preview.video")}
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">
                  {t("post.editor.preview.externalEmbed")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* External embeds (oEmbed) summary */}
      {embeds.length > 0 && (
        <div className="space-y-2">
          {embeds.map((e) => (
            <div
              key={e.url}
              className="card p-2 text-xs text-text-secondary border-border"
            >
              <div className="font-medium text-text-primary truncate">
                {e.title || e.url}
              </div>
              {e.author_name && <div className="text-text-muted">{e.author_name}</div>}
            </div>
          ))}
        </div>
      )}

      {content && (
        <p className="text-sm text-text-secondary whitespace-pre-wrap">{content}</p>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((t) => (
            <span
              key={t}
              className="text-xs px-2 py-0.5 rounded-full bg-surface-hover text-text-secondary"
            >
              #{t}
            </span>
          ))}
        </div>
      )}

      {/* Product meta */}
      {showProductMeta && (
        <footer className="border-t border-border pt-3 text-xs text-text-secondary space-y-1">
          {genre && <div>장르: {genre}</div>}
          <div className="flex items-center gap-3">
            {isAuction && <span className="badge-primary">경매</span>}
            {isBuyNow && typeof buyNowPrice === "number" && (
              <span className="text-text-primary">
                즉시구매가: ${buyNowPrice}
              </span>
            )}
          </div>
        </footer>
      )}
    </article>
  );
}
