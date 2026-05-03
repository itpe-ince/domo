"use client";

/**
 * EditorMobileWizard — editor-responsive-redesign PDCA (#3, Step 5).
 *
 * Mobile (`< md`) step container. Owns a `useEditorWizardStep` instance
 * (deriving the steps array from current post type), renders the
 * WizardStepIndicator on top, the active step component in the middle,
 * and a sticky footer with prev / next / submit buttons + a tertiary
 * 임시저장 button (OQ-D-3 = B — no sticky header, primary submit only on
 * the last step).
 *
 * The desktop EditorWorkspace and this mobile wizard share `formState`
 * via the same setters (PostFormSetters from usePostFormState), so
 * draft autosave and PostTypeSelector role-gating work identically.
 *
 * Pattern source: design §3.3 + §4.1 (EditorMobileWizard) + OQ-4 = A +
 * OQ-D-2 = B + OQ-D-3 = B.
 */

import { useI18n } from "@/i18n";
import {
  type ApiUser,
  type CreatePostMedia,
  type OEmbedData,
  type Visibility,
  type Series,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import type { DraftSaveStatus } from "@/lib/hooks/useDraftAutosave";
import {
  useEditorWizardStep,
  type WizardStep,
} from "@/lib/hooks/useEditorWizardStep";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";
import type { PostFormSetters } from "@/lib/hooks/usePostFormState";
import type { ArtistApplicationStatus } from "@/components/post-editor/PostTypeSelector";
import { WizardStepIndicator } from "@/components/post-editor/WizardStepIndicator";
import { EditorStepType } from "@/components/post-editor/wizard/EditorStepType";
import { EditorStepContent } from "@/components/post-editor/wizard/EditorStepContent";
import { EditorStepProductMeta } from "@/components/post-editor/wizard/EditorStepProductMeta";
import { EditorStepPublish } from "@/components/post-editor/wizard/EditorStepPublish";
import { PublishOptionsPanel } from "@/components/post-editor/PublishOptionsPanel";

export interface EditorMobileWizardProps {
  // Form state read
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
  // Setters
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
  // Multi-tab warning
  multiTabWarning: boolean;
  onDismissWarning: () => void;
  // Media handlers
  onFiles: (files: FileList) => Promise<void>;
  onGif: (file: File) => Promise<void>;
  onEmojiInsert: (emoji: string) => void;
  onEmbedAdd: (data: OEmbedData) => void;
  // editor-media-ux PDCA #4
  onReorder: (activeId: string, overId: string) => void;
  onCaptionChange: (id: string, caption: string) => void;
  uploadQueue: UploadTask[];
  // editor-image-studio PDCA #6-image — Step 6 props drilling
  onEditMedia?: (id: string) => void;
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
}

export function EditorMobileWizard(props: EditorMobileWizardProps) {
  const { t } = useI18n();
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
    visibility,
    setVisibility,
    commentsEnabled,
    setCommentsEnabled,
    seriesIds,
    setSeriesIds,
    mySeries,
    mySeriesLoading,
    onCreateSeriesClick,
  } = props;

  // Derive step machine from current post type — type=product adds a
  // product_meta step between content and publish.
  const wizard = useEditorWizardStep({ type, initialStep: "type" });

  const onLocationManualEntry = (name: string) => {
    setters.setLocationName(name);
    setters.setLocationLat(37.5665);
    setters.setLocationLng(126.978);
  };

  return (
    <div className="flex flex-col min-h-screen md:hidden">
      {/* Top: progress + light header */}
      <header className="border-b border-border bg-background">
        <div className="px-4 pt-3 pb-1 flex items-center justify-between gap-2">
          <h1 className="text-lg font-bold">{t("post.createTitle")}</h1>
          <SaveStateBadge
            status={draftStatus}
            lastSavedAt={lastSavedAt}
            t={t}
          />
        </div>
        <WizardStepIndicator
          steps={wizard.steps as readonly WizardStep[]}
          currentStep={wizard.step}
        />
      </header>

      {/* AC-7: multi-tab warning banner (same UX as desktop) */}
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

      {/* Step body — login-gated, page handles LoginModal */}
      {me && (
        <main className="flex-1 px-4 py-4 pb-24">
          {wizard.step === "type" && (
            <EditorStepType
              type={type}
              onTypeChange={setters.setType}
              userRole={me.role}
              applicationStatus={applicationStatus}
              disabled={uploading || submitting}
            />
          )}
          {wizard.step === "content" && (
            <EditorStepContent
              title={title}
              onTitleChange={setters.setTitle}
              content={content}
              onContentChange={setters.setContent}
              media={media}
              onMediaChange={setters.setMedia}
              embeds={embeds}
              onEmbedsChange={setters.setEmbeds}
              tags={tags}
              onTagsChange={setters.setTags}
              isMakingVideo={isMakingVideo}
              onIsMakingVideoChange={setters.setIsMakingVideo}
              scheduledAt={scheduledAt}
              onScheduledAtChange={setters.setScheduledAt}
              uploading={uploading}
              submitting={submitting}
              textareaRef={textareaRef}
              tagRef={tagRef}
              onFiles={onFiles}
              onGif={onGif}
              onEmojiInsert={onEmojiInsert}
              onEmbedAdd={onEmbedAdd}
              onLocationManualEntry={onLocationManualEntry}
              onReorder={onReorder}
              onCaptionChange={onCaptionChange}
              uploadQueue={uploadQueue}
              onEditMedia={onEditMedia}
            />
          )}
          {wizard.step === "product_meta" && (
            <EditorStepProductMeta
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
          {wizard.step === "publish-options" && (
            <PublishOptionsPanel
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
              onCreateSeriesClick={onCreateSeriesClick}
            />
          )}
          {wizard.step === "publish" && (
            <EditorStepPublish
              scheduledAt={scheduledAt}
              onScheduledAtChange={setters.setScheduledAt}
              locationName={locationName}
              onLocationNameChange={setters.setLocationName}
              onLocationLatChange={setters.setLocationLat}
              onLocationLngChange={setters.setLocationLng}
              error={error}
            />
          )}
        </main>
      )}

      {/* Sticky footer — OQ-D-2 = B (opaque background) + OQ-D-3 = B
          (only the last step exposes the primary submit button). */}
      <footer className="sticky bottom-0 z-20 bg-background border-t border-border px-4 py-3 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={wizard.goPrev}
          disabled={wizard.isFirstStep}
          className="text-sm text-text-secondary border border-border rounded-full px-4 py-2 hover:bg-surface-hover disabled:opacity-40 transition-colors"
        >
          {t("post.editor.wizard.prev")}
        </button>

        <div className="flex items-center gap-2 flex-shrink-0">
          {me && (
            <button
              type="button"
              onClick={onManualSave}
              disabled={draftStatus === "saving" || submitting}
              className="text-xs text-text-secondary hover:text-text-primary px-3 py-2 disabled:opacity-40 transition-colors"
            >
              {draftStatus === "saving"
                ? t("post.draft.savingIndicator")
                : t("post.draft.saveButton")}
            </button>
          )}
          {wizard.isLastStep ? (
            <button
              type="button"
              onClick={onSubmit}
              disabled={submitting || !me}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {submitting
                ? t("post.submitting")
                : scheduledAt
                  ? t("post.submitScheduled")
                  : t("post.submit")}
            </button>
          ) : (
            <button
              type="button"
              onClick={wizard.goNext}
              className="btn-primary text-sm"
            >
              {t("post.editor.wizard.next")}
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}

/**
 * SaveStateBadge — compact autosave status for the wizard top header.
 * Same branch order as the desktop AutosaveIndicator (idle/no save → null).
 */
function SaveStateBadge({
  status,
  lastSavedAt,
  t,
}: {
  status: DraftSaveStatus;
  lastSavedAt: Date | null;
  t: (key: string, params?: Record<string, string>) => string;
}) {
  if (status === "idle" || !lastSavedAt) return null;
  if (status === "error") {
    return (
      <span className="text-[11px] text-danger">
        {t("post.draft.errorIndicator")}
      </span>
    );
  }
  if (status === "saving") {
    return (
      <span className="text-[11px] text-text-muted">
        {t("post.draft.savingIndicator")}
      </span>
    );
  }
  return (
    <span className="text-[11px] text-text-muted">
      {t("post.draft.savedIndicator")} · {formatRelativeTime(lastSavedAt)}
    </span>
  );
}
