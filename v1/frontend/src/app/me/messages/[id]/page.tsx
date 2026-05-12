"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import {
  MessageView,
  listMessages,
  sendMessage,
  editMessage,
  deleteMessage,
  markConversationRead,
  reportConversation,
} from "@/lib/api";
import { MessageBubble } from "@/components/messaging/MessageBubble";
import { MessageComposer } from "@/components/messaging/MessageComposer";

const POLL_INTERVAL_MS = 5_000; // 5 seconds for message list

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t } = useI18n();
  const { me, loading: meLoading } = useMe();

  const [messages, setMessages] = useState<MessageView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [editingMsg, setEditingMsg] = useState<MessageView | null>(null);
  const [reportReason, setReportReason] = useState("");
  const [showReport, setShowReport] = useState(false);
  const [reportSent, setReportSent] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMessages = useCallback(async (reset = false) => {
    if (!id) return;
    try {
      const resp = await listMessages(id, null, 30);
      if (!mountedRef.current) return;
      if (reset) {
        setMessages(resp.data);
      } else {
        setMessages((prev) => {
          const existing = new Set(prev.map((m) => m.id));
          const newMsgs = resp.data.filter((m) => !existing.has(m.id));
          return newMsgs.length > 0 ? [...newMsgs, ...prev] : prev;
        });
      }
      setNextCursor(resp.next_cursor);
      setError(null);
    } catch (e) {
      if (mountedRef.current) {
        setError(e instanceof Error ? e.message : t("common.error"));
      }
    }
  }, [id, t]);

  // Initial load + mark read
  useEffect(() => {
    if (meLoading || !me || !id) return;
    mountedRef.current = true;
    setLoading(true);
    void fetchMessages(true).then(() => {
      if (mountedRef.current) setLoading(false);
      // Mark as read after loading
      void markConversationRead(id).catch(() => {});
    });
    return () => {
      mountedRef.current = false;
    };
  }, [id, me, meLoading, fetchMessages]);

  // Polling
  useEffect(() => {
    if (!id || !me) return;
    timerRef.current = setInterval(() => {
      if (document.visibilityState === "visible") {
        void fetchMessages(false);
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [id, me, fetchMessages]);

  // Scroll to bottom on initial load
  useEffect(() => {
    if (!loading && messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [loading]);

  async function handleSend(body: string) {
    if (!id) return;
    const msg = await sendMessage(id, body);
    setMessages((prev) => [msg, ...prev]);
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  async function handleEdit(msg: MessageView) {
    setEditingMsg(msg);
  }

  async function handleEditSubmit(body: string) {
    if (!editingMsg || !id) return;
    const updated = await editMessage(id, editingMsg.id, body);
    setMessages((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
    setEditingMsg(null);
  }

  async function handleDelete(msg: MessageView) {
    if (!id) return;
    const updated = await deleteMessage(id, msg.id);
    setMessages((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
  }

  async function handleReport() {
    if (!id || !reportReason.trim()) return;
    await reportConversation(id, reportReason.trim());
    setReportSent(true);
    setShowReport(false);
  }

  async function loadMore() {
    if (!id || !nextCursor) return;
    const resp = await listMessages(id, nextCursor, 30);
    setMessages((prev) => {
      const ids = new Set(prev.map((m) => m.id));
      const older = resp.data.filter((m) => !ids.has(m.id));
      return [...prev, ...older];
    });
    setNextCursor(resp.next_cursor);
  }

  if (!meLoading && !me) {
    return (
      <main className="flex-1 flex items-center justify-center text-text-muted p-8">
        <p className="text-sm">{t("messaging.loginRequired")}</p>
      </main>
    );
  }

  // Messages are stored newest-first from API; display oldest-first
  const displayMsgs = [...messages].reverse();

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto flex flex-col h-full">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/me/messages")}
          className="text-text-muted hover:text-text-primary transition-colors text-sm"
          aria-label={t("common.back")}
        >
          ←
        </button>
        <h1 className="flex-1 font-semibold text-base truncate">
          {t("messaging.conversation.title")}
        </h1>
        <button
          onClick={() => setShowReport(true)}
          className="text-xs text-text-muted hover:text-danger transition-colors"
          aria-label={t("messaging.conversation.report")}
        >
          {t("messaging.conversation.report")}
        </button>
      </div>

      {/* Report sent banner */}
      {reportSent && (
        <div className="bg-success/10 text-success text-xs px-4 py-2">
          {t("messaging.conversation.reportSent")}
        </div>
      )}

      {/* Report modal */}
      {showReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="bg-background rounded-2xl p-6 w-full max-w-sm space-y-4">
            <h2 className="font-semibold">{t("messaging.conversation.reportTitle")}</h2>
            <textarea
              value={reportReason}
              onChange={(e) => setReportReason(e.target.value)}
              placeholder={t("messaging.conversation.reportPlaceholder")}
              rows={4}
              maxLength={500}
              className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowReport(false)}
                className="px-4 py-2 text-sm text-text-muted hover:text-text-primary"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={() => void handleReport()}
                disabled={!reportReason.trim()}
                className="px-4 py-2 text-sm bg-danger text-white rounded-xl disabled:opacity-40 hover:bg-danger/90 transition-colors"
              >
                {t("messaging.conversation.reportSubmit")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {/* Load more older messages */}
        {nextCursor && (
          <div className="text-center mb-4">
            <button
              onClick={() => void loadMore()}
              className="text-xs text-text-muted hover:text-primary transition-colors"
            >
              {t("messaging.conversation.loadMore")}
            </button>
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}
              >
                <div className="h-10 w-48 bg-surface-hover rounded-2xl animate-pulse" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="card border-danger p-4 text-danger text-sm">{error}</div>
        ) : displayMsgs.length === 0 ? (
          <div className="text-center text-text-muted text-sm py-12">
            {t("messaging.conversation.empty")}
          </div>
        ) : (
          <div className="space-y-3">
            {displayMsgs.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isOwn={msg.sender_id === me?.id}
                onEdit={me?.id === msg.sender_id ? handleEdit : undefined}
                onDelete={me?.id === msg.sender_id ? handleDelete : undefined}
              />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer — edit mode or normal send */}
      {editingMsg ? (
        <MessageComposer
          onSend={handleEditSubmit}
          initialValue={editingMsg.body}
          onCancel={() => setEditingMsg(null)}
          submitLabel={t("common.save")}
          placeholder={t("messaging.composer.editPlaceholder")}
        />
      ) : (
        <MessageComposer
          onSend={handleSend}
          placeholder={t("messaging.composer.placeholder")}
        />
      )}
    </main>
  );
}
