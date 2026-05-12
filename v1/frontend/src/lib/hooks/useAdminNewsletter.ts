"use client";

/**
 * useAdminNewsletter — C-5 newsletter-digest
 *
 * Hook for admin newsletter issue management:
 * compose, list, edit, and send.
 */

import { useCallback, useEffect, useState } from "react";
import {
  NewsletterIssueOut,
  adminComposeNewsletterIssue,
  adminListNewsletterIssues,
  adminPatchNewsletterIssue,
  adminSendNewsletterIssue,
} from "@/lib/api";

export type AdminNewsletterState = {
  issues: NewsletterIssueOut[];
  loading: boolean;
  error: string | null;
  composing: boolean;
  composeError: string | null;
  compose: (params: { issue_date: string; locale: string }) => Promise<NewsletterIssueOut | null>;
  loadIssues: (params?: { status?: string; locale?: string; limit?: number }) => void;
  patchIssue: (id: string, body: { subject?: string; body_markdown?: string }) => Promise<NewsletterIssueOut | null>;
  sendIssue: (id: string) => Promise<NewsletterIssueOut | null>;
  sending: string | null; // id of issue being sent
};

export function useAdminNewsletter(): AdminNewsletterState {
  const [issues, setIssues] = useState<NewsletterIssueOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [composing, setComposing] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [sending, setSending] = useState<string | null>(null);

  const loadIssues = useCallback(
    async (params?: { status?: string; locale?: string; limit?: number }) => {
      setLoading(true);
      setError(null);
      try {
        const data = await adminListNewsletterIssues(params);
        setIssues(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "뉴스레터 목록 로드 실패");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    void loadIssues();
  }, [loadIssues]);

  const compose = useCallback(
    async (params: {
      issue_date: string;
      locale: string;
    }): Promise<NewsletterIssueOut | null> => {
      setComposing(true);
      setComposeError(null);
      try {
        const issue = await adminComposeNewsletterIssue(params);
        setIssues((prev) => [issue, ...prev.filter((i) => i.id !== issue.id)]);
        return issue;
      } catch (e) {
        setComposeError(e instanceof Error ? e.message : "뉴스레터 작성 실패");
        return null;
      } finally {
        setComposing(false);
      }
    },
    []
  );

  const patchIssue = useCallback(
    async (
      id: string,
      body: { subject?: string; body_markdown?: string }
    ): Promise<NewsletterIssueOut | null> => {
      try {
        const updated = await adminPatchNewsletterIssue(id, body);
        setIssues((prev) => prev.map((i) => (i.id === id ? updated : i)));
        return updated;
      } catch (e) {
        setError(e instanceof Error ? e.message : "이슈 편집 실패");
        return null;
      }
    },
    []
  );

  const sendIssue = useCallback(
    async (id: string): Promise<NewsletterIssueOut | null> => {
      setSending(id);
      try {
        const updated = await adminSendNewsletterIssue(id);
        setIssues((prev) => prev.map((i) => (i.id === id ? updated : i)));
        return updated;
      } catch (e) {
        setError(e instanceof Error ? e.message : "발송 시작 실패");
        return null;
      } finally {
        setSending(null);
      }
    },
    []
  );

  return {
    issues,
    loading,
    error,
    composing,
    composeError,
    compose,
    loadIssues,
    patchIssue,
    sendIssue,
    sending,
  };
}
