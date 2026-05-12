"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { arrayMove } from "@dnd-kit/sortable";
import {
  ApiClientError,
  CreatePostMedia,
  OEmbedData,
  createPost,
  deleteDraft,
  getDraft,
  publishPost,
  registerExternalMedia,
  type Draft,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { centsToDollarsString } from "@/lib/format";
import {
  readLocalStorageDraft,
  useDraftAutosave,
  type DraftState,
} from "@/lib/hooks/useDraftAutosave";
import { usePostFormState } from "@/lib/hooks/usePostFormState";
import { useArtistGate } from "@/lib/hooks/useArtistGate";
import { useGlobalHotkeys } from "@/lib/hooks/useGlobalHotkeys";
import { useMediaUploadQueue } from "@/lib/hooks/useMediaUploadQueue";
import { useMySeries } from "@/lib/hooks/useMySeries";
import { LoginModal } from "@/components/LoginModal";
import {
  DraftRestoreDialog,
  type DraftRestoreSource,
} from "@/components/DraftRestoreDialog";
import { EditorMobileWizard } from "@/components/post-editor/EditorMobileWizard";
import { EditorTopBar } from "@/components/post-editor/EditorTopBar";
import { EditorWorkspace } from "@/components/post-editor/EditorWorkspace";
import { PreviewPane } from "@/components/post-editor/PreviewPane";
import { PublishDrawer } from "@/components/post-editor/PublishDrawer";
import { ImageEditorLazy } from "@/components/post-editor/ImageEditorLazy";
import { DigitalArtWarningModal } from "@/components/post-editor/DigitalArtWarningModal";
import nextDynamic from "next/dynamic";

// SeriesCreateModal — 시리즈 생성 모달. 에디터 페이지에서만 필요하며
// 열릴 때만 로드되도록 dynamic import 적용 (G''-6 번들 최종화)
// 주의: 이 파일은 export const dynamic = "force-dynamic" 을 사용하므로
//       next/dynamic의 default export를 nextDynamic으로 alias
const SeriesCreateModal = nextDynamic(
  () =>
    import("@/components/post-editor/SeriesCreateModal").then(
      (m) => ({ default: m.SeriesCreateModal })
    ),
  {
    ssr: false,
    loading: () => null,
  }
);

// Disable prerender — uses useSearchParams() which requires runtime
export const dynamic = "force-dynamic";

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
    setVisibility,
    setCommentsEnabled,
    setSeriesIds,
    setEarlyAccessDuration,
    setEarlyAccessTier,
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
    visibility = "public",
    commentsEnabled = true,
    seriesIds = [],
    earlyAccessDuration = null,
    earlyAccessTier = null,
  } = formState;

  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // artist-tier-release PDCA #10 — prevent publish when only one of the two
  // tier fields is set (mirrors server-side TIER_FIELDS_INCONSISTENT check).
  const tierInconsistent =
    (earlyAccessDuration !== null) !== (earlyAccessTier !== null);

  // Artist gate — encapsulates the non-artist auto-fallback effect and the
  // application-status fetch. PostTypeSelector consumes applicationStatus.
  const { applicationStatus } = useArtistGate({
    me: me ?? null,
    type,
    onTypeChange: setType,
  });

  // editor-media-ux PDCA #4 — parallel upload queue with real progress
  // upload-retry-ui (D-2) — retryTask + cancelTask now exposed
  const {
    queue: uploadQueue,
    enqueue: enqueueUploads,
    enqueueGif: enqueueGifUpload,
    retryTask: retryUpload,
    cancelTask: cancelUpload,
  } = useMediaUploadQueue();

  // publish-controls PDCA #8 — series list + create modal
  const {
    series: mySeries,
    loading: mySeriesLoading,
    add: addSeries,
  } = useMySeries();
  const [seriesCreateModalOpen, setSeriesCreateModalOpen] = useState(false);

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

  // ─── Preview pane (editor-responsive-redesign PDCA, OQ-D-4 = A) ─────
  // Default visible on desktop. Hidden on mobile via PreviewPane's own
  // `hidden md:block` classes; toggle below only matters when ≥ md.
  const [isPreviewVisible, setIsPreviewVisible] = useState(true);

  // B1: 발행 옵션 Drawer (desktop only) — 헤더 버튼으로 열기
  const [isPublishDrawerOpen, setIsPublishDrawerOpen] = useState(false);

  // ② 디지털 아트 판독 큐 경고 모달 — 미디어 첨부 시 등록 버튼 클릭하면 표시
  const [digitalArtWarningOpen, setDigitalArtWarningOpen] = useState(false);
  // 실제 등록 로직을 저장해두었다가 confirm 시 실행
  const pendingSubmitRef = useRef<(() => Promise<void>) | null>(null);

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
    // editor-media-ux PDCA #4 — backfill _clientId for legacy drafts saved
    // before this PDCA. New drafts get _clientId from useMediaUploadQueue,
    // but pre-existing localStorage entries omit it — adding stable ids now
    // makes drag-reorder deterministic across renders.
    const restored: DraftState = {
      ...d,
      media: d.media.map((m) =>
        m._clientId ? m : { ...m, _clientId: crypto.randomUUID() }
      ),
    };
    resetFromDraft(restored);
    if (sourceId) setCurrentDraftId(sourceId);
    setShowRestoreDialog(false);
  }

  async function handleManualSave() {
    if (!me) return;
    const id = await saveToServer();
    if (id) setCurrentDraftId(id);
  }

  // Phase 11 D-1: ⌘S / Ctrl+S 전역 단축키 → 임시저장
  // preventInInputs: false — 폼(textarea 등) 포커스 중에도 동작해야 함
  useGlobalHotkeys([
    {
      key: "s",
      modifier: "cmd",
      handler: (e) => {
        e.preventDefault(); // 브라우저 기본 "저장" 다이얼로그 차단
        void handleManualSave();
      },
      preventInInputs: false,
    },
  ]);

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

  // editor-media-ux PDCA #4 — replaced sequential `for...of` with the
  // parallel queue. Each successful upload comes back with a `_clientId`
  // pre-filled by useMediaUploadQueue, so SortableContext gets a stable id
  // immediately. Failures stay in the queue with status='error' for the
  // MediaUploadProgress badge to surface.
  async function handleFiles(files: FileList) {
    setUploading(true);
    setError(null);
    try {
      const newMedia = await enqueueUploads(files, isMakingVideo);
      if (newMedia.length > 0) {
        setMedia((prev) => [...prev, ...newMedia]);
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
      const created = await enqueueGifUpload(file);
      if (created) setMedia((prev) => [...prev, created]);
    } catch {
      setError("GIF 업로드 실패");
    } finally {
      setUploading(false);
    }
  }

  // editor-media-ux PDCA #4 — drag-reorder + caption change handlers.
  // mediaIdOf MUST mirror MediaPreviewList's `mediaId` fallback so
  // legacy drafts (no _clientId) reorder predictably.
  function mediaIdOf(m: CreatePostMedia, i: number): string {
    return m._clientId ?? `legacy-${i}-${m.url.length}-${m.url.slice(-12)}`;
  }
  function handleReorder(activeId: string, overId: string) {
    setMedia((prev) => {
      const oldIdx = prev.findIndex((m, i) => mediaIdOf(m, i) === activeId);
      const newIdx = prev.findIndex((m, i) => mediaIdOf(m, i) === overId);
      if (oldIdx === -1 || newIdx === -1) return prev;
      return arrayMove(prev, oldIdx, newIdx);
    });
  }
  function handleCaptionChange(id: string, caption: string) {
    setMedia((prev) =>
      prev.map((m, i) => (mediaIdOf(m, i) === id ? { ...m, caption } : m))
    );
  }

  // editor-image-studio PDCA #6-image — Step 6: open/close image editor modal
  const [editingMediaId, setEditingMediaId] = useState<string | null>(null);

  function handleEditMedia(id: string) {
    setEditingMediaId(id);
  }

  // Find the media item currently being edited (null when modal is closed)
  const editingMedia = editingMediaId
    ? formState.media.find((m, i) => mediaIdOf(m, i) === editingMediaId) ?? null
    : null;

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
    // artist-tier-release PDCA #10 — tier/duration consistency guard
    if (tierInconsistent) {
      setError(t("post.editor.error.tierFieldsInconsistent"));
      return;
    }
    setSubmitting(true);
    try {
      // publish-controls PDCA #8 — Hybrid path C:
      //   For EXISTING drafts (currentDraftId set by autosave/restore): call publishPost directly.
      //   For NEW posts (no currentDraftId): create draft first via saveToServer, then publish.
      //   This avoids any Backend changes to createPost while enabling the full publish endpoint flow.
      const mediaPayload = media.map(({ _clientId: _c, id: _id, ...rest }) => rest);

      let draftId = currentDraftId;

      if (!draftId) {
        // No existing draft — save to server first to get a post id
        const serverDraftId = await saveToServer();
        if (!serverDraftId) {
          // saveToServer failed (network error etc.) — fall back to legacy createPost
          const post = await createPost({
            type,
            title: title || undefined,
            content: content || undefined,
            genre: type === "product" ? genre : undefined,
            tags: tags.length ? tags : undefined,
            media: mediaPayload,
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
            from_draft_id: undefined,
          });
          clearDraft();
          router.push(`/posts/${post.id}`);
          return;
        }
        draftId = serverDraftId;
        setCurrentDraftId(draftId);
      }

      // Publish via the new endpoint
      const result = await publishPost(draftId, {
        publish_at: scheduledAt || null,
        visibility,
        comments_enabled: commentsEnabled,
        series_ids: seriesIds,
        // artist-tier-release PDCA #10
        early_access_duration: earlyAccessDuration ?? null,
        early_access_tier: earlyAccessTier ?? null,
      });

      // Wipe localStorage. Server draft deleted by publishPost's from_draft_id;
      // belt-and-suspenders DELETE as fallback.
      clearDraft();
      try {
        await deleteDraft(draftId);
      } catch {
        /* silent — draft may already be deleted by publish endpoint */
      }

      if (result.status === "scheduled") {
        router.push(`/posts/${result.id}?scheduled=1`);
      } else {
        router.push(`/posts/${result.id}`);
      }
    } catch (e) {
      setError(mapPublishError(e, t));
    } finally {
      setSubmitting(false);
    }
  }

  // ② 등록 버튼 클릭 시 미디어 첨부된 경우 경고 모달 경유
  // 미디어 없으면 바로 handleSubmit 실행, 있으면 경고 모달 → 확인 시 handleSubmit.
  async function handleSubmitWithWarning() {
    const hasMedia = media.some(
      (m) => m.type === "image" || m.type === "video"
    );
    if (hasMedia) {
      pendingSubmitRef.current = handleSubmit;
      setDigitalArtWarningOpen(true);
    } else {
      await handleSubmit();
    }
  }

  function mapPublishError(
    e: unknown,
    t: (key: string) => string
  ): string {
    if (!(e instanceof ApiClientError)) return "작성 실패";
    const codeMap: Record<string, string> = {
      POST_NOT_FOUND: t("post.editor.error.postNotFound"),
      POST_NOT_OWNER: t("post.editor.error.postNotOwner"),
      POST_INVALID_STATE: t("post.editor.error.postInvalidState"),
      AUCTION_ACTIVE_VISIBILITY_LOCKED: t("post.editor.error.auctionActiveVisibilityLocked"),
      SERIES_NOT_FOUND: t("post.editor.error.seriesNotFound"),
      SERIES_NOT_OWNER: t("post.editor.error.seriesNotOwner"),
      SCHEDULED_AT_TOO_SOON: t("post.editor.error.scheduledAtTooSoon"),
      SCHEDULED_AT_TOO_FAR: t("post.editor.error.scheduledAtTooFar"),
      COMMENTS_DISABLED: t("post.editor.error.commentsDisabled"),
      // artist-tier-release PDCA #10
      INVALID_TIER: t("post.editor.error.invalidTier"),
      INVALID_DURATION: t("post.editor.error.invalidDuration"),
      TIER_FIELDS_INCONSISTENT: t("post.editor.error.tierFieldsInconsistent"),
    };
    return codeMap[e.code] ?? `${e.code}: ${e.message}`;
  }

  return (
    <>
      {/* Draft restore dialog (editor-draft-autosave PDCA) — fixed position
          modal, lives outside <main> so it does not become a grid item. */}
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

      {/* ① Desktop 레이아웃: 좌(편집) / 우(미리보기) 2-col split.
          페이지 폭 max-w-7xl로 확장 — 동시 작업 환경 제공. */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Mobile (< md): step wizard. Internally owns useEditorWizardStep
            and renders the four EditorStepXxx components plus a sticky
            footer with prev/next/submit + 임시저장 buttons. */}
        <EditorMobileWizard
          type={type}
          title={title}
          content={content}
          genre={genre}
          tags={tags}
          media={media}
          embeds={embeds}
          isMakingVideo={isMakingVideo}
          scheduledAt={scheduledAt}
          locationName={locationName}
          isAuction={isAuction}
          isBuyNow={isBuyNow}
          buyNowPrice={buyNowPrice}
          dimensions={dimensions}
          medium={medium}
          year={year}
          setters={setters}
          textareaRef={textareaRef}
          tagRef={tagRef}
          me={me ?? null}
          applicationStatus={applicationStatus}
          uploading={uploading}
          submitting={submitting}
          error={error}
          draftStatus={draftStatus}
          lastSavedAt={lastSavedAt}
          onManualSave={handleManualSave}
          onSubmit={handleSubmitWithWarning}
          multiTabWarning={multiTabWarning}
          onDismissWarning={() => setMultiTabWarning(false)}
          onFiles={handleFiles}
          onGif={handleGif}
          onEmojiInsert={handleEmojiInsert}
          onEmbedAdd={handleEmbedAdd}
          onReorder={handleReorder}
          onCaptionChange={handleCaptionChange}
          uploadQueue={uploadQueue}
          onEditMedia={handleEditMedia}
          onRetryUpload={retryUpload}
          onCancelUpload={cancelUpload}
          visibility={visibility}
          setVisibility={setVisibility}
          commentsEnabled={commentsEnabled}
          setCommentsEnabled={setCommentsEnabled}
          seriesIds={seriesIds}
          setSeriesIds={setSeriesIds}
          mySeries={mySeries}
          mySeriesLoading={mySeriesLoading}
          onCreateSeriesClick={() => setSeriesCreateModalOpen(true)}
          earlyAccessDuration={earlyAccessDuration}
          setEarlyAccessDuration={setEarlyAccessDuration}
          earlyAccessTier={earlyAccessTier}
          setEarlyAccessTier={setEarlyAccessTier}
        />

        {/* Desktop (≥ md) sticky toolbar — grid 전체 폭에 걸침.
            모바일은 EditorMobileWizard 자체 sticky footer 사용하므로 hidden md:block. */}
        <div className="hidden md:block w-full max-w-7xl mx-auto">
          <EditorTopBar
            me={me ?? null}
            type={type}
            setters={setters}
            uploading={uploading}
            submitting={submitting}
            draftStatus={draftStatus}
            lastSavedAt={lastSavedAt}
            onManualSave={handleManualSave}
            onSubmit={handleSubmitWithWarning}
            scheduledAt={scheduledAt}
            isPreviewVisible={isPreviewVisible}
            onTogglePreview={() => setIsPreviewVisible((v) => !v)}
            onPublishOptionsClick={() => setIsPublishDrawerOpen(true)}
          />
        </div>

        {/* Desktop (≥ md): 좌(편집) + 우(미리보기) 좌우 split.
            isPreviewVisible 토글 시 우측 패널 접기. 폭은 max-w-7xl까지 확장. */}
        <div className="hidden md:grid w-full max-w-7xl mx-auto gap-6 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] data-[preview-hidden=true]:md:grid-cols-1"
             data-preview-hidden={!isPreviewVisible}>
          <div className="min-w-0">
          <EditorWorkspace
            type={type}
            title={title}
            content={content}
            genre={genre}
            tags={tags}
            media={media}
            embeds={embeds}
            isMakingVideo={isMakingVideo}
            scheduledAt={scheduledAt}
            locationName={locationName}
            isAuction={isAuction}
            isBuyNow={isBuyNow}
            buyNowPrice={buyNowPrice}
            dimensions={dimensions}
            medium={medium}
            year={year}
            setters={setters}
            textareaRef={textareaRef}
            tagRef={tagRef}
            me={me ?? null}
            applicationStatus={applicationStatus}
            uploading={uploading}
            submitting={submitting}
            error={error}
            draftStatus={draftStatus}
            lastSavedAt={lastSavedAt}
            onManualSave={handleManualSave}
            onSubmit={handleSubmitWithWarning}
            isPreviewVisible={isPreviewVisible}
            onTogglePreview={() => setIsPreviewVisible((v) => !v)}
            onPublishOptionsClick={() => setIsPublishDrawerOpen(true)}
            multiTabWarning={multiTabWarning}
            onDismissWarning={() => setMultiTabWarning(false)}
            onFiles={handleFiles}
            onGif={handleGif}
            onEmojiInsert={handleEmojiInsert}
            onEmbedAdd={handleEmbedAdd}
            onReorder={handleReorder}
            onCaptionChange={handleCaptionChange}
            uploadQueue={uploadQueue}
            onEditMedia={handleEditMedia}
            onRetryUpload={retryUpload}
            onCancelUpload={cancelUpload}
            visibility={visibility}
            setVisibility={setVisibility}
            commentsEnabled={commentsEnabled}
            setCommentsEnabled={setCommentsEnabled}
            seriesIds={seriesIds}
            setSeriesIds={setSeriesIds}
            mySeries={mySeries}
            mySeriesLoading={mySeriesLoading}
            onCreateSeriesClick={() => setSeriesCreateModalOpen(true)}
            earlyAccessDuration={earlyAccessDuration}
            setEarlyAccessDuration={setEarlyAccessDuration}
            earlyAccessTier={earlyAccessTier}
            setEarlyAccessTier={setEarlyAccessTier}
          />
          </div>

        {/* ① PreviewPane 우측 — sticky로 스크롤 따라옴.
            isPreviewVisible=false 시 위 grid가 1-col로 떨어지며 이 영역 숨김. */}
        <aside className={`min-w-0 ${isPreviewVisible ? "block" : "hidden"}`}>
          <div className="md:sticky md:top-4">
          <PreviewPane
            isVisible={isPreviewVisible}
            type={type}
            title={title}
            content={content}
            media={media}
            embeds={embeds}
            tags={tags}
            genre={genre}
            isAuction={isAuction}
            isBuyNow={isBuyNow}
            buyNowPrice={buyNowPrice}
            me={me ?? null}
          />
          </div>
        </aside>
        </div>
      </main>

      {/* editor-image-studio PDCA #6-image — image editor modal (Konva, browser-only).
          Mounted outside <main> so it is not a grid item.
          Save wired in Step 8 via patchMediaTransform. */}
      {editingMedia && (
        <ImageEditorLazy
          media={editingMedia}
          initialOps={editingMedia.crop_meta}
          onSave={(updated) => {
            // editor-image-studio PDCA #6-image Step 8:
            // ImageEditor calls patchMediaTransform internally and passes back
            // the updated CreatePostMedia (with new url/crop_meta/id).
            // Replacing the item in formState triggers useDraftAutosave
            // within 2s — no explicit call needed.
            setMedia((prev) =>
              prev.map((m, i) =>
                mediaIdOf(m, i) === editingMediaId ? updated : m
              )
            );
            setEditingMediaId(null);
          }}
          onCancel={() => setEditingMediaId(null)}
        />
      )}

      {/* ② 디지털 아트 판독 큐 경고 모달 — 미디어 첨부 시 등록 직전 표시 */}
      <DigitalArtWarningModal
        open={digitalArtWarningOpen}
        onConfirm={async () => {
          setDigitalArtWarningOpen(false);
          if (pendingSubmitRef.current) {
            await pendingSubmitRef.current();
            pendingSubmitRef.current = null;
          }
        }}
        onCancel={() => {
          setDigitalArtWarningOpen(false);
          pendingSubmitRef.current = null;
        }}
      />

      {/* B1: 발행 옵션 Drawer (desktop only, z-50). 모바일은 wizard step 그대로. */}
      <PublishDrawer
        isOpen={isPublishDrawerOpen}
        onClose={() => setIsPublishDrawerOpen(false)}
        visibility={visibility}
        setVisibility={setVisibility}
        commentsEnabled={commentsEnabled}
        setCommentsEnabled={setCommentsEnabled}
        seriesIds={seriesIds}
        setSeriesIds={setSeriesIds}
        scheduledAt={scheduledAt}
        setScheduledAt={setters.setScheduledAt}
        mySeries={mySeries}
        seriesLoading={mySeriesLoading}
        disabled={uploading || submitting}
        onCreateSeriesClick={() => setSeriesCreateModalOpen(true)}
        earlyAccessDuration={earlyAccessDuration}
        setEarlyAccessDuration={setEarlyAccessDuration}
        earlyAccessTier={earlyAccessTier}
        setEarlyAccessTier={setEarlyAccessTier}
      />

      {/* publish-controls PDCA #8 — series create modal (z-[60]) */}
      <SeriesCreateModal
        open={seriesCreateModalOpen}
        onClose={() => setSeriesCreateModalOpen(false)}
        onCreated={(series) => {
          addSeries(series);
          // Auto-select the newly created series
          setSeriesIds([...seriesIds, series.id]);
        }}
      />
    </>
  );
}

// ─── Draft helpers (editor-draft-autosave PDCA) ─────────────────────────

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
    // G'-10: buy_now_price from draft/DB is cents (int). UI shows dollars.
    // centsToDollarsString converts to "50.00" for display; user edits in dollars.
    buyNowPrice:
      product?.buy_now_price != null
        ? Number(centsToDollarsString(product.buy_now_price))
        : "",
    dimensions: product?.dimensions ?? "",
    medium: product?.medium ?? "",
    year: product?.year ?? 2026,
  };
}
