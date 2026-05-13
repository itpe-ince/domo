"use client";

/**
 * EditorWorkspace — editor-responsive-redesign PDCA (#3, Step 3).
 *
 * Desktop (`md` and up) single-column edit form. Wraps the sticky header,
 * multi-tab warning banner, AutosaveIndicator, PostTypeSelector,
 * MediaToolbar, MediaPreviewList, TagAutocomplete, and ProductFields into
 * one component. Renders only when `me` is logged in — login modal is
 * handled by the page.
 *
 * Most props are forwarded as-is from CreatePostPageInner. The component
 * deliberately does NOT own form state — the page keeps that authority so
 * draft autosave and the upcoming mobile wizard can read the same source.
 *
 * Pattern source: design §4.1 (EditorWorkspace).
 */

import { useI18n } from "@/i18n";
import {
  type ApiUser,
  type CreatePostMedia,
  type EarlyAccessDuration,
  type EarlyAccessTier,
  type OEmbedData,
  type Visibility,
  type Series,
} from "@/lib/api";
import type {
  DraftSaveStatus,
} from "@/lib/hooks/useDraftAutosave";
import type { PostFormSetters } from "@/lib/hooks/usePostFormState";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";
import {
  PostTypeSelector,
  type ArtistApplicationStatus,
} from "@/components/post-editor/PostTypeSelector";
import { MediaToolbar } from "@/components/post-editor/MediaToolbar";
import { MediaPreviewList } from "@/components/post-editor/MediaPreviewList";
import { ProductFields } from "@/components/post-editor/ProductFields";
import { TagAutocomplete } from "@/components/post-editor/TagAutocomplete";
import { PublishOptionsPanel } from "@/components/post-editor/PublishOptionsPanel";
import { useAutoResizeTextarea } from "@/lib/hooks/useAutoResizeTextarea";

export interface EditorWorkspaceProps {
  // Form state (read)
  type: "general" | "product";
  title: string;
  content: string;
  genre: string;
  tags: string[];
  media: CreatePostMedia[];
  embeds: OEmbedData[];
  isMakingVideo: boolean;
  scheduledAt: string;
  locationName: string;
  isAuction: boolean;
  isBuyNow: boolean;
  buyNowPrice: number | "";
  dimensions: string;
  medium: string;
  year: number | "";
  // Setters (write) — full Dispatch<SetStateAction<T>> from usePostFormState
  setters: PostFormSetters;
  // Refs
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  tagRef: React.RefObject<HTMLDivElement | null>;
  // User context
  me: ApiUser | null;
  applicationStatus: ArtistApplicationStatus | undefined;
  // UI state
  uploading: boolean;
  submitting: boolean;
  error: string | null;
  // Draft autosave
  draftStatus: DraftSaveStatus;
  lastSavedAt: Date | null;
  onManualSave: () => void | Promise<void>;
  onSubmit: () => void | Promise<void>;
  // Preview toggle (desktop only)
  isPreviewVisible: boolean;
  onTogglePreview: () => void;
  // B1: 발행 옵션 Drawer 열기 트리거 (desktop only)
  onPublishOptionsClick: () => void;
  // Multi-tab warning
  multiTabWarning: boolean;
  onDismissWarning: () => void;
  // Media handlers
  onFiles: (files: FileList) => Promise<void>;
  onGif: (file: File) => Promise<void>;
  onEmojiInsert: (emoji: string) => void;
  onEmbedAdd: (data: OEmbedData) => void;
  // editor-media-ux PDCA #4 — drag-reorder + caption + upload queue
  onReorder: (activeId: string, overId: string) => void;
  onCaptionChange: (id: string, caption: string) => void;
  uploadQueue: UploadTask[];
  // editor-image-studio PDCA #6-image — Step 6 props drilling
  onEditMedia?: (id: string) => void;
  // upload-retry-ui (D-2) — retry / cancel upload tasks
  onRetryUpload?: (taskId: string) => void;
  onCancelUpload?: (taskId: string) => void;
  // publish-controls PDCA #8
  visibility: Visibility;
  setVisibility: (v: Visibility) => void;
  commentsEnabled: boolean;
  setCommentsEnabled: (b: boolean) => void;
  seriesIds: string[];
  setSeriesIds: (ids: string[]) => void;
  mySeries: Series[];
  mySeriesLoading: boolean;
  onCreateSeriesClick: () => void;
  // artist-tier-release PDCA #10
  earlyAccessDuration: EarlyAccessDuration | null;
  setEarlyAccessDuration: (v: EarlyAccessDuration | null) => void;
  earlyAccessTier: EarlyAccessTier | null;
  setEarlyAccessTier: (v: EarlyAccessTier | null) => void;
}

