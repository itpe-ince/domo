/**
 * useSequenceHotkeys — 두 키 시퀀스 단축키 hook
 *
 * Phase 12 C-3: g+h/f/e/m/n/p 등 GitHub/Slack 표준 두 키 시퀀스 패턴 지원.
 * - 첫 번째 키 입력 후 timeoutMs(기본 1000ms) 이내 두 번째 키 입력 시 핸들러 호출
 * - 타임아웃 경과 시 상태 리셋
 * - input/textarea/select/contentEditable 포커스 시 자동 비활성 (preventInInputs 기본 true)
 * - meta/ctrl/alt 조합 키는 시퀀스에서 무시
 * - useGlobalHotkeys(D-1)와 독립 hook — 동일 window keydown 병렬 처리, 충돌 없음
 */

import { useEffect, useRef } from "react";

interface SequenceHotkey {
  /** 두 키 시퀀스. 예: ['g', 'h'] */
  sequence: [string, string];
  /**
   * 두 번째 키 대기 타임아웃(ms).
   * Phase 12 C-3 권장: 1000ms (300ms는 타이핑 속도에 따라 실패율이 높음)
   */
  timeoutMs?: number;
  /** 시퀀스 매치 시 핸들러 */
  handler: (e: KeyboardEvent) => void;
  /**
   * false 로 설정하면 이 시퀀스를 등록하지 않는다.
   * route별 조건부 활성화에 사용. default: true
   */
  enabled?: boolean;
  /**
   * true(default)이면 input/textarea/select/contentEditable 포커스 시
   * 이 핸들러를 건너뛴다.
   */
  preventInInputs?: boolean;
}

/**
 * input/textarea/select/contentEditable 에 포커스가 있을 때
 * 시퀀스 단축키를 차단해야 하는지 확인한다.
 */
function shouldIgnoreSequenceHotkey(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (target.isContentEditable) return true;
  return false;
}

export function useSequenceHotkeys(hotkeys: SequenceHotkey[]): void {
  // 첫 번째 키 입력 상태를 ref로 관리 (리렌더 없이 유지)
  const lastKeyRef = useRef<{ key: string; at: number } | null>(null);
  // 타임아웃 클리어용 ref
  const timeoutIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // meta/ctrl/alt 조합 키는 시퀀스에서 무시
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const now = Date.now();
      const last = lastKeyRef.current;

      // 활성화된 시퀀스 목록 필터링
      const activeHotkeys = hotkeys.filter((h) => h.enabled !== false);

      const inInput = shouldIgnoreSequenceHotkey(e.target);

      // 첫 번째 키 집합
      const firstKeys = new Set(activeHotkeys.map((h) => h.sequence[0].toLowerCase()));

      if (last === null) {
        // 첫 번째 키 대기 상태
        if (firstKeys.has(e.key.toLowerCase())) {
          if (inInput) return; // 입력 포커스 시 차단
          lastKeyRef.current = { key: e.key.toLowerCase(), at: now };

          // 해당 첫 번째 키에 대한 타임아웃
          const timeout =
            activeHotkeys.find((h) => h.sequence[0].toLowerCase() === e.key.toLowerCase())
              ?.timeoutMs ?? 1000;

          if (timeoutIdRef.current) clearTimeout(timeoutIdRef.current);
          timeoutIdRef.current = setTimeout(() => {
            lastKeyRef.current = null;
            timeoutIdRef.current = null;
          }, timeout);
          return;
        }
        // 첫 번째 키가 아니면 흘려보냄
        return;
      }

      // 두 번째 키 처리 — last !== null (첫 번째 키가 입력된 상태)
      const elapsed = now - last.at;
      const timeoutMs =
        activeHotkeys.find((h) => h.sequence[0].toLowerCase() === last.key)?.timeoutMs ?? 1000;

      if (elapsed >= timeoutMs) {
        // 타임아웃 경과 — 리셋 후 현재 키를 첫 번째 키로 처리
        if (timeoutIdRef.current) {
          clearTimeout(timeoutIdRef.current);
          timeoutIdRef.current = null;
        }
        lastKeyRef.current = null;

        if (firstKeys.has(e.key.toLowerCase()) && !inInput) {
          lastKeyRef.current = { key: e.key.toLowerCase(), at: now };
          const newTimeout =
            activeHotkeys.find((h) => h.sequence[0].toLowerCase() === e.key.toLowerCase())
              ?.timeoutMs ?? 1000;
          timeoutIdRef.current = setTimeout(() => {
            lastKeyRef.current = null;
            timeoutIdRef.current = null;
          }, newTimeout);
        }
        return;
      }

      // 타임아웃 미경과 — 두 번째 키 매칭
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
        timeoutIdRef.current = null;
      }

      const matched = activeHotkeys.find(
        (h) =>
          h.sequence[0].toLowerCase() === last.key &&
          h.sequence[1].toLowerCase() === e.key.toLowerCase() &&
          !(h.preventInInputs !== false && inInput)
      );

      lastKeyRef.current = null;

      if (matched) {
        matched.handler(e);
      } else if (firstKeys.has(e.key.toLowerCase()) && !inInput) {
        // 매치 안 된 경우: 두 번째 키가 새로운 첫 번째 키가 될 수 있는지 확인
        lastKeyRef.current = { key: e.key.toLowerCase(), at: now };
        const newTimeout =
          activeHotkeys.find((h) => h.sequence[0].toLowerCase() === e.key.toLowerCase())
            ?.timeoutMs ?? 1000;
        timeoutIdRef.current = setTimeout(() => {
          lastKeyRef.current = null;
          timeoutIdRef.current = null;
        }, newTimeout);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      if (timeoutIdRef.current) clearTimeout(timeoutIdRef.current);
    };
    // hotkeys 배열이 변경될 때마다 핸들러 재등록
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hotkeys]);
}
