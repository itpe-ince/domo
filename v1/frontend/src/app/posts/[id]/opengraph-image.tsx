/**
 * /posts/[id]/opengraph-image.tsx — G'-6 Dynamic OG card
 *
 * Post detail OG image (1200×630).
 * Layout:
 *   Left 55%: post media thumbnail (or placeholder)
 *   Right 45%: post title + author + tags + Domo branding
 *
 * Distinct from the backend AuctionShareCard (auction-promotion-suite #11):
 *   - Backend share-card: artist-owner-gated, manually generated, 1h cache
 *   - This OG: auto-generated for ALL posts, Twitter/Facebook card standard
 *
 * Runtime: Edge
 */

import { ImageResponse } from "next/og";
import {
  OG_BRAND,
  OG_SIZE,
  OG_CONTENT_TYPE,
  DOMO_BRAND_NAME,
  DOMO_TAGLINE,
  fetchOgPost,
} from "@/lib/og/utils";

export const runtime = "edge";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const post = await fetchOgPost(id);

  const title = post?.title ?? "작품";
  const authorName = post?.author.display_name ?? "작가";
  const isArtist = post?.author.role === "artist";
  const tags = post?.tags?.slice(0, 4) ?? [];
  const mediaUrl = post?.media?.[0]?.thumbnail_url ?? post?.media?.[0]?.url ?? null;

  // Truncate long title
  const displayTitle =
    title.length > 60 ? title.slice(0, 60) + "…" : title;

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          background: OG_BRAND.background,
          display: "flex",
          fontFamily: "'Noto Sans KR', 'Segoe UI', sans-serif",
          overflow: "hidden",
        }}
      >
        {/* Left: media thumbnail */}
        <div
          style={{
            width: "660px",
            height: "630px",
            flexShrink: 0,
            background: OG_BRAND.surface,
            overflow: "hidden",
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {mediaUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={mediaUrl}
              alt={title}
              width={660}
              height={630}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          ) : (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "16px",
                color: OG_BRAND.textMuted,
              }}
            >
              <span style={{ fontSize: "80px" }}>🎨</span>
              <span style={{ fontSize: "18px" }}>Domo Artwork</span>
            </div>
          )}

          {/* Gradient overlay on right edge for blending */}
          <div
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              width: "80px",
              height: "100%",
              background: `linear-gradient(90deg, transparent, ${OG_BRAND.background})`,
            }}
          />
        </div>

        {/* Right: post info */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: "50px 45px 40px",
          }}
        >
          {/* Author line */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.textSecondary,
                fontSize: "18px",
                fontWeight: "600",
              }}
            >
              @{authorName}
            </span>
            {isArtist && (
              <div
                style={{
                  background: `${OG_BRAND.primary}22`,
                  border: `1px solid ${OG_BRAND.primary}55`,
                  borderRadius: "4px",
                  padding: "2px 8px",
                  color: OG_BRAND.primary,
                  fontSize: "13px",
                  fontWeight: "600",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                ✓ Artist
              </div>
            )}
          </div>

          {/* Post title */}
          <div
            style={{
              color: OG_BRAND.textPrimary,
              fontSize: displayTitle.length > 30 ? "32px" : "38px",
              fontWeight: "700",
              lineHeight: 1.3,
              flex: 1,
            }}
          >
            {displayTitle}
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                marginBottom: "28px",
              }}
            >
              {tags.map((tag, i) => (
                <div
                  key={i}
                  style={{
                    background: `${OG_BRAND.surface}`,
                    border: `1px solid ${OG_BRAND.primary}30`,
                    borderRadius: "6px",
                    padding: "4px 12px",
                    color: OG_BRAND.textMuted,
                    fontSize: "15px",
                  }}
                >
                  #{tag}
                </div>
              ))}
            </div>
          )}

          {/* Domo branding */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "3px",
              borderTop: `1px solid ${OG_BRAND.primary}25`,
              paddingTop: "18px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "19px",
                fontWeight: "700",
                letterSpacing: "0.04em",
              }}
            >
              {DOMO_BRAND_NAME}
            </span>
            <span
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "13px",
              }}
            >
              {DOMO_TAGLINE}
            </span>
          </div>
        </div>
      </div>
    ),
    { ...OG_SIZE }
  );
}
