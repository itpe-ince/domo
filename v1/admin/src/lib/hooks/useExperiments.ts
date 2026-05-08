"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiClientError,
  CreateExperimentPayload,
  Experiment,
  ExperimentResults,
  createExperiment,
  getExperimentResults,
  listExperiments,
} from "@/lib/api";

// ── useExperiments: 목록 조회 (30초 자동 갱신) ──────────────────────────────

export function useExperiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listExperiments();
      setExperiments(data);
    } catch {
      setError("실험 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    // 30초 자동 갱신
    intervalRef.current = setInterval(() => {
      void load();
    }, 30_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  return { experiments, isLoading, error, refetch: load };
}

// ── useCreateExperiment: 실험 생성 뮤테이션 ────────────────────────────────

export function useCreateExperiment(onSuccess: () => void) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const submit = useCallback(
    async (payload: CreateExperimentPayload) => {
      setIsSubmitting(true);
      setSubmitError(null);
      try {
        await createExperiment(payload);
        onSuccess();
      } catch (err) {
        if (err instanceof ApiClientError && err.code === "CONFLICT") {
          setSubmitError(
            `'${payload.name}' 이름의 실험이 이미 존재합니다. 다른 이름을 사용해 주세요.`
          );
        } else {
          setSubmitError("실험 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.");
        }
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [onSuccess]
  );

  return { submit, isSubmitting, submitError, setSubmitError };
}

// ── useExperimentResults: 실험 결과 (lazy fetch, enabled 제어) ──────────────

export function useExperimentResults(name: string, enabled: boolean) {
  const [results, setResults] = useState<ExperimentResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !name) return;
    let cancelled = false;
    setIsLoading(true);
    getExperimentResults(name)
      .then((data) => {
        if (!cancelled) setResults(data);
      })
      .catch(() => {
        // 결과 fetch 실패 — PostHogEmbed fallback이 처리
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [name, enabled]);

  return { results, isLoading };
}
