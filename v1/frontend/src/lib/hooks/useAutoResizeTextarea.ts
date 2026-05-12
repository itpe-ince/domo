import { useEffect, RefObject } from "react";

/**
 * useAutoResizeTextarea — textarea 높이를 콘텐츠에 맞게 자동 조절.
 *
 * el.style.height = "auto" 로 리셋 후 scrollHeight 를 적용하는 방식으로
 * 입력이 줄어들 때도 높이가 올바르게 감소한다.
 *
 * @param ref       HTMLTextAreaElement ref
 * @param value     현재 textarea 값 (effect 의존성)
 * @param minHeight 최소 높이(px), 기본값 180
 */
export function useAutoResizeTextarea(
  ref: RefObject<HTMLTextAreaElement | null>,
  value: string,
  minHeight = 180,
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.max(minHeight, el.scrollHeight)}px`;
  }, [ref, value, minHeight]);
}
