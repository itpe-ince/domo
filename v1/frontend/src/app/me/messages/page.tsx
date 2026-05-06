"use client";

import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useConversations } from "@/lib/hooks/useConversations";
import { ConversationList } from "@/components/messaging/ConversationList";
import { ConversationView } from "@/lib/api";
import { MessageCircleIcon } from "@/components/icons";

export default function MessagesPage() {
  const router = useRouter();
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const { conversations, loading, error, refresh } = useConversations();

  function handleSelect(conv: ConversationView) {
    router.push(`/me/messages/${conv.id}`);
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
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">{t("messaging.list.title")}</h1>
        <button
          onClick={refresh}
          className="text-xs text-text-muted hover:text-primary transition-colors"
          aria-label={t("messaging.list.refresh")}
        >
          {t("messaging.list.refresh")}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-danger p-4 m-4 text-danger text-sm">
          {error}
        </div>
      )}

      {/* Conversation list */}
      <ConversationList
        conversations={conversations}
        onSelect={handleSelect}
        loading={meLoading || loading}
      />
    </main>
  );
}
