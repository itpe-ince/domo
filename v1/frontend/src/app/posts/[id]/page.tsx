"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import { BluebirdModal } from "@/components/BluebirdModal";
import { ReportModal } from "@/components/ReportModal";
import {
  ApiClientError,
  ApiUser,
  AuctionView,
  buyNow,
  CommentView,
  PostView,
  createComment,
  fetchAuctions,
  fetchComments,
  fetchMe,
  fetchPost,
  likePost,
  tokenStore,
  unlikePost,
} from "@/lib/api";

export default function PostDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [post, setPost] = useState<PostView | null>(null);
  const [comments, setComments] = useState<CommentView[]>([]);
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [liked, setLiked] = useState(false);
  const [activeMediaIdx, setActiveMediaIdx] = useState(0);
  const [showBluebird, setShowBluebird] = useState(false);
  const [auction, setAuction] = useState<AuctionView | null>(null);
  const [buyingNow, setBuyingNow] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const router = useRouter();

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, c] = await Promise.all([fetchPost(id), fetchComments(id)]);
      setPost(p);
      setComments(c);
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
          setMe(await fetchMe());
        } catch {
          tokenStore.clear();
        }
      }
    } catch (e) {
      if (e instanceof ApiClientError && e.code === "NOT_FOUND") {
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
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        로딩 중...
      </main>
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

  return (
    <main className="min-h-screen px-6 py-8 max-w-6xl mx-auto">
      <Link
        href="/"
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← 피드로 돌아가기
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-8">
        {/* Media */}
        <section>
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
            <div className="flex gap-2 mt-3">
              {post.media.map((m, i) => (
                <button
                  key={m.id}
                  onClick={() => setActiveMediaIdx(i)}
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
        <section className="space-y-6">
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
                  <dt className="text-text-muted">매체</dt>
                  <dd>{product.medium}</dd>
                </>
              )}
              {product.dimensions && (
                <>
                  <dt className="text-text-muted">크기</dt>
                  <dd>{product.dimensions}</dd>
                </>
              )}
              {product.year && (
                <>
                  <dt className="text-text-muted">연도</dt>
                  <dd>{product.year}</dd>
                </>
              )}
              {product.buy_now_price && (
                <>
                  <dt className="text-text-muted">즉시구매가</dt>
                  <dd className="text-primary font-medium">
                    ₩ {Number(product.buy_now_price).toLocaleString()}
                  </dd>
                </>
              )}
            </dl>
          )}

          {/* CTA */}
          <div className="space-y-2">
            <button
              onClick={handleLike}
              className={`w-full text-sm ${
                liked ? "btn-secondary" : "btn-ghost"
              }`}
            >
              ♥ {post.like_count} · {liked ? "좋아요 취소" : "좋아요"}
            </button>

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
                  : `💳 즉시구매 ₩${
                      product.buy_now_price
                        ? Number(product.buy_now_price).toLocaleString()
                        : "—"
                    }`}
              </button>
            )}
            {isProduct && product?.is_sold && (
              <div className="card border-text-muted p-3 text-center text-text-muted text-sm">
                판매 완료
              </div>
            )}
            {isProduct && product?.is_auction && auction && (
              <Link
                href={`/auctions/${auction.id}`}
                className="btn-secondary w-full text-sm text-center block"
              >
                🔨 경매 입찰 — 현재 ₩
                {Math.round(Number(auction.current_price)).toLocaleString()}
              </Link>
            )}
            {isProduct && product?.is_auction && !auction && (
              <button className="btn-secondary w-full text-sm" disabled>
                🔨 경매 준비 중
              </button>
            )}
          </div>

          {/* Comments */}
          <section>
            <h3 className="font-semibold mb-3">
              댓글 {post.comment_count}
            </h3>

            {me && (
              <div className="card p-3 mb-4">
                <textarea
                  value={commentDraft}
                  onChange={(e) => setCommentDraft(e.target.value)}
                  rows={2}
                  placeholder="댓글을 남겨보세요"
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
                      <span className="text-text-muted text-xs">
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
