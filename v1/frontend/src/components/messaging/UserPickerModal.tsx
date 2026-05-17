"use client";

/**
 * UserPickerModal — search-and-pick modal for starting DMs or any user-target action.
 *
 * Responsibilities:
 *  - Debounced GET /users/search (>=2 chars)
 *  - Render results, click → onPick(userId)
 *  - ESC to close, backdrop click to close
 *  - Filters out the current user (cannot DM self)
 *
 * Parent owns the modal `open` state and decides what to do on `onPick`.
 * MessagesPage uses it to call startConversation + router.push.
 */

import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import {
  ApiClientError,
  UserSearchResult,
  searchUsers,
} from "@/lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  onPick: (user: UserSearchResult) => void;
  /** Optional override title */
  title?: string;
};

export function UserPickerModal({ open, onClose, onPick, title }: Props) {
  const { t } = useI18n();
  const { me } = useMe();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ESC to close + auto-focus on open
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    // Focus shortly after mount so it works on dynamic mount
    const tid = setTimeout(() => inputRef.current?.focus(), 50);
    return () => {
      window.removeEventListener("keydown", handler);
      clearTimeout(tid);
    };
  }, [open, onClose]);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setQ("");
      setResults([]);
      setError(null);
    }
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (!open) return;
    const term = q.trim();
    if (term.length < 2) {
      setResults([]);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const tid = setTimeout(async () => {
      try {
        const list = await searchUsers(term, { limit: 20 });
        if (cancelled) return;
        // 본인 제외
        setResults(me ? list.filter((u) => u.id !== me.id) : list);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiClientError ? e.message : "Search failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(tid);
    };
  }, [q, open, me]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title || t("messaging.compose.modalTitle")}
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 pt-20"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md mx-auto p-4 space-y-3 max-h-[70vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-text-primary">
            {title || t("messaging.compose.modalTitle")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("common.close")}
            className="text-text-muted hover:text-text-primary text-xl leading-none px-2"
          >
            ×
          </button>
        </div>

        <input
          ref={inputRef}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("messaging.compose.searchPlaceholder")}
          aria-label={t("messaging.compose.searchPlaceholder")}
          className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
        />

        <div className="flex-1 overflow-y-auto min-h-[120px]">
          {error && (
            <div className="text-danger text-sm py-3 text-center">{error}</div>
          )}
          {!error && q.trim().length < 2 && (
            <div className="text-text-muted text-xs py-4 text-center">
              {t("messaging.compose.searchHint")}
            </div>
          )}
          {!error && q.trim().length >= 2 && loading && (
            <div className="text-text-muted text-xs py-4 text-center">
              {t("common.loading")}
            </div>
          )}
          {!error && q.trim().length >= 2 && !loading && results.length === 0 && (
            <div className="text-text-muted text-xs py-4 text-center">
              {t("messaging.compose.empty")}
            </div>
          )}
          {results.length > 0 && (
            <ul className="space-y-1">
              {results.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => onPick(u)}
                    className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-surface-hover text-left transition-colors"
                  >
                    <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold flex-shrink-0 overflow-hidden">
                      {u.avatar_url ? (
                        <img
                          src={u.avatar_url}
                          alt=""
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        u.display_name.charAt(0).toUpperCase()
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-text-primary truncate">
                        @{u.display_name}
                        {u.role === "artist" && (
                          <span className="text-xs text-primary ml-1.5">✓</span>
                        )}
                      </div>
                      {u.bio && (
                        <div className="text-xs text-text-muted truncate">
                          {u.bio}
                        </div>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
