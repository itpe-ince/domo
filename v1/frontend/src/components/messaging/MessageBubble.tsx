"use client";

import { MessageView } from "@/lib/api";
import { useI18n } from "@/i18n";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

interface MessageBubbleProps {
  message: MessageView;
  isOwn: boolean;
  onEdit?: (msg: MessageView) => void;
  onDelete?: (msg: MessageView) => void;
}

export function MessageBubble({
  message,
  isOwn,
  onEdit,
  onDelete,
}: MessageBubbleProps) {
  const { t } = useI18n();
  const isDeleted = !!message.deleted_at;

  const canEdit =
    isOwn &&
    !isDeleted &&
    // Within 5-minute edit window check (client-side approximation)
    Date.now() - new Date(message.created_at).getTime() < 5 * 60 * 1000;

  return (
    <div
      className={`flex flex-col gap-0.5 ${isOwn ? "items-end" : "items-start"}`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words ${
          isDeleted
            ? "bg-surface-hover text-text-muted italic"
            : isOwn
            ? "bg-primary text-white"
            : "bg-surface-hover text-text-primary"
        }`}
      >
        {isDeleted ? t("messaging.message.deleted") : message.body}
      </div>

      {/* Meta: timestamp + edit/delete actions */}
      <div className={`flex items-center gap-2 px-1 ${isOwn ? "flex-row-reverse" : ""}`}>
        <span className="text-xs text-text-muted">
          {formatRelativeTime(message.created_at)}
          {message.edited_at && !isDeleted && (
            <span className="ml-1 opacity-70">
              ({t("messaging.message.edited")})
            </span>
          )}
          {isOwn && message.read_at && !isDeleted && (
            <span className="ml-1 opacity-70">{t("messaging.message.read")}</span>
          )}
        </span>

        {isOwn && !isDeleted && (canEdit || onDelete) && (
          <div className={`flex gap-1 ${isOwn ? "" : "flex-row-reverse"}`}>
            {canEdit && onEdit && (
              <button
                onClick={() => onEdit(message)}
                className="text-xs text-text-muted hover:text-primary transition-colors"
                aria-label={t("messaging.message.editAriaLabel")}
              >
                {t("common.edit")}
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(message)}
                className="text-xs text-text-muted hover:text-danger transition-colors"
                aria-label={t("messaging.message.deleteAriaLabel")}
              >
                {t("common.delete")}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
