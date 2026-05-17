"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  ApiUser,
  ArtistRankingResponse,
  fetchArtistRanking,
  fetchExplore,
  fetchMe,
  fetchMySponsorships,
  fetchMySubscriptions,
  fetchReceivedSponsorships,
  fetchUserProfile,
  fetchUserBio,
  PostView,
  ReceivedSponsorshipView,
  tokenStore,
  UserProfileView,
} from "@/lib/api";
import { LocaleSwitcher, getStoredLocale, LOCALE_CHANGED_EVENT, type SupportedLocale } from "@/components/LocaleSwitcher";
import { TierBadge } from "@/components/artists/TierBadge";
import { PostCard } from "@/components/PostCard";
import { BluebirdButton } from "@/components/BluebirdButton";
import { FollowButton } from "@/components/FollowButton";
import { MessageButton } from "@/components/messaging/MessageButton";
import { WinbackBanner } from "@/components/sponsorships/WinbackBanner";
import { ArtistTierBenefitsView } from "@/components/tier-benefits/ArtistTierBenefitsView";
import { useWinbackBanner } from "@/lib/hooks/useWinbackBanner";
import { useI18n } from "@/i18n";
import { UserMediaCoverage } from "@/components/users/UserMediaCoverage";

function fmt(n: string | number) {
  const v = typeof n === "string" ? Number(n) : n;
  return `₩ ${Math.round(v).toLocaleString()}`;
}

