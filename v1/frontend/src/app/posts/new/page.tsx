"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import {
  ApiClientError,
  CreatePostMedia,
  OEmbedData,
  createPost,
  deleteDraft,
  getDraft,
  registerExternalMedia,
  uploadMediaFile,
  type Draft,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import {
  readLocalStorageDraft,
  useDraftAutosave,
  type DraftSaveStatus,
  type DraftState,
} from "@/lib/hooks/useDraftAutosave";
import { usePostFormState } from "@/lib/hooks/usePostFormState";
import { useArtistGate } from "@/lib/hooks/useArtistGate";
import { LoginModal } from "@/components/LoginModal";
import {
  DraftRestoreDialog,
  type DraftRestoreSource,
} from "@/components/DraftRestoreDialog";
import { MediaToolbar } from "@/components/post-editor/MediaToolbar";
import { MediaPreviewList } from "@/components/post-editor/MediaPreviewList";
import { PostTypeSelector } from "@/components/post-editor/PostTypeSelector";
import { TagAutocomplete } from "@/components/post-editor/TagAutocomplete";

// Disable prerender — uses useSearchParams() which requires runtime
export const dynamic = "force-dynamic";

const GENRES = [
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
];

export default function CreatePostPage() {
  return (
    <Suspense fallback={<div className="p-8 text-text-muted">로딩 중...</div>}>
      <CreatePostPageInner />
    </Suspense>
  );
}

function CreatePostPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialType =
    searchParams.get("type") === "general" ? "general" : "product";
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [loginOpen, setLoginOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const tagRef = useRef<HTMLDivElement>(null);

  // 18 form-field useStates extracted into usePostFormState hook
  // (editor-responsive-redesign PDCA §4.2). Setters are exported under
  // their original names so existing call sites work unchanged.
  const { formState, setters, resetFromDraft } = usePostFormState({
    initialType,
  });
  const {
    setType,
    setTitle,
    setContent,
    setGenre,
    setTags,
    setMedia,
    setEmbeds,
    setIsMakingVideo,
    setScheduledAt,
    setLocationName,
    setLocationLat,
    setLocationLng,
    setIsAuction,
    setIsBuyNow,
    setBuyNowPrice,
    setDimensions,
    setMedium,
    setYear,
  } = setters;
  const {
    type,
    title,
    content,
    genre,
    tags,
    media,
    embeds,
    isMakingVideo,
    scheduledAt,
    locationName,
    locationLat,
    locationLng,
    isAuction,
    isBuyNow,
    buyNowPrice,
    dimensions,
    medium,
    year,
  } = formState;

  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Artist gate — encapsulates the non-artist auto-fallback effect and the
  // application-status fetch. PostTypeSelector consumes applicationStatus.
  const { applicationStatus } = useArtistGate({
    me: me ?? null,
    type,
    onTypeChange: setType,
  });

  // ─── Draft autosave (editor-draft-autosave PDCA) ────────────────────
  const draftParamRaw = searchParams.get("draft");
  const draftParam = draftParamRaw && draftParamRaw.length > 0 ? draftParamRaw : undefined;
  const [currentDraftId, setCurrentDraftId] = useState<string | undefined>(
    draftParam
  );
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);
  const [serverDraftForRestore, setServerDraftForRestore] =
    useState<DraftRestoreSource | null>(null);
  const [multiTabWarning, setMultiTabWarning] = useState(false);

  useEffect(() => {
    if (!meLoading && !me) {
      setLoginOpen(true);
    }
  }, [me, meLoading]);

  // ─── Draft autosave wiring ──────────────────────────────────────────
  // formState is supplied by usePostFormState (see top of component).
  const storageKey = me
    ? `domo-draft-${me.id}-${draftParam ?? "new"}`
    : "domo-draft-guest-new";
  const {
    status: draftStatus,
    lastSavedAt,
    saveToServer,
    clearDraft,
    discardLocalDraft,
  } = useDraftAutosave({
    formState,
    storageKey,
    debounceMs: 2000,
    draftId: currentDraftId,
    enabled: !meLoading,
  });

  // Restore dialog trigger — runs once on mount when local or server draft exists.
  // (eslint disabled because we intentionally only re-run when storageKey or draftParam changes.)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (meLoading) return;
    let cancelled = false;
    const stored = readLocalStorageDraft(storageKey);

    function open() {
      if (!cancelled) setShowRestoreDialog(true);
    }

    if (draftParam) {
      // Coming back to a server draft via /posts/new?draft=xxx
      getDraft(draftParam)
        .then((d) => {
          if (cancelled) return;
          setServerDraftForRestore({
            state: draftToFormState(d),
            savedAt: d.updated_at,
            id: d.id,
          });
          open();
        })
        .catch(() => {
          // Server draft fetch failed (404/permission) → fall back to local only
          if (!cancelled && stored) open();
        });
    } else if (stored) {
      open();
    }

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meLoading, storageKey, draftParam]);

  function handleRestore(d: DraftState, sourceId?: string) {
    resetFromDraft(d);
    if (sourceId) setCurrentDraftId(sourceId);
    setShowRestoreDialog(false);
  }

  async function handleManualSave() {
    if (!me) return;
    const id = await saveToServer();
    if (id) setCurrentDraftId(id);
  }

  // AC-7: detect multi-tab editing via localStorage `storage` event.
  // When another tab writes the same key, browsers fire `storage` here.
  // Q-5 last-write-wins still protects data; this banner just informs.
  useEffect(() => {
    function handleStorage(e: StorageEvent) {
      if (e.key === storageKey && e.newValue && e.oldValue) {
        setMultiTabWarning(true);
      }
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [storageKey]);

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
    // Defense in depth: PostTypeSelector already prevents non-artist
    // from selecting 'product', and backend api/posts.py:206-210 returns 403.
    // This client-side check stays as a final safety net (e.g. URL ?type=product hijack).
    if (type === "product" && me?.role !== "artist" && me?.role !== "admin") {
      setError(t("post.type.product.errorOnlyArtists"));
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
                currency: "USD",
                dimensions: dimensions || undefined,
                medium: medium || undefined,
                year: typeof year === "number" ? year : undefined,
              }
            : undefined,
        // editor-draft-autosave PDCA Q-4: server deletes the draft atomically
        // in the same transaction as the publish. localStorage cleared below.
        from_draft_id: currentDraftId,
      });
      // Wipe localStorage entry. Server draft is deleted by from_draft_id above;
      // also fire DELETE as a belt-and-suspenders fallback (silent on failure)
      // in case the server didn't process from_draft_id.
      clearDraft();
      if (currentDraftId) {
        try {
          await deleteDraft(currentDraftId);
        } catch {
          /* silent — already deleted by from_draft_id path */
        }
      }
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
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      {/* Draft restore dialog — editor-draft-autosave PDCA */}
      <DraftRestoreDialog
        open={showRestoreDialog}
        localDraft={(() => {
          const stored = readLocalStorageDraft(storageKey);
          return stored
            ? { state: stored.state, savedAt: stored.savedAt }
            : null;
        })()}
        serverDraft={serverDraftForRestore}
        onRestore={handleRestore}
        onDiscard={() => {
          discardLocalDraft();
          setShowRestoreDialog(false);
        }}
        onDiscardAll={async () => {
          discardLocalDraft();
          if (serverDraftForRestore?.id) {
            try {
              await deleteDraft(serverDraftForRestore.id);
            } catch {
              /* silent */
            }
          }
          setShowRestoreDialog(false);
        }}
      />

      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between gap-2">
        <div className="flex flex-col min-w-0">
          <h1 className="text-xl font-bold">{t("post.createTitle")}</h1>
          <AutosaveIndicator
            status={draftStatus}
            lastSavedAt={lastSavedAt}
            t={t}
          />
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            href="/posts/drafts"
            className="text-xs text-text-muted hover:text-primary transition-colors hidden sm:inline"
          >
            {t("post.draft.list.title")}
          </Link>
          {me && (
            <button
              onClick={handleManualSave}
              disabled={draftStatus === "saving" || submitting}
              className="text-sm text-text-secondary border border-border rounded-full px-3 py-1.5 hover:bg-surface-hover disabled:opacity-40 transition-colors"
            >
              {draftStatus === "saving"
                ? t("post.draft.savingIndicator")
                : t("post.draft.saveButton")}
            </button>
          )}
        <button
          onClick={handleSubmit}
          disabled={submitting || !me}
          className="btn-primary text-sm disabled:opacity-50"
        >
          {submitting
            ? t("post.submitting")
            : scheduledAt
              ? t("post.submitScheduled")
              : t("post.submit")}
        </button>
        </div>
      </div>

      {/* AC-7: multi-tab edit warning banner */}
      {multiTabWarning && (
        <div
          className="bg-warning/10 border-b border-warning/40 px-4 py-2 text-xs text-warning flex items-center justify-between gap-2"
          role="status"
        >
          <span>{t("post.draft.multiTabWarning")}</span>
          <button
            type="button"
            onClick={() => setMultiTabWarning(false)}
            aria-label="dismiss"
            className="text-warning/80 hover:text-warning text-sm leading-none"
          >
            ✕
          </button>
        </div>
      )}

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
          {/* Post type toggle — UI guard: non-artists cannot select 'product'.
              Backend defense remains at api/posts.py:206-210 (FORBIDDEN 403). */}
          <PostTypeSelector
            value={type}
            onChange={setType}
            userRole={me.role}
            applicationStatus={applicationStatus}
            disabled={uploading || submitting}
          />

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
            placeholder={t("post.contentPlaceholder")}
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
                      즉시구매가 (USD)
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

