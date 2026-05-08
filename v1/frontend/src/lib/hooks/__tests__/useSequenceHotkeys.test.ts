/**
 * useSequenceHotkeys unit tests — Phase 12 C-3
 *
 * 테스트 케이스:
 * 1. 정확한 시퀀스 입력 시 핸들러 호출
 * 2. 첫 번째 키만 입력 후 타임아웃 경과 시 핸들러 미호출
 * 3. 타임아웃 이내에 등록되지 않은 두 번째 키 입력 시 핸들러 미호출
 * 4. input 포커스 중 g-시퀀스 차단
 * 5. enabled: false 시 시퀀스 무시
 * 6. 두 번째 키 입력 후 lastKeyRef 리셋 (연속 단독 키 무동작)
 * 7. 연속 시퀀스 처리 — 첫 시퀀스 성공 후 두 번째 시퀀스 정상 처리
 */

import { renderHook } from "@testing-library/react";
import { useSequenceHotkeys } from "../useSequenceHotkeys";

/** keydown 이벤트를 window에 발화하는 헬퍼 */
function fireKey(key: string, target?: EventTarget) {
  const event = new KeyboardEvent("keydown", {
    key,
    bubbles: true,
    cancelable: true,
  });
  if (target) {
    Object.defineProperty(event, "target", { value: target, configurable: true });
  }
  window.dispatchEvent(event);
  return event;
}

describe("useSequenceHotkeys", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("정확한 시퀀스 입력 시 핸들러 호출", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, enabled: true },
      ])
    );

    fireKey("g");
    fireKey("h");

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("첫 번째 키만 입력 후 타임아웃 경과 시 핸들러 미호출", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, timeoutMs: 1000, enabled: true },
      ])
    );

    fireKey("g");
    // 1000ms 타임아웃 경과
    jest.advanceTimersByTime(1001);
    // 두 번째 키 입력 (타임아웃 후)
    fireKey("h");

    expect(handler).not.toHaveBeenCalled();
  });

  it("타임아웃 이내에 등록되지 않은 두 번째 키 입력 시 핸들러 미호출", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, enabled: true },
      ])
    );

    fireKey("g");
    fireKey("x"); // 등록되지 않은 두 번째 키

    expect(handler).not.toHaveBeenCalled();
  });

  it("input 포커스 중 g-시퀀스 차단 (preventInInputs 기본값 true)", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, enabled: true },
      ])
    );

    // input 요소 생성 후 포커스 설정
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();

    // input에 포커스된 상태에서 이벤트 발화 시 target이 input이 되도록
    const gEvent = new KeyboardEvent("keydown", { key: "g", bubbles: true, cancelable: true });
    Object.defineProperty(gEvent, "target", { value: input, configurable: true });
    window.dispatchEvent(gEvent);

    const hEvent = new KeyboardEvent("keydown", { key: "h", bubbles: true, cancelable: true });
    Object.defineProperty(hEvent, "target", { value: input, configurable: true });
    window.dispatchEvent(hEvent);

    expect(handler).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it("enabled: false 시 시퀀스 무시", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, enabled: false },
      ])
    );

    fireKey("g");
    fireKey("h");

    expect(handler).not.toHaveBeenCalled();
  });

  it("두 번째 키 입력 후 lastKeyRef 리셋 — 이후 단독 h 입력 시 핸들러 미호출", () => {
    const handler = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler, enabled: true },
      ])
    );

    // 첫 번째 시퀀스 성공
    fireKey("g");
    fireKey("h");
    expect(handler).toHaveBeenCalledTimes(1);

    // 리셋 후 단독 h 입력 — 핸들러 미호출
    fireKey("h");
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("연속 시퀀스 처리 — 첫 시퀀스 성공 후 두 번째 시퀀스 정상 처리", () => {
    const handlerGH = jest.fn();
    const handlerGF = jest.fn();
    renderHook(() =>
      useSequenceHotkeys([
        { sequence: ["g", "h"], handler: handlerGH, enabled: true },
        { sequence: ["g", "f"], handler: handlerGF, enabled: true },
      ])
    );

    // 첫 번째 시퀀스: g → h
    fireKey("g");
    fireKey("h");
    expect(handlerGH).toHaveBeenCalledTimes(1);
    expect(handlerGF).toHaveBeenCalledTimes(0);

    // 두 번째 시퀀스: g → f
    fireKey("g");
    fireKey("f");
    expect(handlerGH).toHaveBeenCalledTimes(1);
    expect(handlerGF).toHaveBeenCalledTimes(1);
  });
});
