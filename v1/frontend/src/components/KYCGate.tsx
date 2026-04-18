"use client";

import { useState } from "react";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/lib/api";
import { useMe } from "@/lib/useMe";

interface KYCGateProps {
  children: React.ReactNode;
  onVerified?: () => void;
}

/**
 * Wraps a button/action that requires identity verification.
 * If user is not verified, shows verification modal instead of executing the action.
 */
export function KYCGate({ children, onVerified }: KYCGateProps) {
  const { me } = useMe();
  const [showModal, setShowModal] = useState(false);

  if (!me) return <>{children}</>;

  // Already verified — just render children
  if (me.identity_verified_at) {
    return <>{children}</>;
  }

  return (
    <>
      <div onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowModal(true); }}>
        {children}
      </div>
      {showModal && (
        <KYCVerifyModal
          onClose={() => setShowModal(false)}
          onVerified={() => {
            setShowModal(false);
            onVerified?.();
            window.location.reload();
          }}
        />
      )}
    </>
  );
}

function KYCVerifyModal({
  onClose,
  onVerified,
}: {
  onClose: () => void;
  onVerified: () => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleVerify() {
    if (!name.trim() || !birthDate) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/kyc/mock-verify", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), birth_date: birthDate }),
      });
      onVerified();
    } catch (e) {
      setError(e instanceof Error ? e.message : "인증 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4" onClick={onClose}>
      <div className="card w-full max-w-md p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div>
            <span className="badge-primary">KYC</span>
            <h2 className="text-xl font-bold mt-2">본인인증</h2>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xl">×</button>
        </div>

        <p className="text-text-secondary text-sm">
          금융거래(구매/후원)를 위해 본인인증이 필요합니다.
          인증은 1회만 진행됩니다.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm text-text-secondary mb-1">이름 (실명)</label>
            <input
              type="text" value={name} onChange={(e) => setName(e.target.value)}
              placeholder="홍길동"
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1">생년월일</label>
            <input
              type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none"
            />
          </div>
        </div>

        {error && <p className="text-danger text-sm">{error}</p>}

        <button
          onClick={handleVerify}
          disabled={submitting || !name.trim() || !birthDate}
          className="btn-primary w-full disabled:opacity-50"
        >
          {submitting ? "인증 중..." : "본인인증 완료"}
        </button>

        <p className="text-xs text-text-muted text-center">
          개발 모드: Mock 인증 (실제 서비스에서는 Toss/PASS 연동)
        </p>
      </div>
    </div>
  );
}
