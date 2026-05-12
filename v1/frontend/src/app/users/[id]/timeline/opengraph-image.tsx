/**
 * /users/[id]/timeline/opengraph-image.tsx — G'-6 Dynamic OG card (A-7 carry-over)
 *
 * Artist timeline OG image (1200×630).
 * Layout:
 *   Top:    artist name + tier badge + ranking
 *   Middle: timeline preview (3 milestone bullets — joined / first post / rank up)
 *   Bottom: Domo logo + "글로벌 신진작가 인덱스" tagline
 *
 * This is the A-7 storytelling-hub carry-over: external shares of the timeline
 * page get a rich preview card on Twitter/Facebook.
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
  countryFlag,
  tierLabel,
  tierColors,
  fetchOgUserProfile,
  fetchOgArtistRanking,
} from "@/lib/og/utils";

export const runtime = "edge";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

function formatDateShort(isoString: string): string {
  try {
    const d = new Date(isoString);
    return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
  } catch {
    return "";
  }
}

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
  const tier = ranking?.tier_badge ?? null;
  const rank = ranking?.rank ?? null;
  const tl = tierLabel(tier);
  const tc = tierColors(tier);
  const avatarUrl = profile?.avatar_url ?? null;

  // Milestone bullets — derived from available profile data
  const milestones: Array<{ icon: string; label: string; date?: string }> = [];

  // Milestone 1: joined (always shown)
  milestones.push({
    icon: "🌱",
    label: "Domo에 합류",
    date: undefined,
  });

  // Milestone 2: has artwork (follower_count > 0 as a proxy, since we don't fetch posts here)
  if ((profile?.follower_count ?? 0) > 0) {
    milestones.push({
      icon: "🎨",
      label: "첫 작품 공개",
    });
  }

  // Milestone 3: ranking
  if (rank !== null) {
    milestones.push({
      icon: tl ? "🏆" : "📈",
      label: tl ? `${tl} 진입` : `글로벌 랭킹 #${rank}`,
    });
  }

  // Fill to 3 milestones if needed
  if (milestones.length < 3) {
    milestones.push({ icon: "🌏", label: "글로벌 커뮤니티 활동 중" });
  }
  const displayMilestones = milestones.slice(0, 3);

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          background: `linear-gradient(160deg, ${OG_BRAND.background} 0%, ${OG_BRAND.surfaceLight} 60%, ${OG_BRAND.surface} 100%)`,
          display: "flex",
          flexDirection: "column",
          fontFamily: "'Noto Sans KR', 'Segoe UI', sans-serif",
          padding: "50px 70px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background accent */}
        <div
          style={{
            position: "absolute",
            bottom: "-80px",
            left: "-80px",
            width: "360px",
            height: "360px",
            borderRadius: "50%",
            background: `radial-gradient(circle, ${OG_BRAND.primary}10 0%, transparent 70%)`,
          }}
        />

        {/* ── TOP: Artist header ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "24px",
            marginBottom: "36px",
          }}
        >
          {/* Avatar */}
          <div
            style={{
              width: "90px",
              height: "90px",
              borderRadius: "50%",
              border: `3px solid ${OG_BRAND.primary}`,
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
                width={90}
                height={90}
                style={{ objectFit: "cover", width: "100%", height: "100%" }}
              />
            ) : (
              <span style={{ fontSize: "40px" }}>🎨</span>
            )}
          </div>

          {/* Name + meta */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              flex: 1,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <span
                style={{
                  color: OG_BRAND.textPrimary,
                  fontSize: "34px",
                  fontWeight: "700",
                  lineHeight: 1,
                }}
              >
                @{name}
              </span>
              {tl && (
                <div
                  style={{
                    background: tc.bg,
                    color: tc.text,
                    fontSize: "15px",
                    fontWeight: "700",
                    padding: "4px 12px",
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {tl}
                </div>
              )}
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              {country && (
                <span style={{ color: OG_BRAND.textSecondary, fontSize: "18px" }}>
                  {flag} {country}
                </span>
              )}
              {rank !== null && (
                <span
                  style={{
                    color: OG_BRAND.primary,
                    fontSize: "18px",
                    fontWeight: "600",
                  }}
                >
                  글로벌 #{rank}
                </span>
              )}
            </div>
          </div>

          {/* 작가 히스토리 label */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: "4px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "14px",
                textTransform: "uppercase",
                letterSpacing: "0.12em",
              }}
            >
              Artist Story
            </span>
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "14px",
                fontWeight: "600",
              }}
            >
              작가 히스토리
            </span>
          </div>
        </div>

        {/* ── MIDDLE: Timeline milestones ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: "0px",
            paddingLeft: "10px",
          }}
        >
          {displayMilestones.map((m, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0px",
                position: "relative",
              }}
            >
              {/* Vertical line (not for last item) */}
              {i < displayMilestones.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    left: "21px",
                    top: "52px",
                    width: "2px",
                    height: "36px",
                    background: `${OG_BRAND.primary}40`,
                  }}
                />
              )}

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "18px",
                  padding: "10px 0",
                }}
              >
                {/* Node circle */}
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "50%",
                    background: `${OG_BRAND.primary}20`,
                    border: `2px solid ${OG_BRAND.primary}60`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "22px",
                    flexShrink: 0,
                  }}
                >
                  {m.icon}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <span
                    style={{
                      color: OG_BRAND.textPrimary,
                      fontSize: "22px",
                      fontWeight: "600",
                      lineHeight: 1.2,
                    }}
                  >
                    {m.label}
                  </span>
                  {m.date && (
                    <span
                      style={{
                        color: OG_BRAND.textMuted,
                        fontSize: "15px",
                      }}
                    >
                      {m.date}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* ── BOTTOM: Domo branding ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: `1px solid ${OG_BRAND.primary}30`,
            paddingTop: "22px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "20px",
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
          <div
            style={{
              color: OG_BRAND.textMuted,
              fontSize: "15px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>🌏</span>
            <span>domo.lounge</span>
          </div>
        </div>
      </div>
    ),
    { ...OG_SIZE }
  );
}
