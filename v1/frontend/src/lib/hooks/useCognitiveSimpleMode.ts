"use client";

/**
 * useCognitiveSimpleMode — Phase 9 L-E
 *
 * localStorage 우선 로딩 → API 동기화 (로그인 시).
 * 비로그인: localStorage 전용 (새로고침 유지).
 * 로그인: localStorage + DB 양방향 동기화.
 *
 * API 실패 시 localStorage 상태 유지 (graceful degradation).
 */
import { useCallback, useEffect, useState } from "react";
import { fetchMe, tokenStore } from "@/lib/api";

const LS_KEY = "cognitive_simple_mode";

async function patchMeAccessibility(cognitive_simple_mode: boolean): Promise<void> {
  const token = tokenStore.get();
  if (!token) return;
  const API_BASE =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:3710/v1";
  await fetch(`${API_BASE}/users/me`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ cognitive_simple_mode }),
  });
}

export function useCognitiveSimpleMode() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(LS_KEY) === "true";
  });

  // DB → localStorage 동기화 (로그인 후 최초 로딩)
  useEffect(() => {
    if (!tokenStore.get()) return;
    fetchMe()
      .then((user) => {
        // ApiUser에 cognitive_simple_mode가 없으면 undefined → false
        const dbValue = (user as unknown as Record<string, unknown>).cognitive_simple_mode;
        if (typeof dbValue === "boolean") {
          setEnabled(dbValue);
          if (typeof window !== "undefined") {
            localStorage.setItem(LS_KEY, String(dbValue));
          }
        }
      })
      .catch(() => {
        // 비로그인 또는 API 오류 시 localStorage 값 유지
      });
  }, []);

  // html 요소에 data-simple-mode 속성 동기화
  useEffect(() => {
    if (typeof document === "undefined") return;
    const html = document.documentElement;
    if (enabled) {
      html.setAttribute("data-simple-mode", "true");
    } else {
      html.removeAttribute("data-simple-mode");
    }
  }, [enabled]);

  const toggle = useCallback(async (next: boolean) => {
    setEnabled(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(LS_KEY, String(next));
    }
    try {
      await patchMeAccessibility(next);
    } catch {
      // API 실패 시 localStorage 상태 유지 (rollback 없음)
    }
  }, []);

  return { enabled, toggle };
}
