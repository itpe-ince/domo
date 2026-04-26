"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { startRegistration } from "@simplewebauthn/browser";
import {
  WebauthnCredentialView,
  fetchMe,
  tokenStore,
  webauthnListCredentials,
  webauthnRegisterBegin,
  webauthnRegisterFinish,
  webauthnRevokeCredential,
} from "@/lib/api";

export default function PasskeysPage() {
  const router = useRouter();
  const [creds, setCreds] = useState<WebauthnCredentialView[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [nickname, setNickname] = useState("");

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
      await loadCreds();
    })();
  }, [router]);

  async function loadCreds() {
    try {
      setCreds(await webauthnListCredentials());
    } catch (e) {
      setError(e instanceof Error ? e.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }

  async function handleEnroll() {
    setEnrolling(true);
    setError(null);
    try {
      const begin = await webauthnRegisterBegin(nickname || undefined);
      const opts = JSON.parse(begin.options);
      // startRegistration handles challenge/userId base64 decoding
      const credential = await startRegistration({ optionsJSON: opts });
      await webauthnRegisterFinish(
        begin.challenge_token,
        credential,
        nickname || undefined
      );
      setNickname("");
      await loadCreds();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "등록 실패";
      // User canceled — don't surface as error
      if (/cancel|abort/i.test(msg)) {
        setError(null);
      } else {
        setError(msg);
      }
    } finally {
      setEnrolling(false);
    }
  }

  async function handleRevoke(id: string, label: string) {
    if (!confirm(`정말 "${label}" 패스키를 제거하시겠습니까?`)) return;
    try {
      await webauthnRevokeCredential(id);
      await loadCreds();
    } catch (e) {
      setError(e instanceof Error ? e.message : "제거 실패");
    }
  }

  return (
    <main className="px-8 py-8 max-w-3xl">
      <header className="mb-8">
        <span className="admin-badge">Admin · 보안</span>
        <h1 className="text-2xl font-semibold mt-3 text-admin-fg tracking-tight">
          패스키 (Passkey / WebAuthn)
        </h1>
        <p className="text-admin-muted text-sm mt-1">
          TouchID / FaceID / 보안 키 등으로 비밀번호 + TOTP를 대체할 수 있습니다.
          서버에 비밀이 저장되지 않아 가장 안전한 방식입니다.
        </p>
      </header>

      {/* Enroll */}
      <div className="admin-card p-6 mb-6">
        <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
          새 패스키 등록
        </h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="닉네임 (예: MacBook TouchID)"
            value={nickname}
            onChange={(e) => setNickname(e.target.value.slice(0, 100))}
            disabled={enrolling}
            className="admin-input flex-1"
          />
          <button
            type="button"
            onClick={handleEnroll}
            disabled={enrolling}
            className="admin-btn-primary text-sm whitespace-nowrap"
          >
            {enrolling ? "등록 중..." : "+ 등록"}
          </button>
        </div>
        <p className="text-admin-muted text-[11px] mt-2">
          버튼 클릭 시 브라우저가 생체 인증 / 보안 키 입력을 요구합니다.
        </p>
        {error && (
          <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-3 py-2 mt-3 text-xs text-admin-danger">
            {error}
          </div>
        )}
      </div>

      {/* List */}
      <div className="admin-card p-6">
        <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
          등록된 패스키
        </h2>
        {loading ? (
          <div className="text-admin-muted text-sm py-4">로딩 중...</div>
        ) : !creds || creds.length === 0 ? (
          <p className="text-admin-muted text-sm py-4">
            아직 등록된 패스키가 없습니다.
          </p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>닉네임</th>
                <th>등록일</th>
                <th>최근 사용</th>
                <th>전송</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {creds.map((c) => (
                <tr key={c.id}>
                  <td className="text-admin-fg font-medium">
                    {c.nickname || "Authenticator"}
                    {c.backed_up && (
                      <span className="ml-2 admin-badge-success">동기화</span>
                    )}
                  </td>
                  <td className="text-admin-muted text-xs">
                    {new Date(c.created_at).toLocaleString("ko-KR")}
                  </td>
                  <td className="text-admin-muted text-xs">
                    {c.last_used_at
                      ? new Date(c.last_used_at).toLocaleString("ko-KR")
                      : "—"}
                  </td>
                  <td className="text-admin-muted text-xs">
                    {c.transports || "—"}
                  </td>
                  <td className="text-right">
                    <button
                      type="button"
                      onClick={() =>
                        handleRevoke(c.id, c.nickname || "Authenticator")
                      }
                      className="admin-btn-danger text-xs"
                    >
                      제거
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
