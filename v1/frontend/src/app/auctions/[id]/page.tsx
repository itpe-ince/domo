"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  ApiClientError,
  ApiUser,
  AuctionView,
  BidView,
  fetchAuction,
  fetchAuctionBids,
  fetchMe,
  fetchPost,
  PostView,
  placeBid,
  tokenStore,
} from "@/lib/api";

const POLL_INTERVAL_MS = 2000;

function fmt(amount: string | number) {
  const n = typeof amount === "string" ? Number(amount) : amount;
  return `₩ ${Math.round(n).toLocaleString()}`;
}

function useCountdown(endAt: string | undefined) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!endAt) return { text: "—", urgent: false, ended: false };
  const diff = new Date(endAt).getTime() - now;
  if (diff <= 0) return { text: "종료됨", urgent: false, ended: true };
  const totalSec = Math.floor(diff / 1000);
  const days = Math.floor(totalSec / 86400);
  const hours = Math.floor((totalSec % 86400) / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;
  let text = "";
  if (days > 0) text = `${days}일 ${hours}시간 ${minutes}분`;
  else if (hours > 0) text = `${hours}시간 ${minutes}분 ${seconds}초`;
  else text = `${minutes}분 ${seconds}초`;
  return { text, urgent: totalSec <= 10, ended: false };
}