export default function UserProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t } = useI18n();
  const [profile, setProfile] = useState<UserProfileView | null>(null);
  const [posts, setPosts] = useState<PostView[]>([]);
  const [sponsorships, setSponsorships] = useState<ReceivedSponsorshipView[]>(
    []
  );
  // C-3: locale-aware bio
  const [currentLocale, setCurrentLocale] = useState<SupportedLocale>("ko");
  const [localeBio, setLocaleBio] = useState<string | null>(null);
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // B-5: winback banner state — has current user previously sponsored this artist?
  const [hasPastSponsorship, setHasPastSponsorship] = useState(false);
  const [hasActiveSubscription, setHasActiveSubscription] = useState(false);

  // A-6: artist index ranking badge
  const [artistRanking, setArtistRanking] = useState<ArtistRankingResponse | null>(null);

  useEffect(() => {
    const stored = getStoredLocale();
    setCurrentLocale(stored);
    void load();
    // C-3: react to locale switcher changes
    function onLocaleChanged(e: Event) {
      const locale = (e as CustomEvent<SupportedLocale>).detail;
      setCurrentLocale(locale);
      void loadLocaleBio(locale);
    }
    window.addEventListener(LOCALE_CHANGED_EVENT, onLocaleChanged);
    return () => window.removeEventListener(LOCALE_CHANGED_EVENT, onLocaleChanged);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function loadLocaleBio(locale: SupportedLocale) {
    try {
      const bioData = await fetchUserBio(id, locale);
      setLocaleBio(bioData.bio);
    } catch {
      setLocaleBio(null);
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const p = await fetchUserProfile(id);
      setProfile(p);
      // C-3: load locale-aware bio (non-blocking)
      const storedLocale = getStoredLocale();
      void fetchUserBio(id, storedLocale)
        .then((bioData) => setLocaleBio(bioData.bio))
        .catch(() => setLocaleBio(null));
      // Posts by this user
      const explore = await fetchExplore({ limit: 30 });
      setPosts(explore.filter((post) => post.author.id === id));
      // Received sponsorships (only meaningful for artists)
      if (p.role === "artist") {
        const sp = await fetchReceivedSponsorships(id, 10);
        setSponsorships(sp);
        // A-6: fetch artist index ranking (non-blocking — badge only)
        try {
          const ranking = await fetchArtistRanking(id);
          setArtistRanking(ranking);
        } catch {
          // non-critical — badge just won't show
        }
      }
      if (tokenStore.get()) {
        try {
          const currentUser = await fetchMe();
          setMe(currentUser);
          // B-5: check if this visitor previously sponsored the artist (winback banner)
          if (p.role === "artist" && currentUser.id !== id) {
            try {
              const [mySponsors, mySubs] = await Promise.all([
                fetchMySponsorships(),
                fetchMySubscriptions(),
              ]);
              const hasSponsor = mySponsors.some((s) => s.artist_id === id);
              const hasSub = mySubs.some((s) => s.artist_id === id);
              const activeNow = mySubs.some(
                (s) =>
                  s.artist_id === id &&
                  (s.status === "active" || s.status === "past_due")
              );
              setHasPastSponsorship(hasSponsor || hasSub);
              setHasActiveSubscription(activeNow);
            } catch {
              // non-critical — banner just won't show
            }
          }
        } catch {
          tokenStore.clear();
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  // B-5: winback banner hook (7-day cooldown localStorage)
  const { shouldShow: showWinback, dismiss: dismissWinback } = useWinbackBanner({
    artistId: id,
    hasPastSponsorship,
    isCurrentlyActive: hasActiveSubscription,
  });

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        로딩 중...
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-3">
        <p className="text-danger">{error ?? "사용자를 찾을 수 없습니다."}</p>
        <Link href="/" className="btn-secondary text-sm">
          홈으로
        </Link>
      </main>
    );
  }

  const totalBluebird = sponsorships.reduce(
    (acc, s) => acc + s.bluebird_count,
    0
  );

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8" aria-label={`@${profile.display_name}`}>
      <Link
        href="/"
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← {t("nav.home")}
      </Link>

      {/* B-5: Win-back banner — shown to past supporters who churned (7d cooldown) */}
      {showWinback && profile.role === "artist" && me && me.id !== profile.id && (
        <div className="mb-6">
          <WinbackBanner
            artistId={profile.id}
            artistName={profile.display_name}
            onDismiss={dismissWinback}
            onSuccess={() => {
              // Reload subscription state after resubscribe
              setHasActiveSubscription(true);
            }}
          />
        </div>
      )}

      <header className="card p-6 mb-8" aria-label={`${t("common.profile")}: @${profile.display_name}`}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-20 h-20 rounded-full bg-surface-hover flex items-center justify-center text-3xl">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={`@${profile.display_name} profile photo`}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                "👤"
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold">@{profile.display_name}</h1>
                {profile.role === "artist" && (
                  <span className="badge-primary">✓ Artist</span>
                )}
                {profile.role === "admin" && (
                  <span className="badge-primary">Admin</span>
                )}
              </div>
              {profile.country_code && (
                <div className="text-text-muted text-sm mt-1">
                  📍 {profile.country_code}
                </div>
              )}

              {/* A-6: Artist ranking badge */}
              {profile.role === "artist" && artistRanking && (
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className="text-xs font-semibold text-text-muted">
                    {t("artist.index.badge.globalRank").replace("{{rank}}", String(artistRanking.rank))}
                  </span>
                  <TierBadge tier={artistRanking.tier_badge} />
                  <span
                    className="text-xs text-text-muted cursor-help underline decoration-dotted"
                    title={t("artist.index.badge.whyTooltip")}
                  >
                    {t("artist.index.badge.whyLabel")}
                  </span>
                </div>
              )}
              <div className="flex gap-4 mt-3 text-sm">
                <span>
                  <strong>{profile.follower_count}</strong>{" "}
                  <span className="text-text-muted">팔로워</span>
                </span>
                <span>
                  <strong>{profile.following_count}</strong>{" "}
                  <span className="text-text-muted">팔로잉</span>
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-2 items-end">
            {/* 팔로우 버튼 — 본인 프로필이 아닐 때 항상 표시 (self-guard는 FollowButton 내부에서도 처리) */}
            <FollowButton userId={profile.id} />
            {/* 메시지 버튼 — 본인 프로필이 아닐 때 표시 (self-guard는 MessageButton 내부) */}
            <MessageButton userId={profile.id} size="sm" />
            {/* Blue Bird 후원 버튼 — 다른 작가 프로필에서만 표시 */}
            {profile.role === "artist" && me?.id !== profile.id && (
              <BluebirdButton
                artistId={profile.id}
                artistName={profile.display_name}
              />
            )}
            <Link
              href={`/users/${id}/series`}
              className="btn-secondary text-sm"
            >
              {t("post.series.viewAll")}
            </Link>
            {me?.id === profile.id && (
              <Link href="/orders" className="btn-secondary text-sm">
                내 주문
              </Link>
            )}
          </div>
        </div>

        {/* C-3: Locale-aware bio display */}
        {(localeBio ?? profile.bio) && (
          <div className="mt-4">
            <p className="text-text-secondary text-sm whitespace-pre-wrap">
              {localeBio ?? profile.bio}
            </p>
          </div>
        )}

        {profile.artist_profile && (
          <div className="mt-6 pt-6 border-t border-border space-y-2 text-sm">
            {profile.artist_profile.school && (
              <div>
                <span className="text-text-muted">학교: </span>
                {profile.artist_profile.school}
              </div>
            )}
            {profile.artist_profile.statement && (
              <div className="text-text-secondary whitespace-pre-wrap">
                {profile.artist_profile.statement}
              </div>
            )}
            <div className="text-text-muted text-xs">
              뱃지: {profile.artist_profile.badge_level}
            </div>
          </div>
        )}
      </header>

      {/* B-4: Artist tier benefits */}
      {profile.role === "artist" && (
        <section className="mb-8">
          <ArtistTierBenefitsView artistId={profile.id} collapsible />
        </section>
      )}

      {/* Received sponsorships (artists only) */}
      {profile.role === "artist" && (
        <section className="mb-8" aria-label="Received sponsorships">
          <h2 className="text-lg font-semibold mb-4">
            <span aria-hidden="true">🕊</span> {t("sponsorship.received") || "받은 후원"}
            {totalBluebird > 0 && (
              <span className="text-primary text-sm ml-2">
                총 {totalBluebird} 블루버드
              </span>
            )}
          </h2>
          {sponsorships.length === 0 ? (
            <div className="card p-6 text-center text-text-muted text-sm">
              아직 받은 후원이 없습니다.
            </div>
          ) : (
            <ul className="space-y-2">
              {sponsorships.map((s) => (
                <li
                  key={s.id}
                  className="card p-4 flex items-start justify-between"
                >
                  <div className="text-sm">
                    <div className="text-text-primary">
                      {s.is_anonymous ? (
                        <span className="text-text-muted">익명 후원자</span>
                      ) : s.sponsor_id ? (
                        <Link
                          href={`/users/${s.sponsor_id}`}
                          className="text-primary hover:underline"
                        >
                          @{s.sponsor_id.slice(0, 8)}
                        </Link>
                      ) : (
                        <span className="text-text-muted">감춰진 후원자</span>
                      )}
                      {" · "}
                      <span className="text-primary font-medium">
                        🕊 {s.bluebird_count}
                      </span>
                    </div>
                    {s.message && (
                      <div className="text-text-secondary text-xs mt-1">
                        "{s.message}"
                      </div>
                    )}
                    <div className="text-text-muted text-xs mt-1">
                      {new Date(s.created_at).toLocaleString("ko-KR")}
                      {s.visibility !== "public" && (
                        <span className="ml-2">· {s.visibility}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-text-secondary text-xs">
                    {fmt(s.amount)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* C-4: Media coverage section — artist profile only, graceful degrade */}
      {profile.role === "artist" && (
        <section className="mb-8">
          <UserMediaCoverage artistId={profile.id} locale={currentLocale} limit={5} />
        </section>
      )}

      {/* Posts by this user */}
      <section aria-label={`${t("post.series.viewAll") || "작품"} (${posts.length})`}>
        <h2 className="text-lg font-semibold mb-4">
          {t("post.series.viewAll") || "작품"} ({posts.length})
        </h2>
        {posts.length === 0 ? (
          <div className="card p-6 text-center text-text-muted text-sm">
            아직 작품이 없습니다.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {posts.map((p) => (
              <PostCard key={p.id} post={p} source="profile" />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
