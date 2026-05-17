"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { AuctionCountdown } from "@/components/AuctionCountdown";
// CO-1 PR-3: DocentSection을 별도 컴포넌트로 분리 (K-wave1 §1.3 deviation 해소)
import { DocentSection } from "@/components/DocentSection";

// Heavy modals: loaded only when user triggers them
const BluebirdModal = dynamic(
  () => import("@/components/BluebirdModal").then((m) => ({ default: m.BluebirdModal })),
  { ssr: false, loading: () => null }
);
const ReportModal = dynamic(
  () => import("@/components/ReportModal").then((m) => ({ default: m.ReportModal })),
  { ssr: false, loading: () => null }
);
// AuctionShareCard: only shown to auction owners — defer its chunk
const AuctionShareCard = dynamic(
  () => import("@/components/AuctionShareCard").then((m) => ({ default: m.AuctionShareCard })),
  { ssr: false, loading: () => null }
);
import {
  ApiClientError,
  ApiUser,
  AuctionView,
  buyNow,
  CommentView,
  DocentView,
  PostView,
  SponsorshipView,
  SubscriptionView,
  createComment,
  fetchAuctions,
  fetchComments,
  fetchDocent,
  fetchMe,
  fetchMySponsorships,
  fetchMySubscriptions,
  fetchPost,
  likePost,
  tokenStore,
  unlikePost,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { formatPriceCents } from "@/lib/format";

// ─── POST_TIER_RESTRICTED CTA panel — D'-1 carry-over ────────────────────────

interface TierRestrictedPanelProps {
  artistId: string;
  artistName: string;
  onClose: () => void;
}

function TierRestrictedPanel({ artistId, artistName, onClose }: TierRestrictedPanelProps) {
  const { t } = useI18n();
  const [showBluebird, setShowBluebird] = useState(false);
  const [bluebirdMode, setBluebirdMode] = useState<"oneTime" | "subscription">("oneTime");

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-6">
      <div className="card max-w-md w-full p-8 space-y-5 text-center">
        <div className="text-4xl">🔒</div>
        <h2 className="text-xl font-bold">{t("post.detail.tierRestrictedTitle")}</h2>
        <p className="text-text-secondary text-sm">
          {t("post.detail.tierRestrictedHint").replace("{{artistName}}", artistName)}
        </p>

        <div className="space-y-3 pt-2">
          <button
            className="btn-primary w-full text-sm"
            onClick={() => {
              setBluebirdMode("oneTime");
              setShowBluebird(true);
            }}
          >
            🕊 {t("post.detail.tierRestrictedSponsorCta")}
          </button>

          <button
            className="btn-secondary w-full text-sm"
            onClick={() => {
              setBluebirdMode("subscription");
              setShowBluebird(true);
            }}
          >
            📅 {t("post.detail.tierRestrictedSubscribeCta")}
          </button>

          <Link
            href="/me/sponsorships"
            className="block text-text-secondary text-sm hover:text-primary underline"
          >
            {t("post.detail.tierRestrictedHistoryCta")}
          </Link>
        </div>

        <button
          onClick={onClose}
          className="text-text-muted text-xs hover:text-text-secondary"
        >
          ← 뒤로
        </button>
      </div>

      {showBluebird && (
        <BluebirdModal
          artistId={artistId}
          artistName={artistName}
          onClose={() => setShowBluebird(false)}
          onSuccess={() => {
            setShowBluebird(false);
            // Reload post after sponsoring — may now qualify
            window.location.reload();
          }}
        />
      )}
    </div>
  );
}

// CO-1 PR-3: 도슨트 섹션을 @/components/DocentSection으로 분리 완료
// DocentSection은 파일 상단 import에서 가져옴

