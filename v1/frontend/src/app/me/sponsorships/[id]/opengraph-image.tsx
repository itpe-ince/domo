/**
 * /me/sponsorships/[id]/opengraph-image.tsx — G'-6 Dynamic OG card (optional)
 *
 * Sponsor success OG image (1200×630).
 * Shared when a supporter wants to celebrate their sponsorship publicly.
 *
 * Layout:
 *   Center: "Blue Bird Sponsor of {{artist}}" hero text
 *   Artist thumbnail + bluebird count + amount
 *   Anonymous handling: hides supporter identity when is_anonymous=true
 *
 * Privacy: anonymous sponsorships show generic "익명 후원자" copy.
 *
 * Runtime: Edge
 *
 * Note: This route returns a fallback card when the sponsorship is not found
 * or is private, to prevent information leakage.
 */

import { ImageResponse } from "next/og";
import {
  OG_BRAND,
  OG_SIZE,
  OG_CONTENT_TYPE,
  DOMO_BRAND_NAME,
  fetchOgSponsorship,
  fetchOgUserProfile,
} from "@/lib/og/utils";

export const runtime = "edge";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

function formatAmount(amount: string, currency: string): string {
  const n = parseFloat(amount);
  if (isNaN(n)) return amount;
  if (currency === "KRW") return `₩${Math.round(n).toLocaleString()}`;
  return `${currency} ${n.toFixed(2)}`;
}

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sponsorship = await fetchOgSponsorship(id);

  // Privacy-safe fallback — never reveal private/anonymous details
  if (!sponsorship) {
    return new ImageResponse(
      (
        <div
          style={{
            width: "1200px",
            height: "630px",
            background: OG_BRAND.background,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "'Noto Sans KR', 'Segoe UI', sans-serif",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <span style={{ fontSize: "80px" }}>🕊</span>
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "28px",
                fontWeight: "700",
              }}
            >
              Blue Bird Sponsorship
            </span>
            <span
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "18px",
              }}
            >
              {DOMO_BRAND_NAME}
            </span>
          </div>
        </div>
      ),
      { ...OG_SIZE }
    );
  }

  const isAnonymous = sponsorship.is_anonymous;
  const bluebirdCount = sponsorship.bluebird_count;
  const amountDisplay = formatAmount(sponsorship.amount, sponsorship.currency);

  // Fetch artist profile for the card
  const artistProfile = await fetchOgUserProfile(sponsorship.artist_id);
  const artistName = artistProfile?.display_name ?? "작가";
  const artistAvatar = artistProfile?.avatar_url ?? null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          background: `linear-gradient(135deg, ${OG_BRAND.background} 0%, ${OG_BRAND.surfaceLight} 100%)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "'Noto Sans KR', 'Segoe UI', sans-serif",
          padding: "60px 80px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background glow */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "600px",
            height: "600px",
            borderRadius: "50%",
            background: `radial-gradient(circle, ${OG_BRAND.primary}12 0%, transparent 70%)`,
          }}
        />

        {/* Bluebird icon */}
        <div
          style={{
            fontSize: "72px",
            marginBottom: "24px",
            display: "flex",
          }}
        >
          🕊
        </div>

        {/* Hero headline */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
            marginBottom: "36px",
            textAlign: "center",
          }}
        >
          {!isAnonymous ? (
            <div
              style={{
                color: OG_BRAND.textPrimary,
                fontSize: "36px",
                fontWeight: "800",
                lineHeight: 1.2,
              }}
            >
              Blue Bird Sponsor of
            </div>
          ) : (
            <div
              style={{
                color: OG_BRAND.textMuted,
                fontSize: "28px",
                fontWeight: "600",
                lineHeight: 1.2,
              }}
            >
              익명 후원자의 Blue Bird
            </div>
          )}

          {/* Artist info */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}
          >
            {artistAvatar && (
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "50%",
                  border: `3px solid ${OG_BRAND.primary}`,
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: OG_BRAND.surface,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={artistAvatar}
                  alt={artistName}
                  width={60}
                  height={60}
                  style={{ objectFit: "cover", width: "100%", height: "100%" }}
                />
              </div>
            )}
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "44px",
                fontWeight: "800",
              }}
            >
              @{artistName}
            </span>
          </div>
        </div>

        {/* Stats row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "40px",
            padding: "20px 40px",
            background: `${OG_BRAND.surface}`,
            borderRadius: "16px",
            border: `1px solid ${OG_BRAND.primary}30`,
            marginBottom: "36px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.primary,
                fontSize: "36px",
                fontWeight: "800",
              }}
            >
              🕊 {bluebirdCount}
            </span>
            <span style={{ color: OG_BRAND.textMuted, fontSize: "15px" }}>
              블루버드
            </span>
          </div>
          <div
            style={{
              width: "1px",
              height: "50px",
              background: `${OG_BRAND.primary}30`,
            }}
          />
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <span
              style={{
                color: OG_BRAND.textPrimary,
                fontSize: "30px",
                fontWeight: "700",
              }}
            >
              {amountDisplay}
            </span>
            <span style={{ color: OG_BRAND.textMuted, fontSize: "15px" }}>
              후원 금액
            </span>
          </div>
        </div>

        {/* Domo branding */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            color: OG_BRAND.textMuted,
            fontSize: "16px",
          }}
        >
          <span style={{ color: OG_BRAND.primary, fontWeight: "700", fontSize: "18px" }}>
            {DOMO_BRAND_NAME}
          </span>
          <span>·</span>
          <span>글로벌 신진작가 후원 플랫폼</span>
        </div>
      </div>
    ),
    { ...OG_SIZE }
  );
}
