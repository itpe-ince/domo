"use client";

import { Suspense, useEffect, useState } from "react";
import {
  RecoveryCodeStatus,
  adminRecoveryCodesRegenerate,
  adminRecoveryCodesStatus,
  fetchMe,
  tokenStore,
} from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

// Disable prerender — page requires runtime auth + searchParams
export const dynamic = "force-dynamic";

export default function RecoveryCodesPage() {
  return (
    <Suspense
      fallback={
        <main className="px-8 py-8 max-w-3xl">
          <div className="admin-card p-8 text-center text-admin-muted text-sm">
            로딩 중...
          </div>
        </main>
      }
    >
      <RecoveryCodesPageInner />
    </Suspense>
  );
}

function RecoveryCodesPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const lowSignal = searchParams.get("low") === "1";

  const [status, setStatus] = useState<RecoveryCodeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Regenerate flow
  const [showRegen, setShowRegen] = useState(false);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [newCodes, setNewCodes] = useState<string[] | null>(null);

  useEffect(() => {
    void (async () => {
      if (!tokenStore.get()) {
        router.replace("/login");
        return;
      }
      try {
        const me = await fetchMe();
        if (me.role !== "admin") {
          router.replace("/login");
          return;
        }
      } catch {
        router.replace("/login");
        return;
      }
      try {
        setStatus(await adminRecoveryCodesStatus());
      } catch (e) {
        setError(e instanceof Error ? e.message : "조회 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function handleRegenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await adminRecoveryCodesRegenerate(password);
      setNewCodes(result.recovery_codes);
      setStatus(await adminRecoveryCodesStatus());
      setPassword("");
      setShowRegen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "재발급 실패");
    } finally {
      setSubmitting(false);
    }
  }

  function copyCodes() {
    if (!newCodes) return;
    void navigator.clipboard.writeText(newCodes.join("\n"));
  }

  function downloadCodes() {
    if (!newCodes) return;
    const text =
      "Domo Admin Recovery Codes\n=========================\n" +
      "Generated: " + new Date().toISOString() + "\n\n" +
      newCodes.join("\n") + "\n";
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "domo-admin-recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="px-8 py-8 max-w-3xl">
      <header className="mb-8">
        <span className="admin-badge">Admin · 보안</span>
        <h1 className="text-2xl font-semibold mt-3 text-admin-fg tracking-tight">
          복구 코드 (Recovery codes)
        </h1>
        <p className="text-admin-muted text-sm mt-1">
          Authenticator 앱 분실 시 1회용으로 사용하는 백업 코드입니다.
        </p>
      </header>

      {lowSignal && !newCodes && (
        <div className="rounded-md border border-admin-warning/30 bg-admin-warning/10 px-4 py-3 mb-6 text-sm text-admin-warning">
          ⚠️ 복구 코드가 거의 소진되었습니다. 즉시 재발급하세요.
        </div>
      )}

      {loading ? (
        <div className="admin-card p-8 text-center text-admin-muted text-sm">
          불러오는 중...
        </div>
      ) : !status ? (
        <div className="admin-card p-6 border border-admin-danger/30 text-admin-danger text-sm">
          {error ?? "TOTP가 활성화되어 있어야 복구 코드를 사용할 수 있습니다."}
        </div>
      ) : (
        <>
          {/* Status panel */}
          <div className="admin-card p-6 mb-6">
            <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
              현재 상태
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <div className="text-admin-muted text-[11px] uppercase tracking-wider">
                  남은 코드
                </div>
                <div
                  className={`text-3xl font-semibold mt-1 tabular-nums ${
                    status.warning_low ? "text-admin-warning" : "text-admin-fg"
                  }`}
                >
                  {status.remaining}
                </div>
              </div>
              <div>
                <div className="text-admin-muted text-[11px] uppercase tracking-wider">
                  사용됨
                </div>
                <div className="text-3xl font-semibold mt-1 text-admin-fg-soft tabular-nums">
                  {status.used}
                </div>
              </div>
              <div>
                <div className="text-admin-muted text-[11px] uppercase tracking-wider">
                  전체 발급
                </div>
                <div className="text-3xl font-semibold mt-1 text-admin-fg-soft tabular-nums">
                  {status.total}
                </div>
              </div>
            </div>
            {status.warning_low && (
              <p className="text-admin-warning text-xs">
                ⚠️ 코드가 얼마 남지 않았습니다. 새 세트로 재발급을 권장합니다.
              </p>
            )}
            <p className="text-admin-muted text-[11px] mt-3 pt-3 border-t border-admin-border">
              보안상 평문 코드는 다시 표시할 수 없습니다. 분실 시 재발급으로
              새 세트를 받으세요 (기존 코드는 즉시 무효화).
            </p>
          </div>

          {/* New codes panel (after regenerate) */}
          {newCodes && (
            <div className="admin-card p-6 mb-6 border border-admin-warning/40 bg-admin-warning/5">
              <div className="flex items-start gap-3 mb-4">
                <span className="text-admin-warning text-lg">⚠️</span>
                <div>
                  <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider">
                    새 복구 코드 (한 번만 표시됨)
                  </h2>
                  <p className="text-admin-muted text-xs mt-1">
                    안전한 곳에 보관하세요. 페이지를 떠나면 다시 표시할 수
                    없습니다. 기존 코드는 모두 무효화되었습니다.
                  </p>
                </div>
              </div>
              <div className="bg-admin-bg border border-admin-border rounded-md p-4 mb-4">
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 font-mono text-sm text-admin-fg">
                  {newCodes.map((c, i) => (
                    <div key={c} className="flex items-baseline gap-2">
                      <span className="text-admin-muted text-[10px] w-4 text-right">
                        {i + 1}.
                      </span>
                      <span className="tracking-wider">{c}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={copyCodes}
                  className="admin-btn-secondary text-xs"
                >
                  📋 복사
                </button>
                <button
                  type="button"
                  onClick={downloadCodes}
                  className="admin-btn-secondary text-xs"
                >
                  ⬇ .txt 다운로드
                </button>
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="admin-btn-secondary text-xs"
                >
                  🖨 인쇄
                </button>
                <button
                  type="button"
                  onClick={() => setNewCodes(null)}
                  className="admin-btn-ghost text-xs ml-auto"
                >
                  닫기
                </button>
              </div>
            </div>
          )}

          {/* Regenerate panel */}
          <div className="admin-card p-6">
            <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
              재발급
            </h2>
            {!showRegen ? (
              <>
                <p className="text-admin-fg-soft text-sm mb-4">
                  새 10개 코드를 발급합니다. 기존 사용/미사용 코드는{" "}
                  <span className="text-admin-danger">즉시 모두 무효화</span>됩니다.
                </p>
                <button
                  type="button"
                  onClick={() => setShowRegen(true)}
                  className="admin-btn-danger text-sm"
                >
                  새 코드 발급
                </button>
              </>
            ) : (
              <form onSubmit={handleRegenerate} className="space-y-3">
                <p className="text-admin-fg-soft text-sm">
                  보안 확인을 위해 비밀번호를 다시 입력하세요.
                </p>
                <input
                  type="password"
                  autoFocus
                  autoComplete="current-password"
                  placeholder="비밀번호"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={submitting}
                  className="admin-input w-full max-w-sm"
                />
                {error && (
                  <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-3 py-2 text-xs text-admin-danger">
                    {error}
                  </div>
                )}
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={submitting || !password}
                    className="admin-btn-danger text-sm"
                  >
                    {submitting ? "발급 중..." : "확인 — 새 코드 발급"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowRegen(false);
                      setPassword("");
                      setError(null);
                    }}
                    disabled={submitting}
                    className="admin-btn-ghost text-sm"
                  >
                    취소
                  </button>
                </div>
              </form>
            )}
          </div>
        </>
      )}
    </main>
  );
}
