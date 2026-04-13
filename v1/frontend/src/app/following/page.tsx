"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchFollowingFeed, PostView } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { FeedItem, FeedSkeleton } from "../feed/page";

export default function FollowingPage() {
  const { me, loading: meLoading } = useMe();
  const [posts, setPosts] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      setLoading(false);
      return;
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPosts(await fetchFollowingFeed(20));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">팔로잉</h1>
        <p className="text-xs text-text-muted mt-0.5">
          팔로우한 작가의 최신 작품만 보여드려요.
        </p>
      </div>

      {!me && !meLoading ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          <p>로그인 후 이용할 수 있습니다.</p>
          <p className="text-xs mt-2">
            좌측 사이드바의 로그인 버튼을 눌러주세요.
          </p>
        </div>
      ) : error ? (
        <div className="mx-4 mt-4 card border-danger p-4 text-danger text-sm">
          {error}
        </div>
      ) : loading ? (
        <FeedSkeleton />
      ) : posts.length === 0 ? (
        <div className="card p-8 m-4 text-center">
          <div className="text-4xl mb-3">🕊</div>
          <h2 className="text-lg font-bold mb-2">
            아직 팔로우한 작가가 없어요
          </h2>
          <p className="text-sm text-text-muted mb-4">
            탐색에서 마음에 드는 작가를 찾아 팔로우해보세요.
          </p>
          <Link
            href="/explore"
            className="inline-block bg-primary text-background hover:bg-primary-hover rounded-full font-bold px-6 py-2.5 transition-colors"
          >
            작가 둘러보기
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {posts.map((post) => (
            <FeedItem key={post.id} post={post} />
          ))}
        </div>
      )}
    </main>
  );
}