// ─── Draft helpers (editor-draft-autosave PDCA) ─────────────────────────

function AutosaveIndicator({
  status,
  lastSavedAt,
  t,
}: {
  status: DraftSaveStatus;
  lastSavedAt: Date | null;
  t: (key: string) => string;
}) {
  if (status === "idle" || !lastSavedAt) return null;
  if (status === "error") {
    return (
      <span className="text-xs text-danger">
        {t("post.draft.errorIndicator")}
      </span>
    );
  }
  if (status === "saving") {
    return (
      <span className="text-xs text-text-muted">
        {t("post.draft.savingIndicator")}
      </span>
    );
  }
  return (
    <span className="text-xs text-text-muted">
      {t("post.draft.savedIndicator")} · {formatRelativeTime(lastSavedAt)}
    </span>
  );
}

/** Convert a server-side Draft into the editor's DraftState shape. */
function draftToFormState(d: Draft): DraftState {
  const product = d.product;
  return {
    type: d.type,
    title: d.title ?? "",
    content: d.content ?? "",
    genre: d.genre ?? "painting",
    tags: d.tags ?? [],
    media: d.media.map((m) => ({
      type: m.type,
      url: m.url,
      thumbnail_url: m.thumbnail_url ?? undefined,
      width: m.width ?? undefined,
      height: m.height ?? undefined,
      duration_sec: m.duration_sec ?? undefined,
      size_bytes: m.size_bytes ?? undefined,
      external_source: m.external_source ?? undefined,
      external_id: m.external_id ?? undefined,
      is_making_video: m.is_making_video ?? undefined,
    })),
    embeds: [],
    isMakingVideo: false,
    scheduledAt: d.scheduled_at ?? "",
    locationName: d.location_name ?? "",
    locationLat: d.location_lat ?? null,
    locationLng: d.location_lng ?? null,
    isAuction: product?.is_auction ?? true,
    isBuyNow: product?.is_buy_now ?? false,
    buyNowPrice:
      typeof product?.buy_now_price === "number"
        ? product.buy_now_price
        : typeof product?.buy_now_price === "string"
          ? Number(product.buy_now_price) || ""
          : "",
    dimensions: product?.dimensions ?? "",
    medium: product?.medium ?? "",
    year: product?.year ?? 2026,
  };
}
