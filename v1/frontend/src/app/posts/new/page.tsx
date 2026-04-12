"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiClientError,
  ApiUser,
  createPost,
  CreatePostMedia,
  fetchMe,
  loginWithMockEmail,
  registerExternalMedia,
  tokenStore,
  uploadMediaFile,
} from "@/lib/api";

const GENRES = [
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
];

export default function CreatePostPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialType =
    searchParams.get("type") === "general" ? "general" : "product";
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loginEmail, setLoginEmail] = useState("");

  const [type, setType] = useState<"general" | "product">(initialType);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [genre, setGenre] = useState("painting");
  const [tags, setTags] = useState("");
  const [media, setMedia] = useState<CreatePostMedia[]>([]);

  const [externalUrl, setExternalUrl] = useState("");
  const [isMakingVideo, setIsMakingVideo] = useState(false);

  // Product fields
  const [isAuction, setIsAuction] = useState(true);
  const [isBuyNow, setIsBuyNow] = useState(false);
  const [buyNowPrice, setBuyNowPrice] = useState<number | "">("");
  const [dimensions, setDimensions] = useState("");
  const [medium, setMedium] = useState("");
  const [year, setYear] = useState<number | "">(2026);

  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    if (!tokenStore.get()) return;
    try {
      setMe(await fetchMe());
    } catch {
      tokenStore.clear();
    }
  }

  async function handleLogin() {
    try {
      setMe(await loginWithMockEmail(loginEmail.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadMediaFile(file, isMakingVideo);
      setMedia((prev) => [
        ...prev,
        {
          type: uploaded.type,
          url: uploaded.url,
          size_bytes: uploaded.size_bytes,
          is_making_video: uploaded.is_making_video,
        },
      ]);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Upload failed"
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleAddExternal() {
    if (!externalUrl.trim()) return;
    setError(null);
    try {
      const ext = await registerExternalMedia(externalUrl.trim(), isMakingVideo);
      setMedia((prev) => [
        ...prev,
        {
          type: ext.type,
          url: ext.url,
          external_source: ext.external_source,
          external_id: ext.external_id,
          is_making_video: ext.is_making_video,
        },
      ]);
      setExternalUrl("");
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "External register failed"
      );
    }
  }

  function removeMedia(idx: number) {
    setMedia((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleSubmit() {
    setError(null);
    if (type === "product" && me?.role !== "artist" && me?.role !== "admin") {
      setError("상품 포스트는 작가만 작성할 수 있습니다.");
      return;
    }
    setSubmitting(true);
    try {
      const tagList = tags
        .split(/[,\n]/)
        .map((t) => t.trim())
        .filter(Boolean);

      const post = await createPost({
        type,
        title: title || undefined,
        content: content || undefined,
        genre: type === "product" ? genre : undefined,
        tags: tagList.length ? tagList : undefined,
        media,
        product:
          type === "product"
            ? {
                is_auction: isAuction,
                is_buy_now: isBuyNow,
                buy_now_price:
                  isBuyNow && typeof buyNowPrice === "number"
                    ? buyNowPrice
                    : undefined,
                currency: "KRW",
                dimensions: dimensions || undefined,
                medium: medium || undefined,
                year: typeof year === "number" ? year : undefined,
              }
            : undefined,
      });
      router.push(`/posts/${post.id}`);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Create failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 max-w-3xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">New</span>
          <h1 className="text-3xl font-bold mt-3">포스트 작성</h1>
        </div>
        <Link href="/" className="btn-ghost text-sm">
          ← 홈
        </Link>
      </header>

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="email@example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {error && (
        <div className="card border-danger p-3 text-danger text-sm mb-4">
          {error}
        </div>
      )}

      {me && (
        <div className="space-y-6">
          {/* Type toggle */}
          <div>
            <label className="block text-sm text-text-secondary mb-2">
              포스트 종류
            </label>
            <div className="flex bg-surface rounded-full p-1 border border-border w-fit">
              <button
                onClick={() => setType("general")}
                className={`px-5 py-2 rounded-full text-sm transition-colors ${
                  type === "general"
                    ? "bg-primary text-background"
                    : "text-text-secondary"
                }`}
              >
                일반 포스트
              </button>
              <button
                onClick={() => setType("product")}
                className={`px-5 py-2 rounded-full text-sm transition-colors ${
                  type === "product"
                    ? "bg-primary text-background"
                    : "text-text-secondary"
                }`}
              >
                상품 포스트
              </button>
            </div>
            {type === "product" && me.role !== "artist" && me.role !== "admin" && (
              <p className="text-warning text-xs mt-2">
                상품 포스트는 작가 권한이 필요합니다.
              </p>
            )}
          </div>

          {/* Title + content */}
          <div>
            <label className="block text-sm text-text-secondary mb-1">
              제목
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1">
              내용
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none resize-none"
            />
          </div>

          {/* Media uploader */}
          <div>
            <label className="block text-sm text-text-secondary mb-2">
              미디어
            </label>
            <div className="card p-4 space-y-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={isMakingVideo}
                  onChange={(e) => setIsMakingVideo(e.target.checked)}
                  className="accent-primary"
                />
                메이킹/타임랩스 영상 (최대 1GB)
              </label>

              <div>
                <input
                  type="file"
                  accept="image/*,video/*"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void handleFile(f);
                    e.target.value = "";
                  }}
                  disabled={uploading}
                  className="text-sm text-text-secondary"
                />
                {uploading && (
                  <span className="text-text-muted text-xs ml-2">업로드 중...</span>
                )}
              </div>

              <div className="flex gap-2">
                <input
                  type="url"
                  placeholder="YouTube/Vimeo URL"
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  className="flex-1 bg-background border border-border rounded-lg px-3 py-1.5 text-sm focus:border-primary outline-none"
                />
                <button
                  onClick={handleAddExternal}
                  className="btn-secondary text-xs"
                >
                  임베드 추가
                </button>
              </div>

              {media.length > 0 && (
                <ul className="space-y-2 pt-2 border-t border-border">
                  {media.map((m, i) => (
                    <li
                      key={i}
                      className="flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="badge-primary">{m.type}</span>
                        <span className="text-text-secondary truncate max-w-xs">
                          {m.url}
                        </span>
                      </div>
                      <button
                        onClick={() => removeMedia(i)}
                        className="text-danger hover:underline"
                      >
                        제거
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <p className="text-text-muted text-xs mt-2">
              ※ 이미지/영상 포함 시 디지털 아트 판독 큐에 진입합니다 (관리자
              승인 필요).
            </p>
          </div>

          {/* Product fields */}
          {type === "product" && (
            <div className="card p-4 space-y-4">
              <h3 className="font-semibold text-sm">상품 정보</h3>

              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  장르
                </label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                >
                  {GENRES.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    크기
                  </label>
                  <input
                    type="text"
                    placeholder="50x70cm"
                    value={dimensions}
                    onChange={(e) => setDimensions(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    매체
                  </label>
                  <input
                    type="text"
                    placeholder="Oil on canvas"
                    value={medium}
                    onChange={(e) => setMedium(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    제작 연도
                  </label>
                  <input
                    type="number"
                    value={year}
                    onChange={(e) =>
                      setYear(e.target.value ? Number(e.target.value) : "")
                    }
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                  />
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isAuction}
                    onChange={(e) => setIsAuction(e.target.checked)}
                    className="accent-primary"
                  />
                  경매로 판매
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isBuyNow}
                    onChange={(e) => setIsBuyNow(e.target.checked)}
                    className="accent-primary"
                  />
                  즉시구매 가능
                </label>
                {isBuyNow && (
                  <div>
                    <label className="block text-xs text-text-secondary mb-1">
                      즉시구매가 (KRW)
                    </label>
                    <input
                      type="number"
                      value={buyNowPrice}
                      onChange={(e) =>
                        setBuyNowPrice(
                          e.target.value ? Number(e.target.value) : ""
                        )
                      }
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tags */}
          <div>
            <label className="block text-sm text-text-secondary mb-1">
              태그 (쉼표 구분)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="oil, landscape"
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? "작성 중..." : "포스트 작성"}
          </button>
        </div>
      )}
    </main>
  );
}
