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
  registerExternalMedia,
  type Draft,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import {
  readLocalStorageDraft,
  useDraftAutosave,
  type DraftState,
} from "@/lib/hooks/useDraftAutosave";
import { usePostFormState } from "@/lib/hooks/usePostFormState";
import { useArtistGate } from "@/lib/hooks/useArtistGate";
import { useMediaUploadQueue } from "@/lib/hooks/useMediaUploadQueue";
import { LoginModal } from "@/components/LoginModal";
import {
  DraftRestoreDialog,
  type DraftRestoreSource,
} from "@/components/DraftRestoreDialog";
import { EditorMobileWizard } from "@/components/post-editor/EditorMobileWizard";
import { EditorWorkspace } from "@/components/post-editor/EditorWorkspace";
import { PreviewPane } from "@/components/post-editor/PreviewPane";

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

  // editor-media-ux PDCA #4 — parallel upload queue with real progress
  const {
    queue: uploadQueue,
    enqueue: enqueueUploads,
    enqueueGif: enqueueGifUpload,
  } = useMediaUploadQueue();

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
      // editor-media-ux PDCA #4 — strip the client-only _clientId before
      // sending to the backend. Pydantic schemas don't declare this field
      // (and may reject it under `extra="forbid"` in future), so we must
      // not leak it across the API boundary.
      const mediaPayload = media.map(({ _clientId: _ignore, ...rest }) => rest);
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

      <main
        className={`flex-1 min-w-0 md:grid md:items-start ${
          isPreviewVisible
            ? "md:grid-cols-[minmax(0,1fr)_24rem]"
            : "md:grid-cols-1"
        }`}
      >
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
          onSubmit={handleSubmit}
          multiTabWarning={multiTabWarning}
          onDismissWarning={() => setMultiTabWarning(false)}
          onFiles={handleFiles}
          onGif={handleGif}
          onEmojiInsert={handleEmojiInsert}
          onEmbedAdd={handleEmbedAdd}
          onReorder={handleReorder}
          onCaptionChange={handleCaptionChange}
          uploadQueue={uploadQueue}
        />

        {/* Desktop (≥ md): single-column workspace + side preview pane.
            EditorMobileWizard above sets `display:none` on md+ so it is
            removed from the CSS grid; grid placement falls to these
            two children. */}
        <div className="hidden md:block max-w-3xl mx-auto md:mx-0 md:max-w-none w-full">
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
            onSubmit={handleSubmit}
            isPreviewVisible={isPreviewVisible}
            onTogglePreview={() => setIsPreviewVisible((v) => !v)}
            multiTabWarning={multiTabWarning}
            onDismissWarning={() => setMultiTabWarning(false)}
            onFiles={handleFiles}
            onGif={handleGif}
            onEmojiInsert={handleEmojiInsert}
            onEmbedAdd={handleEmbedAdd}
            onReorder={handleReorder}
            onCaptionChange={handleCaptionChange}
            uploadQueue={uploadQueue}
          />
        </div>

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
      </main>
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
