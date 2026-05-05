"use client";

/**
 * EditorStepContent — editor-responsive-redesign PDCA (#3, Step 4).
 *
 * Mobile wizard step 2: title, content body, media (with toolbar + preview),
 * tags, isMakingVideo checkbox. Renders the same building blocks the
 * desktop EditorWorkspace uses, in single-column mobile layout.
 *
 * Pattern source: design §4.1 (EditorStepContent).
 */

import type { CreatePostMedia, OEmbedData } from "@/lib/api";
import { useI18n } from "@/i18n";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";
import { MediaToolbar } from "@/components/post-editor/MediaToolbar";
import { MediaPreviewList } from "@/components/post-editor/MediaPreviewList";
import { TagAutocomplete } from "@/components/post-editor/TagAutocomplete";

export interface EditorStepContentProps {
  title: string;
  onTitleChange: (v: string) => void;
  content: string;
  onContentChange: (v: string) => void;
  media: CreatePostMedia[];
  onMediaChange: React.Dispatch<React.SetStateAction<CreatePostMedia[]>>;
  embeds: OEmbedData[];
  onEmbedsChange: React.Dispatch<React.SetStateAction<OEmbedData[]>>;
  tags: string[];
  onTagsChange: (v: string[]) => void;
  isMakingVideo: boolean;
  onIsMakingVideoChange: (v: boolean) => void;
  scheduledAt: string;
  onScheduledAtChange: (v: string) => void;
  uploading: boolean;
  submitting: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  tagRef: React.RefObject<HTMLDivElement | null>;
  onFiles: (files: FileList) => Promise<void>;
  onGif: (file: File) => Promise<void>;
  onEmojiInsert: (emoji: string) => void;
  onEmbedAdd: (data: OEmbedData) => void;
  onLocationManualEntry: (name: string) => void;
  // editor-media-ux PDCA #4
  onReorder: (activeId: string, overId: string) => void;
  onCaptionChange: (id: string, caption: string) => void;
  uploadQueue: UploadTask[];
  // editor-image-studio PDCA #6-image — Step 6 props drilling
  onEditMedia?: (id: string) => void;
  // upload-retry-ui (D-2) — retry / cancel upload tasks
  onRetryUpload?: (taskId: string) => void;
  onCancelUpload?: (taskId: string) => void;
}

export function EditorStepContent(props: EditorStepContentProps) {
  const { t } = useI18n();
  const {
    title,
    onTitleChange,
    content,
    onContentChange,
    media,
    onMediaChange,
    embeds,
    onEmbedsChange,
    tags,
    onTagsChange,
    isMakingVideo,
    onIsMakingVideoChange,
    scheduledAt,
    onScheduledAtChange,
    uploading,
    submitting,
    textareaRef,
    tagRef,
    onFiles,
    onGif,
    onEmojiInsert,
    onEmbedAdd,
    onLocationManualEntry,
    onReorder,
    onCaptionChange,
    uploadQueue,
    onEditMedia,
    onRetryUpload,
    onCancelUpload,
  } = props;

  return (
    <section className="space-y-4">
      <input
        type="text"
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        placeholder={t("post.title")}
        className="w-full bg-transparent text-xl font-bold text-text-primary placeholder:text-text-muted outline-none border-none"
      />

      <textarea
        ref={textareaRef as React.Ref<HTMLTextAreaElement>}
        value={content}
        onChange={(e) => onContentChange(e.target.value)}
        placeholder={t("post.contentPlaceholder")}
        rows={6}
        className="w-full bg-transparent text-text-primary placeholder:text-text-muted outline-none border-none resize-none text-sm leading-relaxed"
      />

      <MediaPreviewList
        media={media}
        embeds={embeds}
        onReorder={onReorder}
        onCaptionChange={onCaptionChange}
        uploadQueue={uploadQueue}
        onEditMedia={onEditMedia}
        onRetryUpload={onRetryUpload}
        onCancelUpload={onCancelUpload}
        onRemoveMedia={(i) => onMediaChange((prev) => prev.filter((_, j) => j !== i))}
        onRemoveEmbed={(i) => {
          onEmbedsChange((prev) => prev.filter((_, j) => j !== i));
          const embedUrl = embeds[i]?.url;
          if (embedUrl) {
            onMediaChange((prev) =>
              prev.filter(
                (m) => !(m.type === "external_embed" && m.url === embedUrl)
              )
            );
          }
        }}
      />

      {uploading && (
        <div className="text-text-muted text-xs animate-pulse">{t("post.editor.media.uploading")}</div>
      )}

      <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
        <input
          type="checkbox"
          checked={isMakingVideo}
          onChange={(e) => onIsMakingVideoChange(e.target.checked)}
          className="accent-primary"
        />
        {t("post.makingVideoLabel")}
      </label>

      <div className="card">
        <MediaToolbar
          onImageSelect={onFiles}
          onGifSelect={onGif}
          onEmojiInsert={onEmojiInsert}
          onEmbedAdd={onEmbedAdd}
          onLocationClick={() => {
            const name = prompt(t("post.locationPrompt"));
            if (name) onLocationManualEntry(name);
          }}
          scheduledAt={scheduledAt}
          onScheduleChange={onScheduledAtChange}
          onTagFocus={() => tagRef.current?.scrollIntoView({ behavior: "smooth" })}
          disabled={uploading || submitting}
        />
      </div>

      <div ref={tagRef as React.Ref<HTMLDivElement>}>
        <label className="block text-sm text-text-secondary mb-1">{t("post.tags")}</label>
        <TagAutocomplete tags={tags} onTagsChange={onTagsChange} />
      </div>
    </section>
  );
}
