/**
 * /users/[id]/opengraph-image.tsx — G'-6 Dynamic OG card
 *
 * Artist profile OG image (1200×630).
 * Layout:
 *   Left 50%: avatar (rounded) + display_name + country flag
 *   Right 50%: tier badge + ranking + follower count + Domo branding
 *
 * Runtime: Edge (fast cold start, free tier)
 * Cache: 5 min (revalidate in fetchOgUserProfile)
 */

import { ImageResponse } from "next/og";
import {
  OG_BRAND,
  OG_SIZE,
  OG_CONTENT_TYPE,
  DOMO_BRAND_NAME,
  DOMO_TAGLINE,
  countryFlag,
  tierLabel,
  tierColors,
  scorePercent,
  fetchOgUserProfile,
  fetchOgArtistRanking,
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

  const [profile, ranking] = await Promise.all([
    fetchOgUserProfile(id),
    fetchOgArtistRanking(id),
  ]);

  const name = profile?.display_name ?? "Unknown Artist";
  const country = profile?.country_code ?? null;
  const flag = countryFlag(country);
  const followers = profile?.follower_count ?? 0;
  const tier = ranking?.tier_badge ?? null;
  const rank = ranking?.rank ?? null;
  const score = ranking?.score ?? 0;
  const pct = scorePercent(score);
  const tc = tierColors(tier);
  const tl = tierLabel(tier);
  const avatarUrl = profile?.avatar_url ?? null;
  const statement = profile?.artist_profile?.statement ?? null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          background: `linear-gradient(135deg, ${OG_BRAND.background} 0%, ${OG_BRAND.surfaceLight} 100%)`,
          display: "flex",
          fontFamily: "'Noto Sans KR', 'Segoe UI', sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background accent circle */}
        <div
          style={{
            position: "absolute",
            top: "-120px",
            right: "-120px",
            width: "480px",
            height: "480px",
            borderRadius: "50%",
            background: `radial-gradient(circle, ${OG_BRAND.primary}18 0%, transparent 70%)`,
          }}
        />

        {/* Left panel — avatar + identity */}
        <div
          style={{
            width: "580px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "60px 50px",
            gap: "20px",
          }}
        >
          {/* Avatar */}
          <div
            style={{
              width: "180px",
              height: "180px",
              borderRadius: "50%",
              border: `4px solid ${OG_BRAND.primary}`,
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: OG_BRAND.surface,
              flexShrink: 0,
            }}
          >
            {avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={avatarUrl}
                alt={name}
                width={180}
                height={180}
                style={{ objectFit: "cover", width: "100%", height: "100%" }}
              />
            ) : (
              <span style={{ fontSize: "80px" }}>🎨</span>
            )}
          </div>

          {/* Name */}
          <div
            style={{
              color: OG_BRAND.textPrimary,
              fontSize: "36px",
              fontWeight: "700",
              textAlign: "center",
              lineHeight: 1.2,
              maxWidth: "460px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            @{name}
          </div>

          {/* Country flag + code */}
          {country && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: OG_BRAND.textSecondary,
                fontSize: "22px",
              }}
            >
              <span>{flag}</span>
              <span>{country}</span>
            </div>
          )}

          {/* Artist badge */}
          {profile?.role === "artist" && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: `${OG_BRAND.primary}22`,
                border: `1px solid ${OG_BRAND.primary}55`,
                borderRadius: "20px",
                padding: "6px 16px",
                color: OG_BRAND.primary,
                fontSize: "16px",
                fontWeight: "600",
              }}
            >
              <span>✓ Artist</span>
            </div>
          )}

          {/* Bio statement snippet */}
          {statement && (
            <div
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "16px",
                textAlign: "center",
                lineHeight: 1.4,
                maxWidth: "420px",
                overflow: "hidden",
                display: "-webkit-box",
              }}
            >
              {statement.length > 80 ? statement.slice(0, 80) + "…" : statement}
            </div>
          )}
        </div>

        {/* Divider */}
        <div
          style={{
            width: "1px",
            background: `${OG_BRAND.primary}30`,
            margin: "60px 0",
          }}
        />

        {/* Right panel — ranking + stats + branding */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "60px 50px",
            gap: "24px",
          }}
        >
          {/* Tier badge */}
          {tl && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                alignSelf: "flex-start",
              }}
            >
              <div
                style={{
                  background: tc.bg,
                  color: tc.text,
                  fontSize: "20px",
                  fontWeight: "800",
                  padding: "8px 20px",
                  borderRadius: "8px",
                  letterSpacing: "0.05em",
                }}
              >
                {tl}
              </div>
            </div>
          )}

          {/* Global rank */}
          {rank !== null && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <div
                style={{
                  color: OG_BRAND.textMuted,
                  fontSize: "16px",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Global Rank
              </div>
              <div
                style={{
                  color: OG_BRAND.primary,
                  fontSize: "52px",
                  fontWeight: "800",
                  lineHeight: 1,
                }}
              >
                #{rank}
              </div>
            </div>
          )}

          {/* Score progress bar */}
          {score > 0 && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  color: OG_BRAND.textMuted,
                  fontSize: "14px",
                }}
              >
                <span>Artist Score</span>
                <span>{score.toFixed(2)}</span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: "8px",
                  background: `${OG_BRAND.surface}`,
                  borderRadius: "4px",
                  overflow: "hidden",
                  display: "flex",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    background: `linear-gradient(90deg, ${OG_BRAND.primaryDark}, ${OG_BRAND.primary})`,
                    borderRadius: "4px",
                  }}
                />
              </div>
            </div>
          )}

          {/* Follower stat */}
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "8px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.textPrimary,
                fontSize: "32px",
                fontWeight: "700",
              }}
            >
              {followers.toLocaleString()}
            </span>
            <span
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "18px",
              }}
            >
              팔로워
            </span>
          </div>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Domo branding footer */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              borderTop: `1px solid ${OG_BRAND.primary}30`,
              paddingTop: "20px",
            }}
          >
            <div
              style={{
                color: OG_BRAND.primary,
                fontSize: "22px",
                fontWeight: "700",
                letterSpacing: "0.05em",
              }}
            >
              {DOMO_BRAND_NAME}
            </div>
            <div
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "14px",
              }}
            >
              {DOMO_TAGLINE}
            </div>
          </div>
        </div>
      </div>
    ),
    { ...OG_SIZE }
  );
}
