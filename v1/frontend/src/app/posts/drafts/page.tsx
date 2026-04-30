"use client";

/**
 * /posts/drafts — editor-draft-autosave PDCA (#2 sub-PDCA).
 *
 * Lists the current user's saved drafts. Each card supports "이어쓰기"
 * (open in editor with ?draft=id) and "삭제".
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { LoginModal } from "@/components/LoginModal";
import { useI18n } from "@/i18n";
import {
  ApiClientError,
  type Draft,
  deleteDraft,
  listDrafts,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { useMe } from "@/lib/useMe";

export const dynamic = "force-dynamic";

export default function DraftsPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      setLoading(false);
      setLoginOpen(true);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    listDrafts()
      .then((items) => {
        if (!cancelled) setDrafts(items);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof ApiClientError ? `${e.code}: ${e.message}` : "Failed"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [me?.id, meLoading]);

  async function handleDelete(id: string) {
    // Optimistic UI update
    setDrafts((prev) => (prev ? prev.filter((d) => d.id !== id) : prev));
    try {
      await deleteDraft(id);
    } catch (e) {
      // Reload on failure to keep UI honest
      try {
        const reloaded = await listDrafts();
        setDrafts(reloaded);
      } catch {
        /* silent */
      }
      setError(
        e instanceof ApiClientError ? `${e.code}: ${e.message}` : "Delete failed"
      );
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">{t("post.draft.list.title")}</h1>
      </div>

      {!me && !meLoading && (
        <LoginModal
          open={loginOpen}
          onClose={() => setLoginOpen(false)}
          redirectTo="/posts/drafts"
        />
      )}

      {error && (
        <div className="mx-4 mt-4 card border-danger p-3 text-danger text-sm">
          {error}
        </div>
      )}

      {me && (
        <div className="p-4 space-y-3">
          {loading && (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-20 rounded-lg bg-surface-hover/40 animate-pulse"
                  aria-hidden
                />
              ))}
            </div>
          )}

          {!loading && drafts !== null && drafts.length === 0 && (
            <div className="flex flex-col items-center gap-4 py-16 text-text-muted">
              <span className="text-4xl" aria-hidden>
                📝
              </span>
              <p className="text-sm">{t("post.draft.list.empty")}</p>
              <Link href="/posts/new" className="btn-primary text-sm">
                {t("post.draft.list.newPost")}
              </Link>
            </div>
          )}

          {!loading &&
            drafts &&
            drafts.length > 0 &&
            drafts.map((d) => (
              <DraftCard key={d.id} draft={d} onDelete={handleDelete} t={t} />
            ))}
        </div>
      )}
    </main>
  );
}

function DraftCard({
  draft,
  onDelete,
  t,
}: {
  draft: Draft;
  onDelete: (id: string) => void;
  t: (key: string) => string;
}) {
  const titleRaw = draft.title || draft.content || "";
  const title =
    titleRaw.length > 80 ? titleRaw.slice(0, 80) + "…" : titleRaw;
  const displayTitle = title || t("post.draft.card.untitled");
  const thumbnail = draft.media.find((m) => m.type === "image");
  const typeLabel =
    draft.type === "product"
      ? t("post.draft.card.typeProduct")
      : t("post.draft.card.typeGeneral");

  return (
    <article className="card p-3 flex items-center gap-3">
      {/* Thumbnail */}
      <div className="w-16 h-16 rounded bg-surface-hover flex-shrink-0 overflow-hidden">
        {thumbnail ? (
          <img
            src={thumbnail.thumbnail_url || thumbnail.url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-text-muted text-xs">
            {typeLabel}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] uppercase tracking-wider text-text-muted bg-surface-hover px-1.5 py-0.5 rounded">
            {typeLabel}
          </span>
          <span className="text-xs text-text-muted">
            {formatRelativeTime(draft.updated_at)}
          </span>
        </div>
        <p className="text-sm text-text-primary truncate">{displayTitle}</p>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-1 flex-shrink-0">
        <Link
          href={`/posts/new?draft=${encodeURIComponent(draft.id)}`}
          className="text-xs text-primary border border-primary/30 rounded-full px-3 py-1 hover:bg-primary/10 text-center"
        >
          {t("post.draft.card.openInEditor")}
        </Link>
        <button
          type="button"
          onClick={() => onDelete(draft.id)}
          className="text-xs text-danger border border-danger/30 rounded-full px-3 py-1 hover:bg-danger/10"
        >
          {t("post.draft.card.delete")}
        </button>
      </div>
    </article>
  );
}
