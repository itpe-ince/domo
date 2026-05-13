"use client";

/**
 * EditorTopBar — 데스크탑 전용 sticky 툴바.
 *
 * EditorWorkspace 내부에 있던 sticky header(line 192-296)를 grid 컨테이너
 * 바깥으로 끌어내어 편집(3fr) + 미리보기(2fr) 전체 폭에 걸치도록 분리.
 *
 * 포함 요소:
 *   - 등록 제목 + AutosaveIndicator
 *   - PostType segmented control (일반 / 상품)
 *   - PreviewToggleButton
 *   - 발행 옵션 버튼
 *   - 임시저장 목록 링크
 *   - 임시저장 버튼
 *   - 등록 버튼
 *
 * 모바일: 렌더 자체는 하지 않음 (부모에서 hidden md:block으로 래핑).
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import { type ApiUser } from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import type { DraftSaveStatus } from "@/lib/hooks/useDraftAutosave";
import type { PostFormSetters } from "@/lib/hooks/usePostFormState";
import { PreviewToggleButton } from "@/components/post-editor/PreviewToggleButton";

export interface EditorTopBarProps {
  // 사용자
  me: ApiUser | null;
  // 포스트 타입
  type: "general" | "product";
  setters: Pick<PostFormSetters, "setType">;
  // 업로드/제출 상태
  uploading: boolean;
  submitting: boolean;
  // 임시저장
  draftStatus: DraftSaveStatus;
  lastSavedAt: Date | null;
  onManualSave: () => void | Promise<void>;
  // 등록
  onSubmit: () => void | Promise<void>;
  scheduledAt: string;
  // 미리보기 토글
  isPreviewVisible: boolean;
  onTogglePreview: () => void;
  // 발행 옵션
  onPublishOptionsClick: () => void;
}

export function EditorTopBar({
  me,
  type,
  setters,
  uploading,
  submitting,
  draftStatus,
  lastSavedAt,
  onManualSave,
  onSubmit,
  scheduledAt,
  isPreviewVisible,
  onTogglePreview,
  onPublishOptionsClick,
}: EditorTopBarProps) {
  const { t } = useI18n();

  return (
    <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-2 flex flex-wrap items-center justify-between gap-2">
      {/* 좌측: 등록 제목 + PostType segmented control */}
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="text-base font-bold leading-tight">{t("post.createTitle")}</h1>

        {me && (
          <div className="flex bg-surface rounded-full p-0.5 border border-border">
            <button
              type="button"
              onClick={() => setters.setType("general")}
              disabled={uploading || submitting}
              className={`px-3 py-1 rounded-full text-xs transition-colors disabled:opacity-60 ${
                type === "general"
                  ? "bg-primary text-background"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {t("post.generalPost")}
            </button>
            <button
              type="button"
              onClick={() => {
                const canCreate = me.role === "artist" || me.role === "admin";
                if (canCreate) setters.setType("product");
              }}
              disabled={
                uploading ||
                submitting ||
                !(me.role === "artist" || me.role === "admin")
              }
              aria-disabled={!(me.role === "artist" || me.role === "admin")}
              title={
                !(me.role === "artist" || me.role === "admin")
                  ? t("post.type.product.disabledTitle")
                  : undefined
              }
              className={`px-3 py-1 rounded-full text-xs transition-colors ${
                !(me.role === "artist" || me.role === "admin")
                  ? "opacity-60 cursor-not-allowed text-text-muted"
                  : type === "product"
                    ? "bg-primary text-background"
                    : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {t("post.productPost")}
            </button>
          </div>
        )}
      </div>

      {/* 우측: 액션 버튼들 */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* AutosaveIndicator — 미리보기 토글 좌측에 위치 */}
        <AutosaveIndicator status={draftStatus} lastSavedAt={lastSavedAt} t={t} />

        {/* 미리보기 토글 */}
        <PreviewToggleButton isVisible={isPreviewVisible} onToggle={onTogglePreview} />

        {/* 발행 옵션 Drawer 트리거 */}
        <button
          type="button"
          onClick={onPublishOptionsClick}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border text-sm font-medium hover:bg-surface-hover transition-colors"
        >
          ⚙️ {t("post.editor.publishOptions.title")}
        </button>

        {/* 임시저장 목록 링크 */}
        <Link
          href="/posts/drafts"
          className="text-xs text-text-muted hover:text-primary transition-colors hidden sm:inline"
        >
          {t("post.draft.list.title")}
        </Link>

        {/* 임시저장 버튼 */}
        {me && (
          <button
            onClick={onManualSave}
            disabled={draftStatus === "saving" || submitting}
            className="text-sm text-text-secondary border border-border rounded-full px-3 py-1.5 hover:bg-surface-hover disabled:opacity-40 transition-colors"
          >
            {draftStatus === "saving"
              ? t("post.draft.savingIndicator")
              : t("post.draft.saveButton")}
          </button>
        )}

        {/* 등록 버튼 */}
        <button
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
      </div>
    </div>
  );
}

// ─── AutosaveIndicator ───────────────────────────────────────────────────────
// EditorWorkspace에서 EditorTopBar로 이동. EditorTopBar만 사용하므로 여기서 colocate.
function AutosaveIndicator({
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
