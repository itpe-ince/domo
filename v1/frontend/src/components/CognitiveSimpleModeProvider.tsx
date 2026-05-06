"use client";

/**
 * CognitiveSimpleModeProvider — Phase 9 L-E
 *
 * Context로 `enabled` + `toggle` 공급.
 * AppShell 내부에서 Sidebar 바깥에 배치.
 * enabled true 시 <html> 요소에 data-simple-mode="true" 속성 추가
 * → CSS selector [data-simple-mode="true"] 로 전역 스타일 적용.
 */
import { createContext, useContext } from "react";
import { useCognitiveSimpleMode } from "@/lib/hooks/useCognitiveSimpleMode";

interface CognitiveSimpleModeContextValue {
  enabled: boolean;
  toggle: (next: boolean) => Promise<void>;
}

const CognitiveSimpleModeContext = createContext<CognitiveSimpleModeContextValue>({
  enabled: false,
  toggle: async () => {},
});

export function CognitiveSimpleModeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { enabled, toggle } = useCognitiveSimpleMode();

  return (
    <CognitiveSimpleModeContext.Provider value={{ enabled, toggle }}>
      {children}
    </CognitiveSimpleModeContext.Provider>
  );
}

export function useCognitiveSimpleModeContext() {
  return useContext(CognitiveSimpleModeContext);
}
