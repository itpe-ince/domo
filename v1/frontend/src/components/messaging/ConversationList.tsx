"use client";

import { ConversationView } from "@/lib/api";
import { useI18n } from "@/i18n";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { MessageCircleIcon } from "@/components/icons";

interface ConversationListProps {
  conversations: ConversationView[];
  selectedId?: string;
  onSelect: (conv: ConversationView) => void;
  loading?: boolean;
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  loading,
}: ConversationListProps) {
  const { t } = useI18n();

  if (loading) {
    return (
      <div className="space-y-1 p-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3 rounded-xl animate-pulse">
            <div className="w-10 h-10 rounded-full bg-surface-hover flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="h-4 w-1/2 bg-surface-hover rounded mb-1.5" />
              <div className="h-3 w-3/4 bg-surface-hover rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 px-4 text-center">
        <MessageCircleIcon className="w-10 h-10 text-text-muted opacity-40" />
        <p className="text-sm text-text-muted">{t("messaging.list.empty")}</p>
      </div>
    );
  }

  return (
    <ul className="py-1" role="listbox" aria-label={t("messaging.list.title")}>
      {conversations.map((conv) => {
        const isSelected = conv.id === selectedId;
        return (
          <li key={conv.id}>
            <button
              role="option"
              aria-selected={isSelected}
              onClick={() => onSelect(conv)}
              className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors ${
                isSelected
                  ? "bg-surface-hover"
                  : "hover:bg-surface-hover/60"
              }`}
            >
              {/* Avatar placeholder */}
              <div
                className="w-10 h-10 rounded-full bg-border flex items-center justify-center flex-shrink-0 mt-0.5"
                aria-hidden="true"
              >
                <MessageCircleIcon className="w-5 h-5 text-text-muted" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-medium text-sm text-text-primary truncate">
                    {conv.other_user_id.slice(0, 8)}
                  </span>
                  {conv.last_message_at && (
                    <span className="text-xs text-text-muted flex-shrink-0">
                      {formatRelativeTime(conv.last_message_at)}
                    </span>
                  )}
                </div>
                {conv.last_message_preview && (
                  <p className="text-xs text-text-muted truncate mt-0.5">
                    {conv.closed_by_admin
                      ? t("messaging.conversation.closed")
                      : conv.last_message_preview}
                  </p>
                )}
                {!conv.last_message_preview && (
                  <p className="text-xs text-text-muted mt-0.5 italic">
                    {t("messaging.list.noMessages")}
                  </p>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
