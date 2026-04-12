"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const CONSENT_KEY = "domo_cookie_consent_v1";

type ConsentLevel = "essential" | "all";

type ConsentRecord = {
  level: ConsentLevel;
  accepted_at: string;
  version: string;
};

export function getStoredConsent(): ConsentRecord | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(CONSENT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ConsentRecord;
  } catch {
    return null;
  }
}

export function CookieConsent() {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!localStorage.getItem(CONSENT_KEY)) {
      setShown(true);
    }
  }, []);

  function accept(level: ConsentLevel) {
    const record: ConsentRecord = {
      level,
      accepted_at: new Date().toISOString(),
      version: "v1",
    };
    localStorage.setItem(CONSENT_KEY, JSON.stringify(record));
    setShown(false);
  }

  if (!shown) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-border p-4 shadow-lg">
      <div className="max-w-4xl mx-auto flex flex-col md:flex-row md:items-center gap-3">
        <div className="flex-1 text-sm text-text-secondary">
          <p className="font-medium text-text-primary mb-1">🍪 쿠키 사용 안내</p>
          <p>
            Domo는 서비스 제공을 위해 필수 쿠키를 사용합니다. 선택적으로 분석
            쿠키를 허용할 수 있습니다.{" "}
            <Link href="/legal/cookies" className="text-primary underline">
              쿠키 정책
            </Link>{" "}
            ·{" "}
            <Link href="/legal/privacy" className="text-primary underline">
              개인정보 처리방침
            </Link>
          </p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={() => accept("essential")}
            className="btn-secondary text-xs"
          >
            필수만
          </button>
          <button
            onClick={() => accept("all")}
            className="btn-primary text-xs"
          >
            모두 허용
          </button>
        </div>
      </div>
    </div>
  );
}
