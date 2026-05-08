/**
 * useGlobalHotkeys — 전역 키보드 단축키 등록 hook
 *
 * Phase 11 D-1: 재사용 가능한 전역 keydown 이벤트 관리.
 * - input/textarea/contentEditable 포커스 시 자동 비활성 (preventInInputs 기본값 true)
 * - modifier "cmd": macOS ⌘ (metaKey) + Windows/Linux Ctrl (ctrlKey) 동시 지원
 * - enabled: false 로 설정 시 해당 단축키 비등록 (route별 조건부 활성화)
 */

import { useEffect } from "react";

type HotkeyHandler = (e: KeyboardEvent) => void;

interface HotkeyDefinition {
  /** 단일 키 문자열. 예: "j", "k", "?", "s" */
  key: string;
  /**
   * 수정자 키.
   * "cmd"는 macOS ⌘(metaKey) + Windows/Linux Ctrl(ctrlKey) 모두 처리.
   * "ctrl"은 ctrlKey만. "shift"는 shiftKey만.
   */
  modifier?: "cmd" | "ctrl" | "shift";
  /** 키 핸들러 */
  handler: HotkeyHandler;
  /**
   * false 로 설정하면 이 단축키를 등록하지 않는다.
   * route별 조건부 활성화에 사용. default: true
   */
  enabled?: boolean;
  /**
   * true(default)이면 input/textarea/select/contentEditable 포커스 시
   * 이 핸들러를 건너뛴다.
   * ⌘S 처럼 폼 안에서도 의도적으로 동작해야 할 경우 false 로 오버라이드.
   */
  preventInInputs?: boolean;
}

/**
 * input/textarea/select/contentEditable 에 포커스가 있을 때 단축키를 차단해야
 * 하는지 확인한다.
 */
function shouldIgnoreHotkey(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  // 표준 입력 요소
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  // contentEditable (리치 텍스트 에디터 포함)
  if (target.isContentEditable) return true;
  return false;
}

export function useGlobalHotkeys(hotkeys: HotkeyDefinition[]): void {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      for (const definition of hotkeys) {
        // enabled === false 이면 건너뜀
        if (definition.enabled === false) continue;

        // preventInInputs !== false 이고 입력 포커스 중이면 건너뜀
        if (
          definition.preventInInputs !== false &&
          shouldIgnoreHotkey(e.target)
        ) {
          continue;
        }

        // modifier 체크
        if (definition.modifier) {
          switch (definition.modifier) {
            case "cmd":
              // macOS: metaKey, Windows/Linux: ctrlKey
              if (!(e.metaKey || e.ctrlKey)) continue;
              break;
            case "ctrl":
              if (!e.ctrlKey) continue;
              break;
            case "shift":
              if (!e.shiftKey) continue;
              break;
          }
        } else {
          // modifier 없는 단순 키는 meta/ctrl/alt 조합이 눌린 경우 무시
          // (브라우저 단축키와의 충돌 방지)
          if (e.metaKey || e.ctrlKey || e.altKey) continue;
        }

        // 키 일치 확인
        if (e.key.toLowerCase() === definition.key.toLowerCase()) {
          definition.handler(e);
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
    // hotkeys 배열이 변경될 때마다 핸들러 재등록
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hotkeys]);
}
