"use client";

import { useEffect, useRef, useState } from "react";
import { createUserByAdmin, AdminUserCreated } from "@/lib/api";

interface CreateUserModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateUserModal({
  open,
  onClose,
  onCreated,
}: CreateUserModalProps) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<"user" | "artist" | "admin">("user");
  const [sendMagicLink, setSendMagicLink] = useState(true);
  const [countryCode, setCountryCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement>(null);

  // 열릴 때 상태 초기화 + 포커스
  useEffect(() => {
    if (open) {
      setEmail("");
      setDisplayName("");
      setRole("user");
      setSendMagicLink(true);
      setCountryCode("");
      setError(null);
      setToast(null);
      setTimeout(() => emailRef.current?.focus(), 50);
    }
  }, [open]);

  // ESC 키로 닫기
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // admin 선택 시 추가 confirm
    if (role === "admin") {
      const ok = window.confirm(
        "관리자 권한으로 사용자를 등록하시겠습니까? 매직 링크 + 2FA 등록이 강제됩니다."
      );
      if (!ok) return;
    }

    if (countryCode && countryCode.length !== 2) {
      setError("국가 코드는 2자리 ISO 코드여야 합니다. (예: KR, US)");
      return;
    }

    setSubmitting(true);
    try {
      await createUserByAdmin({
        email,
        display_name: displayName,
        role,
        send_magic_link: sendMagicLink,
        country_code: countryCode || null,
      });
      setToast(
        sendMagicLink
          ? "사용자 등록 완료. 매직 링크 발송됨."
          : "사용자 등록 완료."
      );
      setTimeout(() => {
        onCreated();
        onClose();
      }, 1200);
    } catch (err: any) {
      if (err?.code === "CONFLICT" || err?.message?.includes("already")) {
        setError("이미 등록된 이메일입니다.");
      } else if (err?.code === "VALIDATION_ERROR") {
        setError(err.message ?? "입력값을 확인해 주세요.");
      } else {
        setError(err?.message ?? "사용자 등록에 실패했습니다.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    /* 배경 오버레이 */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "rgba(11, 18, 32, 0.85)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="bg-admin-surface border border-admin-border rounded-xl w-full max-w-md mx-4 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-user-title"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-admin-border">
          <h2
            id="create-user-title"
            className="text-base font-semibold text-admin-fg"
          >
            신규 사용자 등록
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-admin-muted hover:text-admin-fg transition-colors rounded-md p-1"
            aria-label="닫기"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
            >
              <path d="M2 2l12 12M14 2L2 14" />
            </svg>
          </button>
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* 이메일 */}
          <div>
            <label
              htmlFor="cu-email"
              className="block text-xs font-medium text-admin-fg-soft mb-1"
            >
              이메일 <span className="text-admin-danger">*</span>
            </label>
            <input
              ref={emailRef}
              id="cu-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              className="admin-input w-full"
            />
          </div>

          {/* 표시 이름 */}
          <div>
            <label
              htmlFor="cu-display-name"
              className="block text-xs font-medium text-admin-fg-soft mb-1"
            >
              표시 이름 <span className="text-admin-danger">*</span>
            </label>
            <input
              id="cu-display-name"
              type="text"
              required
              minLength={3}
              maxLength={50}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="3~50자"
              className="admin-input w-full"
            />
          </div>

          {/* 역할 선택 */}
          <div>
            <p className="text-xs font-medium text-admin-fg-soft mb-2">
              역할 <span className="text-admin-danger">*</span>
            </p>
            <div className="flex gap-4">
              {(["user", "artist", "admin"] as const).map((r) => (
                <label
                  key={r}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="cu-role"
                    value={r}
                    checked={role === r}
                    onChange={() => setRole(r)}
                    className="accent-admin-accent"
                  />
                  <span
                    className={`text-sm font-medium ${
                      role === r
                        ? r === "admin"
                          ? "text-admin-danger"
                          : "text-admin-accent"
                        : "text-admin-fg-soft"
                    }`}
                  >
                    {r}
                  </span>
                </label>
              ))}
            </div>
            {role === "admin" && (
              <p className="mt-1.5 text-xs text-admin-danger">
                관리자 등록 시 매직 링크와 2FA 등록이 강제됩니다.
              </p>
            )}
          </div>

          {/* 국가 코드 (선택) */}
          <div>
            <label
              htmlFor="cu-country"
              className="block text-xs font-medium text-admin-fg-soft mb-1"
            >
              국가 코드{" "}
              <span className="text-admin-muted font-normal">(선택, ISO 2자리)</span>
            </label>
            <input
              id="cu-country"
              type="text"
              maxLength={2}
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
              placeholder="KR"
              className="admin-input w-24 uppercase"
            />
          </div>

          {/* 매직 링크 발송 체크박스 */}
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={sendMagicLink}
              onChange={(e) => setSendMagicLink(e.target.checked)}
              className="mt-0.5 accent-admin-accent"
            />
            <span className="text-sm text-admin-fg-soft leading-snug">
              사용자에게 비밀번호 설정 매직 링크 이메일 발송
            </span>
          </label>

          {/* 에러 메시지 */}
          {error && (
            <div className="bg-admin-danger/10 border border-admin-danger/30 rounded-md px-3 py-2 text-sm text-admin-danger">
              {error}
            </div>
          )}

          {/* 성공 토스트 (인라인) */}
          {toast && (
            <div className="bg-admin-success/10 border border-admin-success/30 rounded-md px-3 py-2 text-sm text-admin-success">
              {toast}
            </div>
          )}

          {/* 버튼 */}
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="admin-btn-secondary"
              disabled={submitting}
            >
              취소
            </button>
            <button
              type="submit"
              className="admin-btn-primary"
              disabled={submitting}
            >
              {submitting ? "등록 중..." : "등록"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