export default function AuctionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [auction, setAuction] = useState<AuctionView | null>(null);
  const [bids, setBids] = useState<BidView[]>([]);
  const [post, setPost] = useState<PostView | null>(null);
  const [me, setMe] = useState<ApiUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [bidAmount, setBidAmount] = useState<number | "">("");
  const [bidding, setBidding] = useState(false);
  const [bidFlash, setBidFlash] = useState<string | null>(null);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [a, b] = await Promise.all([
          fetchAuction(id),
          fetchAuctionBids(id),
        ]);
        if (cancelled) return;
        setAuction(a);
        setBids(b);
        const p = await fetchPost(a.product_post_id).catch(() => null);
        if (cancelled) return;
        if (p) setPost(p);
        if (tokenStore.get()) {
          try {
            setMe(await fetchMe());
          } catch {
            tokenStore.clear();
          }
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load auction");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // 2-second polling for live updates (design.md §10 폴링 결정)
  useEffect(() => {
    if (!auction || auction.status === "ended" || auction.status === "cancelled")
      return;
    const t = setInterval(async () => {
      try {
        const [a, b] = await Promise.all([
          fetchAuction(id),
          fetchAuctionBids(id),
        ]);
        setAuction(a);
        setBids(b);
      } catch {
        // ignore polling errors
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(t);
  }, [id, auction?.status]);

  // Sync default bid amount = current_price + min_increment
  useEffect(() => {
    if (auction && bidAmount === "") {
      const next =
        Number(auction.current_price) + Number(auction.min_increment);
      setBidAmount(next);
    }
  }, [auction, bidAmount]);

  const countdown = useCountdown(auction?.end_at);

  async function handleBid() {
    if (!me) {
      setError("로그인이 필요합니다.");
      return;
    }
    if (!auction) return;
    if (typeof bidAmount !== "number") return;
    setBidding(true);
    setError(null);
    setBidFlash(null);
    try {
      const r = await placeBid(auction.id, bidAmount);
      setAuction(r.auction);
      setBids((prev) => [r.bid, ...prev.map((b) => ({ ...b, status: "outbid" as const }))]);
      setBidFlash(`✓ 입찰 성공: ${fmt(r.bid.amount)}`);
      // Bump default bid to next minimum
      setBidAmount(
        Number(r.auction.current_price) + Number(r.auction.min_increment)
      );
    } catch (e) {
      const msg =
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Bid failed";
      setError(msg);
    } finally {
      setBidding(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        로딩 중...
      </main>
    );
  }

  if (!auction) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-3">
        <p className="text-danger">{error ?? "경매를 찾을 수 없습니다."}</p>
        <Link href="/" className="btn-secondary text-sm">
          홈으로
        </Link>
      </main>
    );
  }

  const cover = post?.media[0];
  const isSeller = me?.id === auction.seller_id;
  const isWinner = me?.id === auction.current_winner;
  const isActive = auction.status === "active";
  const minRequired =
    Number(auction.current_price) + Number(auction.min_increment);

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <Link
        href={`/posts/${auction.product_post_id}`}
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← 작품 상세로
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-8">
        {/* Image */}
        <section>
          <div className="card overflow-hidden">
            {cover ? (
              <div className="aspect-[4/5] bg-background overflow-hidden">
                <img
                  src={cover.url}
                  alt={post?.title ?? "auction"}
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="aspect-[4/5] flex items-center justify-center text-text-muted">
                미디어 없음
              </div>
            )}
          </div>
          {post && (
            <div className="mt-4 space-y-2">
              <h2 className="text-xl font-semibold">{post.title}</h2>
              {post.product?.medium && (
                <p className="text-text-secondary text-sm">
                  {post.product.medium} · {post.product.dimensions} ·{" "}
                  {post.product.year}
                </p>
              )}
              <Link
                href={`/users/${auction.seller_id}`}
                className="text-text-secondary text-sm hover:text-primary inline-block"
              >
                @{post.author.display_name}
                {post.author.role === "artist" && (
                  <span className="text-primary text-xs ml-1">✓ Artist</span>
                )}
              </Link>
            </div>
          )}
        </section>

        {/* Bid panel */}
        <section className="space-y-4">
          <div className="card p-6 space-y-4">
            <div>
              <span
                className={`badge-primary ${
                  auction.status === "ended" ? "opacity-60" : ""
                }`}
              >
                {auction.status === "active"
                  ? "진행 중"
                  : auction.status === "ended"
                    ? "종료"
                    : auction.status === "scheduled"
                      ? "예정"
                      : auction.status}
              </span>
            </div>

            <div>
              <div className="text-text-muted text-xs mb-1">현재 입찰가</div>
              <div className="text-3xl font-bold text-primary">
                {fmt(auction.current_price)}
              </div>
              <div className="text-text-muted text-xs mt-1">
                시작가 {fmt(auction.start_price)} · 입찰 단위{" "}
                {fmt(auction.min_increment)}
              </div>
            </div>

            <div>
              <div className="text-text-muted text-xs mb-1">남은 시간</div>
              <div
                className={`text-2xl font-mono ${
                  countdown.urgent ? "text-danger animate-pulse" : ""
                }`}
              >
                {countdown.text}
              </div>
            </div>

            <div className="flex justify-between text-sm text-text-secondary border-t border-border pt-3">
              <span>총 입찰 수</span>
              <span className="text-text-primary font-medium">
                {auction.bid_count}
              </span>
            </div>

            {isWinner && (
              <div className="card border-primary p-3 text-primary text-sm text-center">
                🏆 현재 최고 입찰자입니다
              </div>
            )}
            {isSeller && (
              <div className="card border-warning p-3 text-warning text-sm text-center">
                작가 본인의 경매입니다 (입찰 불가)
              </div>
            )}

            {isActive && !isSeller && me && (
              <div className="space-y-2 pt-2">
                <input
                  type="number"
                  value={bidAmount}
                  min={minRequired}
                  step={Number(auction.min_increment)}
                  onChange={(e) =>
                    setBidAmount(Number(e.target.value) || "")
                  }
                  className="w-full bg-background border border-border rounded-lg px-4 py-3 text-text-primary text-lg focus:border-primary outline-none"
                />
                <div className="text-text-muted text-xs">
                  최소 입찰가: {fmt(minRequired)}
                </div>
                <button
                  onClick={handleBid}
                  disabled={bidding || typeof bidAmount !== "number"}
                  className="btn-primary w-full disabled:opacity-50"
                >
                  {bidding ? "입찰 중..." : `🔨 ${fmt(bidAmount || 0)} 입찰`}
                </button>
              </div>
            )}

            {!me && (
              <div className="text-text-muted text-sm text-center pt-2">
                로그인 후 입찰 가능
              </div>
            )}

            {error && (
              <div className="card border-danger p-3 text-danger text-sm">
                {error}
              </div>
            )}
            {bidFlash && (
              <div className="card border-primary p-3 text-primary text-sm">
                {bidFlash}
              </div>
            )}
          </div>

          {/* Bid history */}
          <div className="card p-4">
            <h3 className="font-semibold mb-3 text-sm">입찰 내역</h3>
            {bids.length === 0 ? (
              <p className="text-text-muted text-sm">아직 입찰이 없습니다.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {bids.slice(0, 10).map((b) => (
                  <li
                    key={b.id}
                    className={`flex items-center justify-between py-1 ${
                      b.status === "active"
                        ? "text-primary font-medium"
                        : "text-text-secondary"
                    }`}
                  >
                    <span className="font-mono">
                      {fmt(b.amount)}
                      {b.status === "active" && " ✦"}
                    </span>
                    <span className="text-text-muted text-xs">
                      {new Date(b.created_at).toLocaleTimeString("ko-KR")}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-text-muted text-xs mt-3 text-right">
              · 2초마다 자동 갱신
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
