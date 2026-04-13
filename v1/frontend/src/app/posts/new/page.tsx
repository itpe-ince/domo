"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiClientError,
  CreatePostMedia,
  OEmbedData,
  createPost,
  registerExternalMedia,
  uploadMediaFile,
} from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { LoginModal } from "@/components/LoginModal";
import { MediaToolbar } from "@/components/post-editor/MediaToolbar";
import { MediaPreviewList } from "@/components/post-editor/MediaPreviewList";
import { TagAutocomplete } from "@/components/post-editor/TagAutocomplete";

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
  const { me, loading: meLoading } = useMe();
  const [loginOpen, setLoginOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const tagRef = useRef<HTMLDivElement>(null);

  const [type, setType] = useState<"general" | "product">(initialType);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [genre, setGenre] = useState("painting");
  const [tags, setTags] = useState<string[]>([]);
  const [media, setMedia] = useState<CreatePostMedia[]>([]);
  const [embeds, setEmbeds] = useState<OEmbedData[]>([]);

  const [isMakingVideo, setIsMakingVideo] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [locationName, setLocationName] = useState("");
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);

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
    if (!meLoading && !me) {
      setLoginOpen(true);
    }
  }, [me, meLoading]);

  async function handleFiles(files: FileList) {
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
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
      }
    } catch (e) {
      setError(
        e instanceof ApiClientError ? `${e.code}: ${e.message}` : "업로드 실패"
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleGif(file: File) {
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadMediaFile(file, false);
      setMedia((prev) => [
        ...prev,
        { type: uploaded.type, url: uploaded.url, size_bytes: uploaded.size_bytes },
      ]);
    } catch (e) {
      setError("GIF 업로드 실패");
    } finally {
      setUploading(false);
    }
  }

  function handleEmojiInsert(emoji: string) {
    const ta = textareaRef.current;
    if (!ta) {
      setContent((prev) => prev + emoji);
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const newContent =
      content.substring(0, start) + emoji + content.substring(end);
    setContent(newContent);
    requestAnimationFrame(() => {
      ta.selectionStart = ta.selectionEnd = start + emoji.length;
      ta.focus();
    });
  }

  function handleEmbedAdd(data: OEmbedData) {
    setEmbeds((prev) => [...prev, data]);
    // Also add as external_embed media for backend
    setMedia((prev) => [
      ...prev,
      {
        type: "external_embed" as const,
        url: data.url,
        external_source: data.provider,
      },
    ]);
  }

  async function handleSubmit() {
    setError(null);
    if (type === "product" && me?.role !== "artist" && me?.role !== "admin") {
      setError("상품 포스트는 작가만 작성할 수 있습니다.");
      return;
    }
    setSubmitting(true);
    try {
      const post = await createPost({
        type,
        title: title || undefined,
        content: content || undefined,
        genre: type === "product" ? genre : undefined,
        tags: tags.length ? tags : undefined,
        media,
        scheduled_at: scheduledAt || undefined,
        location_name: locationName || undefined,
        location_lat: locationLat ?? undefined,
        location_lng: locationLng ?? undefined,
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
        e instanceof ApiClientError ? `${e.code}: ${e.message}` : "작성 실패"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 xl:max-w-[680px] border-r border-border">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">등록</h1>
        <button
          onClick={handleSubmit}
          disabled={submitting || !me}
          className="btn-primary text-sm disabled:opacity-50"
        >
          {submitting
            ? "등록 중..."
            : scheduledAt
              ? "예약 등록"
              : "등록"}
        </button>
      </div>

      {!me && !meLoading && (
        <LoginModal
          open={loginOpen}
          onClose={() => {
            setLoginOpen(false);
            if (!me) router.push("/");
          }}
          redirectTo="/posts/new"
        />
      )}

      {error && (
        <div className="mx-4 mt-4 card border-danger p-3 text-danger text-sm">
          {error}
        </div>
      )}

      {me && (
        <div className="p-4 space-y-4">
          {/* Post type toggle */}
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
            <p className="text-warning text-xs">
              상품 포스트는 작가 권한이 필요합니다.
            </p>
          )}

          {/* Title */}
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="제목"
            className="w-full bg-transparent text-xl font-bold text-text-primary placeholder:text-text-muted outline-none border-none"
          />

          {/* Content */}
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="작품에 대한 이야기를 들려주세요..."
            rows={6}
            className="w-full bg-transparent text-text-primary placeholder:text-text-muted outline-none border-none resize-none text-sm leading-relaxed"
          />

          {/* Media Preview */}
          <MediaPreviewList
            media={media}
            embeds={embeds}
            onRemoveMedia={(i) => setMedia((prev) => prev.filter((_, j) => j !== i))}
            onRemoveEmbed={(i) => {
              setEmbeds((prev) => prev.filter((_, j) => j !== i));
              // Also remove corresponding external_embed from media
              const embedUrl = embeds[i]?.url;
              if (embedUrl) {
                setMedia((prev) =>
                  prev.filter((m) => !(m.type === "external_embed" && m.url === embedUrl))
                );
              }
            }}
          />

          {uploading && (
            <div className="text-text-muted text-xs animate-pulse">
              업로드 중...
            </div>
          )}

          {/* Schedule / Location badges */}
          {(scheduledAt || locationName) && (
            <div className="flex flex-wrap gap-2">
              {scheduledAt && (
                <span className="flex items-center gap-1.5 bg-surface rounded-full px-3 py-1 text-xs text-primary">
                  ⏰ {new Date(scheduledAt).toLocaleString("ko-KR")} 예약
                  <button
                    onClick={() => setScheduledAt("")}
                    className="text-text-muted hover:text-danger"
                  >
                    ✕
                  </button>
                </span>
              )}
              {locationName && (
                <span className="flex items-center gap-1.5 bg-surface rounded-full px-3 py-1 text-xs text-primary">
                  📍 {locationName}
                  <button
                    onClick={() => {
                      setLocationName("");
                      setLocationLat(null);
                      setLocationLng(null);
                    }}
                    className="text-text-muted hover:text-danger"
                  >
                    ✕
                  </button>
                </span>
              )}
            </div>
          )}

          {/* Making video checkbox */}
          <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={isMakingVideo}
              onChange={(e) => setIsMakingVideo(e.target.checked)}
              className="accent-primary"
            />
            다음 업로드를 메이킹/타임랩스 영상으로 표시
          </label>

          {/* Media Toolbar */}
          <div className="card">
            <MediaToolbar
              onImageSelect={handleFiles}
              onGifSelect={handleGif}
              onEmojiInsert={handleEmojiInsert}
              onEmbedAdd={handleEmbedAdd}
              onLocationClick={() => {
                // Kakao Maps 미연동 상태에서는 수동 입력
                const name = prompt("장소명을 입력하세요 (예: 서울시립미술관)");
                if (name) {
                  setLocationName(name);
                  setLocationLat(37.5665);
                  setLocationLng(126.978);
                }
              }}
              scheduledAt={scheduledAt}
              onScheduleChange={setScheduledAt}
              onTagFocus={() => tagRef.current?.scrollIntoView({ behavior: "smooth" })}
              disabled={uploading || submitting}
            />
          </div>

          {/* Tags */}
          <div ref={tagRef}>
            <label className="block text-sm text-text-secondary mb-1">태그</label>
            <TagAutocomplete tags={tags} onTagsChange={setTags} />
          </div>

          {/* Product fields */}
          {type === "product" && (
            <div className="card p-4 space-y-4">
              <h3 className="font-semibold text-sm">상품 정보</h3>

              <div>
                <label className="block text-xs text-text-secondary mb-1">장르</label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                >
                  {GENRES.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">크기</label>
                  <input
                    type="text"
                    placeholder="50x70cm"
                    value={dimensions}
                    onChange={(e) => setDimensions(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">매체</label>
                  <input
                    type="text"
                    placeholder="Oil on canvas"
                    value={medium}
                    onChange={(e) => setMedium(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">제작 연도</label>
                  <input
                    type="number"
                    value={year}
                    onChange={(e) => setYear(e.target.value ? Number(e.target.value) : "")}
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
                        setBuyNowPrice(e.target.value ? Number(e.target.value) : "")
                      }
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          <p className="text-text-muted text-xs">
            ※ 이미지/영상 포함 시 디지털 아트 판독 큐에 진입합니다 (관리자 승인 필요).
          </p>
        </div>
      )}
    </main>
  );
}
