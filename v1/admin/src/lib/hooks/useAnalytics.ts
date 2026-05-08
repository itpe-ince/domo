"use client";

/**
 * useAnalytics — Phase 12 B-2 분석 대시보드 hooks.
 *
 * admin app에 TanStack Query 미설치 → useState + useEffect 패턴.
 * 각 카드가 독립적으로 period를 전달받아 개별 fetch.
 */

import { useCallback, useEffect, useState } from "react";
import {
  AnalyticsPeriod,
  CohortRetentionResponse,
  NewsletterOpenRateResponse,
  FeedCTRResponse,
  AIFeaturesUsageResponse,
  fetchCohortRetention,
  fetchNewsletterOpenRate,
  fetchFeedCTR,
  fetchAIFeaturesUsage,
} from "@/lib/api";

interface AnalyticsState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  cachedAt: string | null;
}

function _initialState<T>(): AnalyticsState<T> {
  return { data: null, loading: true, error: null, cachedAt: null };
}

// ── 1. Cohort Retention ───────────────────────────────────────────────────────

export function useAnalyticsCohortRetention(period: AnalyticsPeriod, bust = false) {
  const [state, setState] = useState<AnalyticsState<CohortRetentionResponse>>(_initialState());

  const load = useCallback(
    async (forceBust = false) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await fetchCohortRetention(period, forceBust);
        setState({
          data: res,
          loading: false,
          error: null,
          cachedAt: res._cachedAt ?? null,
        });
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : "데이터를 불러오지 못했습니다",
        }));
      }
    },
    [period]
  );

  useEffect(() => {
    void load(bust);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, bust]);

  return { ...state, refetch: (b = false) => void load(b) };
}

// ── 2. Newsletter Open Rate ───────────────────────────────────────────────────

export function useAnalyticsNewsletterOpenRate(period: AnalyticsPeriod, bust = false) {
  const [state, setState] = useState<AnalyticsState<NewsletterOpenRateResponse>>(_initialState());

  const load = useCallback(
    async (forceBust = false) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await fetchNewsletterOpenRate(period, forceBust);
        setState({
          data: res,
          loading: false,
          error: null,
          cachedAt: res._cachedAt ?? null,
        });
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : "데이터를 불러오지 못했습니다",
        }));
      }
    },
    [period]
  );

  useEffect(() => {
    void load(bust);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, bust]);

  return { ...state, refetch: (b = false) => void load(b) };
}

// ── 3. Feed CTR ───────────────────────────────────────────────────────────────

export function useAnalyticsFeedCTR(period: AnalyticsPeriod, bust = false) {
  const [state, setState] = useState<AnalyticsState<FeedCTRResponse>>(_initialState());

  const load = useCallback(
    async (forceBust = false) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await fetchFeedCTR(period, forceBust);
        setState({
          data: res,
          loading: false,
          error: null,
          cachedAt: res._cachedAt ?? null,
        });
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : "데이터를 불러오지 못했습니다",
        }));
      }
    },
    [period]
  );

  useEffect(() => {
    void load(bust);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, bust]);

  return { ...state, refetch: (b = false) => void load(b) };
}

// ── 4. AI Features Usage ─────────────────────────────────────────────────────

export function useAnalyticsAIFeaturesUsage(period: AnalyticsPeriod, bust = false) {
  const [state, setState] = useState<AnalyticsState<AIFeaturesUsageResponse>>(_initialState());

  const load = useCallback(
    async (forceBust = false) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await fetchAIFeaturesUsage(period, forceBust);
        setState({
          data: res,
          loading: false,
          error: null,
          cachedAt: res._cachedAt ?? null,
        });
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : "데이터를 불러오지 못했습니다",
        }));
      }
    },
    [period]
  );

  useEffect(() => {
    void load(bust);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, bust]);

  return { ...state, refetch: (b = false) => void load(b) };
}