export function EditorWorkspace(props: EditorWorkspaceProps) {
  const { t, locale } = useI18n();

  // A1 — textarea auto-resize: 내용이 바뀔 때마다 height를 scrollHeight 에 맞춤
  useAutoResizeTextarea(
    props.textareaRef as React.RefObject<HTMLTextAreaElement | null>,
    props.content,
  );

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
    isAuction,
    isBuyNow,
    buyNowPrice,
    dimensions,
    medium,
    year,
    setters,
    textareaRef,
    tagRef,
    me,
    applicationStatus,
    uploading,
    submitting,
    error,
    draftStatus,
    lastSavedAt,
    onManualSave,
    onSubmit,
    isPreviewVisible,
    onTogglePreview,
    onPublishOptionsClick,
    multiTabWarning,
    onDismissWarning,
    onFiles,
    onGif,
    onEmojiInsert,
    onEmbedAdd,
    onReorder,
    onCaptionChange,
    uploadQueue,
    onEditMedia,
    onRetryUpload,
    onCancelUpload,
    visibility,
    setVisibility,
    commentsEnabled,
    setCommentsEnabled,
    seriesIds,
    setSeriesIds,
    mySeries,
    mySeriesLoading,
    onCreateSeriesClick,
    earlyAccessDuration,
    setEarlyAccessDuration,
    earlyAccessTier,
    setEarlyAccessTier,
  } = props;

  return (
    <>
      {/* AC-7: multi-tab edit warning banner */}
      {multiTabWarning && (
        <div
          className="bg-warning/10 border-b border-warning/40 px-4 py-2 text-xs text-warning flex items-center justify-between gap-2"
          role="status"
        >
          <span>{t("post.draft.multiTabWarning")}</span>
          <button
            type="button"
            onClick={onDismissWarning}
            aria-label="dismiss"
            className="text-warning/80 hover:text-warning text-sm leading-none"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="mx-4 mt-4 card border-danger p-3 text-danger text-sm">
          {error}
        </div>
      )}

      {me && (
        <div className="p-4 space-y-4">
          {/* PostTypeSelector는 sticky header에 통합됨 (③).
              비아티스트 사용자를 위한 hint만 별도 행으로 유지.
              applicationStatus=undefined(미신청자)도 hint 보이도록 조건 완화.
              Backend defense remains at api/posts.py:206-210 (FORBIDDEN 403). */}
          {!(me.role === "artist" || me.role === "admin") && (
            <PostTypeSelector
              value={type}
              onChange={setters.setType}
              userRole={me.role}
              applicationStatus={applicationStatus}
              disabled={uploading || submitting}
            />
          )}

          {/* Title */}
          <input
            type="text"
            value={title}
            onChange={(e) => setters.setTitle(e.target.value)}
            placeholder={t("post.title")}
            className="w-full bg-transparent text-xl font-bold text-text-primary placeholder:text-text-muted outline-none border-none pb-3 border-b border-border"
          />

          {/* Content — A1: rows 고정 제거, min-h-[180px] + useAutoResizeTextarea 로 자동 확장.
               max-h-[55vh] + overflow-y-auto: 본문이 길어져도 textarea 내부 스크롤로 처리,
               툴바·태그 영역이 화면 밖으로 밀리지 않음 (개선 1). */}
          <textarea
            ref={textareaRef as React.Ref<HTMLTextAreaElement>}
            value={content}
            onChange={(e) => setters.setContent(e.target.value)}
            placeholder={t("post.contentPlaceholder")}
            className="w-full bg-transparent text-text-primary placeholder:text-text-muted outline-none border-none resize-none text-sm leading-relaxed min-h-[180px] max-h-[55vh] overflow-y-auto"
          />

          {/* Media Preview — dnd-kit drag-reorder + caption (PDCA #4) */}
          <MediaPreviewList
            media={media}
            embeds={embeds}
            onRemoveMedia={(i) =>
              setters.setMedia((prev) => prev.filter((_, j) => j !== i))
            }
            onRemoveEmbed={(i) => {
              setters.setEmbeds((prev) => prev.filter((_, j) => j !== i));
              const embedUrl = embeds[i]?.url;
              if (embedUrl) {
                setters.setMedia((prev) =>
                  prev.filter(
                    (m) => !(m.type === "external_embed" && m.url === embedUrl)
                  )
                );
              }
            }}
            onReorder={onReorder}
            onCaptionChange={onCaptionChange}
            uploadQueue={uploadQueue}
            onEditMedia={onEditMedia}
            onRetryUpload={onRetryUpload}
            onCancelUpload={onCancelUpload}
          />
          {/* Note: legacy "uploading..." inline status is replaced by
              MediaUploadProgress badge inside MediaPreviewList (OQ-7=A). */}

          {/* Schedule / Location badges */}
          {(scheduledAt || locationName) && (
            <div className="flex flex-wrap gap-2">
              {scheduledAt && (
                <span className="flex items-center gap-1.5 bg-surface rounded-full px-3 py-1 text-xs text-primary">
                  ⏰ {new Date(scheduledAt).toLocaleString(locale)} {t("post.editor.scheduledLabel")}
                  <button
                    onClick={() => setters.setScheduledAt("")}
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
                      setters.setLocationName("");
                      setters.setLocationLat(null);
                      setters.setLocationLng(null);
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
              onChange={(e) => setters.setIsMakingVideo(e.target.checked)}
              className="accent-primary"
            />
            {t("post.makingVideoLabel")}
          </label>

          {/* Media Toolbar */}
          <div className="card">
            <MediaToolbar
              onImageSelect={onFiles}
              onGifSelect={onGif}
              onEmojiInsert={onEmojiInsert}
              onEmbedAdd={onEmbedAdd}
              onLocationClick={() => {
                const name = prompt(t("post.locationPrompt"));
                if (name) {
                  setters.setLocationName(name);
                  setters.setLocationLat(37.5665);
                  setters.setLocationLng(126.978);
                }
              }}
              scheduledAt={scheduledAt}
              onScheduleChange={setters.setScheduledAt}
              onTagFocus={() =>
                tagRef.current?.scrollIntoView({ behavior: "smooth" })
              }
              disabled={uploading || submitting}
            />
          </div>

          {/* Tags */}
          <div ref={tagRef as React.Ref<HTMLDivElement>}>
            <label className="block text-sm text-text-secondary mb-1">{t("post.tags")}</label>
            <TagAutocomplete tags={tags} onTagsChange={setters.setTags} />
          </div>

          {/* Product fields */}
          {type === "product" && (
            <ProductFields
              genre={genre}
              onGenreChange={setters.setGenre}
              dimensions={dimensions}
              onDimensionsChange={setters.setDimensions}
              medium={medium}
              onMediumChange={setters.setMedium}
              year={year}
              onYearChange={setters.setYear}
              isAuction={isAuction}
              onIsAuctionChange={setters.setIsAuction}
              isBuyNow={isBuyNow}
              onIsBuyNowChange={setters.setIsBuyNow}
              buyNowPrice={buyNowPrice}
              onBuyNowPriceChange={setters.setBuyNowPrice}
            />
          )}

          {/* ② artCheckNote 항상 표시 제거 — 등록 버튼 클릭 시 미디어 첨부된 경우에만 경고 모달로 표시 */}
          {/* B1: PublishOptionsPanel 은 page.tsx 의 PublishDrawer 로 이동.
               inline 박스 제거 — 데스크탑에서 헤더 "⚙️ 발행 옵션" 버튼으로 Drawer 열기. */}
        </div>
      )}
    </>
  );
}