export default function PostDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t } = useI18n();
  const [post, setPost] = useState<PostView | null>(null);
  const [comments, setComments] = useState<CommentView[]>([]);
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tierRestrictedArtist, setTierRestrictedArtist] = useState<{ id: string; name: string } | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [liked, setLiked] = useState(false);
  const [activeMediaIdx, setActiveMediaIdx] = useState(0);
  const [showBluebird, setShowBluebird] = useState(false);
  const [auction, setAuction] = useState<AuctionView | null>(null);
  const [buyingNow, setBuyingNow] = useState(false);
  const [showReport, setShowReport] = useState(false);
  // K-5 도슨트 상태
  const [docent, setDocent] = useState<DocentView | null>(null);
  // 현재 사용자의 이 작가에 대한 후원 이력/구독 상태 — CTA 위에 요약 노출
  const [mySponsorships, setMySponsorships] = useState<SponsorshipView[]>([]);
  const [mySubscriptions, setMySubscriptions] = useState<SubscriptionView[]>([]);
  const router = useRouter();

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      // K-5: 도슨트를 포스트/댓글과 동시에 로드
      const [p, c] = await Promise.all([fetchPost(id), fetchComments(id)]);
      setPost(p);
      setComments(c);

      // 도슨트 비동기 로드 (실패해도 포스트 노출에 영향 없음)
      fetchDocent(id, navigator.language?.split("-")[0] || "ko")
        .then(setDocent)
        .catch(() => { /* 도슨트 로드 실패 — 섹션 숨김 */ });
      setActiveMediaIdx(0);
      // If product post with auction enabled, fetch the latest active/scheduled auction
      if (p.type === "product" && p.product?.is_auction) {
        try {
          const list = await fetchAuctions({ limit: 50 });
          const match = list.find(
            (a) =>
              a.product_post_id === p.id &&
              (a.status === "active" || a.status === "scheduled" || a.status === "ended")
          );
          if (match) setAuction(match);
        } catch {
          // ignore
        }
      }
      if (tokenStore.get()) {
        try {
          const meData = await fetchMe();
          setMe(meData);
          // 본인 글이 아닌 경우에만 후원 이력 조회 (실패해도 본문 노출에는 영향 없음)
          if (meData.id !== p.author.id) {
            void Promise.all([fetchMySponsorships(), fetchMySubscriptions()])
              .then(([sp, sub]) => {
                setMySponsorships(sp.filter((s) => s.artist_id === p.author.id));
                setMySubscriptions(sub.filter((s) => s.artist_id === p.author.id));
              })
              .catch(() => { /* 조용히 실패 — 섹션만 미노출 */ });
          }
        } catch {
          tokenStore.clear();
        }
      }
    } catch (e) {
      if (e instanceof ApiClientError && e.code === "POST_TIER_RESTRICTED") {
        // D'-1 carry-over: show rich CTA panel with BluebirdModal integration
        // We may have a partial post from fetchPost before the 403; try to extract author.
        // If post is already set in state from a previous load, use that; else use placeholder.
        setTierRestrictedArtist(
          post
            ? { id: post.author.id, name: post.author.display_name }
            : { id: "", name: "이 작가" }
        );
        setError("POST_TIER_RESTRICTED");
      } else if (e instanceof ApiClientError && e.code === "NOT_FOUND") {
        setError("존재하지 않는 포스트입니다.");
      } else {
        setError(e instanceof Error ? e.message : "Failed to load post");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLike() {
    if (!me) {
      setError("로그인이 필요합니다.");
      return;
    }
    if (!post) return;
    try {
      if (liked) {
        const r = await unlikePost(post.id);
        setLiked(false);
        setPost({ ...post, like_count: r.like_count ?? post.like_count - 1 });
      } else {
        const r = await likePost(post.id);
        setLiked(true);
        setPost({ ...post, like_count: r.like_count ?? post.like_count + 1 });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Like failed");
    }
  }

  async function handleSubmitComment() {
    if (!me) {
      setError("로그인이 필요합니다.");
      return;
    }
    if (!commentDraft.trim() || !post) return;
    setPosting(true);
    try {
      const created = await createComment(post.id, commentDraft.trim());
      setComments((prev) => [...prev, created]);
      setCommentDraft("");
      setPost({ ...post, comment_count: post.comment_count + 1 });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comment failed");
    } finally {
      setPosting(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted" aria-busy="true" aria-label={t("common.loading")}>
        {t("common.loading")}
      </main>
    );
  }

  if (error === "POST_TIER_RESTRICTED" && tierRestrictedArtist) {
    return (
      <TierRestrictedPanel
        artistId={tierRestrictedArtist.id}
        artistName={tierRestrictedArtist.name}
        onClose={() => router.push("/")}
      />
    );
  }

  if (error || !post) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-danger">{error ?? "Not found"}</p>
        <Link href="/" className="btn-secondary text-sm">
          홈으로
        </Link>
      </main>
    );
  }

  const cover = post.media[activeMediaIdx];
  const isProduct = post.type === "product";
  const product = post.product;

  // 내 후원 이력 요약 (CTA 위에 노출) — useMySponsorships의 status 필터 정책과 일치
  const activeSub = mySubscriptions.find(
    (s) => s.status === "active" || s.status === "past_due"
  );
  const completedSpons = mySponsorships.filter(
    (s) => s.status === "succeeded" || s.status === "completed"
  );
  const sponsTotalBirds = completedSpons.reduce(
    (acc, s) => acc + s.bluebird_count,
    0
  );
  const sponsTotalCents = completedSpons.reduce(
    (acc, s) => acc + Math.round(parseFloat(s.amount) * 100),
    0
  );
  const sponsCurrency =
    completedSpons[0]?.currency || activeSub?.currency || "KRW";
  const hasMyHistory = !!activeSub || completedSpons.length > 0;

  return (
    <main id="main-content" className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8" aria-label={post.title ?? t("nav.home")}>
      <Link
        href="/"
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← {t("nav.home")}
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-8">
        {/* Media */}
        <section aria-label={t("post.detail.mediaSection") || "Post media"}>
          {cover ? (
            <div className="card overflow-hidden">
              <div className="aspect-[4/5] bg-background overflow-hidden">
                <img
                  src={cover.url}
                  alt={post.title ?? "post"}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          ) : (
            <div className="card p-12 text-text-muted text-center">
              미디어 없음
            </div>
          )}

          {post.media.length > 1 && (
            <div className="flex gap-2 mt-3" role="group" aria-label="Media thumbnails">
              {post.media.map((m, i) => (
                <button
                  key={m.id}
                  onClick={() => setActiveMediaIdx(i)}
                  aria-label={`Media ${i + 1} of ${post.media.length}`}
                  aria-pressed={i === activeMediaIdx}
                  className={`w-16 h-16 rounded-md overflow-hidden border-2 ${
                    i === activeMediaIdx ? "border-primary" : "border-border"
                  }`}
                >
                  <img
                    src={m.thumbnail_url ?? m.url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Info & actions */}
        <section className="space-y-6" aria-label="Post details">
          <div>
            <Link
              href={`/users/${post.author.id}`}
              className="flex items-center gap-2 text-text-secondary hover:text-primary"
            >
              <span className="text-sm">@{post.author.display_name}</span>
              {post.author.role === "artist" && (
                <span className="text-xs text-primary">✓ Artist</span>
              )}
            </Link>

            {post.title && (
              <h1 className="text-3xl font-bold mt-3">{post.title}</h1>
            )}
            {post.content && (
              <p className="text-text-secondary mt-3 whitespace-pre-wrap">
                {post.content}
              </p>
            )}
          </div>

          {isProduct && product && (
            <dl className="card p-4 grid grid-cols-2 gap-3 text-sm">
              {product.medium && (
                <>
                  <dt className="text-text-subtle">매체</dt>
                  <dd>{product.medium}</dd>
                </>
              )}
              {product.dimensions && (
                <>
                  <dt className="text-text-subtle">크기</dt>
                  <dd>{product.dimensions}</dd>
                </>
              )}
              {product.year && (
                <>
                  <dt className="text-text-subtle">연도</dt>
                  <dd>{product.year}</dd>
                </>
              )}
              {product.buy_now_price != null && product.buy_now_price > 0 && (
                <>
                  <dt className="text-text-subtle">즉시구매가</dt>
                  <dd className="text-primary font-medium">
                    {formatPriceCents(product.buy_now_price, product.currency || "KRW")}
                  </dd>
                </>
              )}
            </dl>
          )}

          {/* CTA */}
          <div className="space-y-2">
            <button
              onClick={handleLike}
              aria-label={liked ? t("post.feed.liked") || "좋아요 취소" : t("post.feed.like") || "좋아요"}
              aria-pressed={liked}
              className={`w-full text-sm ${
                liked ? "btn-secondary" : "btn-ghost"
              }`}
            >
              <span aria-hidden="true">♥</span> {post.like_count} · {liked ? t("post.feed.liked") || "좋아요 취소" : t("post.feed.like") || "좋아요"}
            </button>

            {/* 내 후원 이력/구독 상태 요약 — 본인 글 제외, 이력이 있을 때만 노출 */}
            {me && me.id !== post.author.id && hasMyHistory && (
              <Link
                href="/me/sponsorships"
                aria-label={t("post.detail.mySponsorshipStatus.ariaLabel", {
                  artistName: post.author.display_name,
                })}
                className="block card p-3 text-xs space-y-1.5 hover:border-primary transition-colors"
              >
                {activeSub && (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-text-secondary">
                      🔄 {t("post.detail.mySponsorshipStatus.subscribing")}
                    </span>
                    <span className="text-text-primary font-medium">
                      {t("post.detail.mySponsorshipStatus.monthly", {
                        birds: activeSub.monthly_bluebird,
                        amount: formatPriceCents(
                          Math.round(parseFloat(activeSub.monthly_amount) * 100),
                          activeSub.currency
                        ),
                      })}
                    </span>
                  </div>
                )}
                {completedSpons.length > 0 && (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-text-secondary">
                      🕊 {t("post.detail.mySponsorshipStatus.oneTimeCount", {
                        count: completedSpons.length,
                      })}
                    </span>
                    <span className="text-text-primary font-medium">
                      {t("post.detail.mySponsorshipStatus.oneTimeAmount", {
                        birds: sponsTotalBirds,
                        amount: formatPriceCents(sponsTotalCents, sponsCurrency),
                      })}
                    </span>
                  </div>
                )}
                <div className="text-right text-text-muted">
                  {t("post.detail.mySponsorshipStatus.viewDetails")} →
                </div>
              </Link>
            )}

            <button
              className="btn-primary w-full text-sm"
              onClick={() => {
                if (!me) {
                  setError("로그인이 필요합니다.");
                  return;
                }
                if (me.id === post.author.id) {
                  setError("자기 자신은 후원할 수 없습니다.");
                  return;
                }
                setShowBluebird(true);
              }}
            >
              🕊 블루버드 후원
            </button>

            {isProduct && product?.is_buy_now && !product.is_sold && (
              <button
                className="btn-secondary w-full text-sm disabled:opacity-50"
                disabled={buyingNow}
                onClick={async () => {
                  if (!me) {
                    setError("로그인이 필요합니다.");
                    return;
                  }
                  if (me.id === post.author.id) {
                    setError("자기 작품은 구매할 수 없습니다.");
                    return;
                  }
                  setBuyingNow(true);
                  setError(null);
                  try {
                    const r = await buyNow(post.id);
                    router.push(`/orders?new=${r.order.id}`);
                  } catch (e) {
                    setError(
                      e instanceof ApiClientError
                        ? `${e.code}: ${e.message}`
                        : e instanceof Error
                          ? e.message
                          : "Buy-now failed"
                    );
                  } finally {
                    setBuyingNow(false);
                  }
                }}
              >
                {buyingNow
                  ? "처리 중..."
                  : `💳 즉시구매 ${formatPriceCents(product.buy_now_price, product.currency || "KRW")}`}
              </button>
            )}
            {isProduct && product?.is_sold && (
              <div className="card border-text-muted p-3 text-center text-text-muted text-sm">
                판매 완료
              </div>
            )}
            {isProduct && product?.is_auction && auction && (
              <div className="space-y-2">
                <Link
                  href={`/auctions/${auction.id}`}
                  className="btn-secondary w-full text-sm text-center block"
                >
                  🔨 경매 입찰 — 현재 ₩
                  {Math.round(Number(auction.current_price)).toLocaleString()}
                </Link>
                {/* auction-promotion-suite PDCA #11 — F-5: full countdown (always visible while active) */}
                {auction.status === "active" && (
                  <div className="card p-3 flex items-center justify-between gap-2">
                    <AuctionCountdown
                      endAt={auction.end_at}
                      onEnded={() =>
                        setAuction((prev) =>
                          prev ? { ...prev, status: "ended" } : prev
                        )
                      }
                    />
                  </div>
                )}
                {/* Share card — only for auction owner (backend 403s others anyway) */}
                {auction.status === "active" && me?.id === post.author.id && (
                  <AuctionShareCard
                    auctionId={auction.id}
                    isOwner={true}
                    cachedUrl={auction.share_card_url}
                    cachedAt={auction.share_card_generated_at}
                  />
                )}
              </div>
            )}
            {isProduct && product?.is_auction && !auction && (
              <button className="btn-secondary w-full text-sm" disabled>
                🔨 경매 준비 중
              </button>
            )}
          </div>

          {/* K-5 도슨트 섹션 — 댓글 위에 표시 */}
          {docent && <DocentSection docent={docent} />}

          {/* Comments */}
          <section aria-labelledby="comments-heading">
            <h2 id="comments-heading" className="font-semibold mb-3">
              {t("common.comments")} {post.comment_count}
            </h2>

            {post.comments_enabled === false ? (
              <div className="text-text-muted text-sm py-4 text-center border border-border rounded-lg my-4">
                {t("post.feed.indicator.commentsDisabled")}
              </div>
            ) : (
              me && (
                <div className="card p-3 mb-4">
                  <label htmlFor="comment-input" className="sr-only">
                    {t("comments.inputLabel") || "댓글 입력"}
                  </label>
                  <textarea
                    id="comment-input"
                    value={commentDraft}
                    onChange={(e) => setCommentDraft(e.target.value)}
                    rows={2}
                    placeholder="댓글을 남겨보세요"
                    aria-label={t("comments.inputLabel") || "댓글 입력"}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none resize-none"
                  />
                  <div className="flex justify-end mt-2">
                    <button
                      onClick={handleSubmitComment}
                      disabled={posting || !commentDraft.trim()}
                      className="btn-primary text-xs disabled:opacity-50"
                    >
                      {posting ? "작성 중..." : "작성"}
                    </button>
                  </div>
                </div>
              )
            )}

            {comments.length === 0 ? (
              <p className="text-text-muted text-sm">
                첫 댓글을 작성해보세요.
              </p>
            ) : (
              <ul className="space-y-3">
                {comments.map((c) => (
                  <li key={c.id} className="card p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-secondary">
                        @{c.author.display_name}
                      </span>
                      <span className="text-text-subtle text-xs">
                        {new Date(c.created_at).toLocaleString("ko-KR")}
                      </span>
                    </div>
                    <p className="text-text-primary whitespace-pre-wrap">
                      {c.content}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </section>
      </div>

      {/* Report link */}
      {me && me.id !== post.author.id && (
        <div className="text-center mt-12">
          <button
            onClick={() => setShowReport(true)}
            className="text-text-muted text-xs hover:text-danger"
          >
            ⚠ 이 포스트 신고
          </button>
        </div>
      )}

      {showBluebird && (
        <BluebirdModal
          artistId={post.author.id}
          artistName={post.author.display_name}
          postId={post.id}
          onClose={() => setShowBluebird(false)}
          onSuccess={(_kind, count) => {
            setPost({ ...post, bluebird_count: post.bluebird_count + count });
            // 요약 카드 즉시 갱신 — 실패해도 무시 (다음 페이지 로드 시 자연 갱신)
            void Promise.all([fetchMySponsorships(), fetchMySubscriptions()])
              .then(([sp, sub]) => {
                setMySponsorships(sp.filter((s) => s.artist_id === post.author.id));
                setMySubscriptions(sub.filter((s) => s.artist_id === post.author.id));
              })
              .catch(() => { /* 조용히 실패 */ });
            setTimeout(() => setShowBluebird(false), 1500);
          }}
        />
      )}

      {showReport && (
        <ReportModal
          targetType="post"
          targetId={post.id}
          targetLabel={post.title ?? `포스트 ${post.id.slice(0, 8)}`}
          onClose={() => setShowReport(false)}
        />
      )}
    </main>
  );
}
