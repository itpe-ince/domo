"use client";

/**
 * DraftRestoreDialog — editor-draft-autosave PDCA.
 *
 * Shown on /posts/new mount when localStorage has a saved draft OR
 * the URL has ?draft=id. Per Q-5 decision, when both local and server
 * drafts exist, the more recent one (by savedAt) is the recommended
 * restore target.
 */

import { useI18n } from "@/i18n";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import type { DraftState } from "@/lib/hooks/useDraftAutosave";

export interface DraftRestoreSource {
  state: DraftState;
  savedAt: string; // ISO 8601
  id?: string;
}

interface DraftRestoreDialogProps {
  open: boolean;
  localDraft: DraftRestoreSource | null;
  serverDraft: DraftRestoreSource | null;
  onRestore: (state: DraftState, sourceId?: string) => void;
  /** "새로 작성" — discard local only, keep server draft (still in /posts/drafts list) */
  onDiscard: () => void;
  /** "둘 다 삭제" — discard local + delete server */
  onDiscardAll?: () => void;
}

export function DraftRestoreDialog({
  open,
  localDraft,
  serverDraft,
  onRestore,
  onDiscard,
  onDiscardAll,
}: DraftRestoreDialogProps) {
  const { t } = useI18n();

  if (!open) return null;
  if (!localDraft && !serverDraft) return null;

  // Q-5: pick the newer one as the recommended option.
  const both = localDraft && serverDraft;
  const newer =
    both && new Date(localDraft.savedAt) >= new Date(serverDraft.savedAt)
      ? { source: localDraft, label: "local" as const }
      : both
        ? { source: serverDraft, label: "server" as const }
        : localDraft
          ? { source: localDraft, label: "local" as const }
          : { source: serverDraft!, label: "server" as const };

  const older = both
    ? newer.label === "local"
      ? { source: serverDraft, label: "server" as const }
      : { source: localDraft, label: "local" as const }
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="draft-restore-title"
    >
      <div
        className="w-full max-w-md bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-6 pt-5 pb-2">
          <h2
            id="draft-restore-title"
            className="text-lg font-bold text-text-primary"
          >
            {t("post.draft.restoreDialog.title")}
          </h2>
          <p className="text-text-muted text-xs mt-1">
            {t("post.draft.restoreDialog.body")}
          </p>
        </header>

        <div className="px-6 py-3 space-y-2">
          <DraftSourceRow
            recommended
            source={newer.source}
            label={newer.label}
          />
          {older && (
            <DraftSourceRow
              source={older.source}
              label={older.label}
            />
          )}
        </div>

        <div className="px-6 pb-4 pt-2 flex flex-col gap-2">
          <button
            type="button"
            onClick={() => onRestore(newer.source.state, newer.source.id)}
            className="btn-primary text-sm w-full py-2.5"
            autoFocus
          >
            {both
              ? t("post.draft.restoreDialog.continueRecommended")
              : t("post.draft.restoreDialog.continue")}
          </button>

          {older && (
            <button
              type="button"
              onClick={() => onRestore(older.source.state, older.source.id)}
              className="text-sm text-text-secondary border border-border rounded-full px-3 py-2 hover:bg-surface-hover w-full"
            >
              {t("post.draft.restoreDialog.restorePrevious")}
            </button>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onDiscard}
              className="text-sm text-text-secondary border border-border rounded-full px-3 py-2 hover:bg-surface-hover flex-1"
            >
              {t("post.draft.restoreDialog.discard")}
            </button>
            {onDiscardAll && both && (
              <button
                type="button"
                onClick={onDiscardAll}
                className="text-sm text-danger border border-danger/40 rounded-full px-3 py-2 hover:bg-danger/10 flex-1"
              >
                {t("post.draft.restoreDialog.discardAll")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DraftSourceRow({
  source,
  label,
  recommended = false,
}: {
  source: DraftRestoreSource;
  label: "local" | "server";
  recommended?: boolean;
}) {
  const sourceLabel = label === "local" ? "로컬 저장" : "서버 저장";
  const title = source.state.title || source.state.content || "(제목 없음)";
  const truncated = title.length > 50 ? title.slice(0, 50) + "…" : title;

  return (
    <div
      className={`rounded-lg border p-3 text-xs ${
        recommended
          ? "border-primary/50 bg-primary/5"
          : "border-border bg-surface-hover/30"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={`font-semibold ${recommended ? "text-primary" : "text-text-secondary"}`}
        >
          {recommended && "✓ "}
          {sourceLabel}
        </span>
        <span className="text-text-muted">
          {formatRelativeTime(source.savedAt)}
        </span>
      </div>
      <p className="text-text-primary truncate">{truncated}</p>
    </div>
  );
}
