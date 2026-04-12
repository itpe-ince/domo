"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  ApiUser,
  fetchExplore,
  fetchMe,
  fetchReceivedSponsorships,
  fetchUserProfile,
  PostView,
  ReceivedSponsorshipView,
  tokenStore,
  UserProfileView,
} from "@/lib/api";
import { PostCard } from "@/components/PostCard";

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
  const [profile, setProfile] = useState<UserProfileView | null>(null);
  const [posts, setPosts] = useState<PostView[]>([]);
  const [sponsorships, setSponsorships] = useState<ReceivedSponsorshipView[]>(
    []
  );
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const p = await fetchUserProfile(id);
      setProfile(p);
      // Posts by this user
      const explore = await fetchExplore({ limit: 30 });
      setPosts(explore.filter((post) => post.author.id === id));
      // Received sponsorships (only meaningful for artists)
      if (p.role === "artist") {
        const sp = await fetchReceivedSponsorships(id, 10);
        setSponsorships(sp);
      }
      if (tokenStore.get()) {
        try {
          setMe(await fetchMe());
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
    <main className="min-h-screen px-6 py-8 max-w-5xl mx-auto">
      <Link
        href="/"
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← 홈
      </Link>

      <header className="card p-6 mb-8">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-20 h-20 rounded-full bg-surface-hover flex items-center justify-center text-3xl">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile.display_name}
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
          {me?.id === profile.id && (
            <Link href="/orders" className="btn-secondary text-sm">
              내 주문
            </Link>
          )}
        </div>

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

      {/* Received sponsorships (artists only) */}
      {profile.role === "artist" && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">
            🕊 받은 후원
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

      {/* Posts by this user */}
      <section>
        <h2 className="text-lg font-semibold mb-4">
          작품 ({posts.length})
        </h2>
        {posts.length === 0 ? (
          <div className="card p-6 text-center text-text-muted text-sm">
            아직 작품이 없습니다.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {posts.map((p) => (
              <PostCard key={p.id} post={p} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
