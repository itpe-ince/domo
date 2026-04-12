"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiClientError,
  ApiUser,
  acceptPolicies,
  cancelAccountDeletion,
  exportMyData,
  fetchLegalVersions,
  fetchMe,
  LegalVersions,
  loginWithMockEmail,
  requestAccountDeletion,
  tokenStore,
} from "@/lib/api";

export default function MyAccountPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [versions, setVersions] = useState<LegalVersions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [deletionInfo, setDeletionInfo] = useState<{
    deleted_at: string;
    deletion_scheduled_for: string;
  } | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setVersions(await fetchLegalVersions());
      if (tokenStore.get()) {
        try {
          setMe(await fetchMe());
        } catch {
          tokenStore.clear();
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    try {
      setMe(await loginWithMockEmail(loginEmail.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handleExport() {
    setBusy("export");
    setError(null);
    try {
      const blob = await exportMyData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `domo_export_${me?.id ?? "user"}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Export failed"
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (confirmText !== "DELETE MY ACCOUNT") {
      setError('"DELETE MY ACCOUNT"을 정확히 입력해주세요.');
      return;
    }
    setBusy("delete");
    setError(null);
    try {
      const r = await requestAccountDeletion();
      setDeletionInfo({
        deleted_at: r.deleted_at,
        deletion_scheduled_for: r.deletion_scheduled_for,
      });
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Delete failed"
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleCancelDelete() {
    setBusy("cancel");
    setError(null);
    try {
      await cancelAccountDeletion();
      setDeletionInfo(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleAcceptPolicies() {
    if (!versions) return;
    setBusy("accept");
    try {
      await acceptPolicies({
        privacy_policy_version: versions.privacy_policy.version,
        terms_version: versions.terms.version,
      });
      setMe(await fetchMe());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Accept failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 max-w-3xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">My Account</span>
          <h1 className="text-3xl font-bold mt-3">계정 설정</h1>
          <p className="text-text-secondary text-sm mt-1">
            개인정보 관리 및 GDPR 권리 행사
          </p>
        </div>
        <Link href="/" className="btn-ghost text-sm">
          ← 홈
        </Link>
      </header>

      {error && (
        <div className="card border-danger p-3 text-danger text-sm mb-4">
          {error}
        </div>
      )}

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 필요</h2>
          <input
            type="email"
            placeholder="email@example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {me && (
        <div className="space-y-6">
          {/* Profile summary */}
          <section className="card p-5">
            <h2 className="text-lg font-semibold mb-3">내 정보</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-text-muted">이메일</dt>
              <dd>{me.email}</dd>
              <dt className="text-text-muted">닉네임</dt>
              <dd>@{me.display_name}</dd>
              <dt className="text-text-muted">역할</dt>
              <dd>{me.role}</dd>
              <dt className="text-text-muted">상태</dt>
              <dd>{me.status}</dd>
            </dl>
          </section>

          {/* Policy consent */}
          {versions && (
            <section className="card p-5">
              <h2 className="text-lg font-semibold mb-3">정책 동의</h2>
              <div className="text-sm space-y-2">
                <div>
                  개인정보 처리방침:{" "}
                  <code className="text-primary">
                    {versions.privacy_policy.version}
                  </code>{" "}
                  <Link
                    href="/legal/privacy"
                    className="text-text-muted text-xs underline ml-2"
                  >
                    내용 보기
                  </Link>
                </div>
                <div>
                  이용약관:{" "}
                  <code className="text-primary">{versions.terms.version}</code>{" "}
                  <Link
                    href="/legal/terms"
                    className="text-text-muted text-xs underline ml-2"
                  >
                    내용 보기
                  </Link>
                </div>
              </div>
              <button
                onClick={handleAcceptPolicies}
                disabled={busy === "accept"}
                className="btn-secondary text-xs mt-4 disabled:opacity-50"
              >
                {busy === "accept" ? "저장 중..." : "현재 버전에 동의"}
              </button>
            </section>
          )}

          {/* Data export */}
          <section className="card p-5">
            <h2 className="text-lg font-semibold mb-2">내 데이터 내보내기</h2>
            <p className="text-text-secondary text-sm mb-4">
              GDPR 이전권(Right to Data Portability)에 따라 가입 이후 모든 개인
              데이터를 JSON 파일로 다운로드할 수 있습니다.
            </p>
            <button
              onClick={handleExport}
              disabled={busy === "export"}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {busy === "export" ? "준비 중..." : "📦 내 데이터 다운로드"}
            </button>
          </section>

          {/* Account deletion */}
          <section className="card border-danger p-5">
            <h2 className="text-lg font-semibold text-danger mb-2">
              계정 삭제
            </h2>
            <p className="text-text-secondary text-sm mb-4">
              계정 삭제를 요청하면 30일 유예 기간 후 영구적으로 개인정보가
              익명화됩니다. 유예 기간 내에는 취소할 수 있습니다.
            </p>

            {deletionInfo ? (
              <div className="card border-warning p-3 text-sm">
                <p className="text-warning font-medium">⚠ 삭제 요청됨</p>
                <p className="text-text-secondary mt-1">
                  요청일:{" "}
                  {new Date(deletionInfo.deleted_at).toLocaleString("ko-KR")}
                </p>
                <p className="text-text-secondary">
                  영구 삭제 예정일:{" "}
                  {new Date(
                    deletionInfo.deletion_scheduled_for
                  ).toLocaleString("ko-KR")}
                </p>
                <button
                  onClick={handleCancelDelete}
                  disabled={busy === "cancel"}
                  className="btn-primary text-xs mt-3 disabled:opacity-50"
                >
                  {busy === "cancel" ? "처리 중..." : "삭제 취소"}
                </button>
              </div>
            ) : (
              <>
                <p className="text-text-muted text-xs mb-2">
                  삭제를 진행하려면 아래에 정확히{" "}
                  <code className="text-danger">DELETE MY ACCOUNT</code>를
                  입력하세요.
                </p>
                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="DELETE MY ACCOUNT"
                  className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-3 focus:border-danger outline-none font-mono text-sm"
                />
                <button
                  onClick={handleDelete}
                  disabled={
                    busy === "delete" || confirmText !== "DELETE MY ACCOUNT"
                  }
                  className="bg-danger text-white rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
                >
                  {busy === "delete"
                    ? "처리 중..."
                    : "⚠ 계정 삭제 요청 (30일 유예)"}
                </button>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
