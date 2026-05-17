"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useConversations } from "@/lib/hooks/useConversations";
import { ConversationList } from "@/components/messaging/ConversationList";
import { UserPickerModal } from "@/components/messaging/UserPickerModal";
import { ApiClientError, ConversationView, startConversation } from "@/lib/api";
import { MessageCircleIcon } from "@/components/icons";

export default function MessagesPage() {
  const router = useRouter();
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const { conversations, loading, error, refresh } = useConversations();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  function handleSelect(conv: ConversationView) {
    router.push(`/me/messages/${conv.id}`);
  }

  async function handlePick(user: { id: string }) {
    setStarting(true);
    setStartError(null);
    try {
      const conv = await startConversation(user.id);
      setPickerOpen(false);
      router.push(`/me/messages/${conv.id}`);
    } catch (e) {
      setStartError(
        e instanceof ApiClientError
          ? e.message
          : t("messaging.compose.failed")
      );
    } finally {
      setStarting(false);
    }
  }

  if (!meLoading && !me) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto">
        <div className="card p-12 m-4 text-center text-text-muted">
          <MessageCircleIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">{t("messaging.loginRequired")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between gap-2">
        <h1 className="text-xl font-bold">{t("messaging.list.title")}</h1>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setStartError(null);
              setPickerOpen(true);
            }}
            className="btn-primary text-xs inline-flex items-center gap-1"
            aria-label={t("messaging.compose.newConversation")}
          >
            <span aria-hidden="true">＋</span>
            <span>{t("messaging.compose.newConversation")}</span>
          </button>
          <button
            onClick={refresh}
            className="text-xs text-text-muted hover:text-primary transition-colors"
            aria-label={t("messaging.list.refresh")}
          >
            {t("messaging.list.refresh")}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-danger p-4 m-4 text-danger text-sm">
          {error}
        </div>
      )}
      {startError && (
        <div role="alert" className="card border-danger p-4 m-4 text-danger text-sm">
          {startError}
        </div>
      )}
      {starting && (
        <div className="px-4 py-2 text-text-muted text-xs">
          {t("messaging.compose.starting")}
        </div>
      )}

      {/* Conversation list */}
      <ConversationList
        conversations={conversations}
        onSelect={handleSelect}
        loading={meLoading || loading}
      />

      <UserPickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onPick={handlePick}
      />
    </main>
  );
}
