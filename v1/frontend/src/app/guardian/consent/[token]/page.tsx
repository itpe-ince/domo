"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  ApiClientError,
  approveGuardianConsent,
  fetchGuardianConsent,
  GuardianConsentInfo,
  withdrawGuardianConsent,
} from "@/lib/api";

export default function GuardianConsentPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [info, setInfo] = useState<GuardianConsentInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<"approve" | "withdraw" | null>(null);
  const [done, setDone] = useState<"approved" | "withdrawn" | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setInfo(await fetchGuardianConsent(token));
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? e.code === "NOT_FOUND"
            ? "잘못되었거나 만료된 링크입니다."
            : e.message
          : e instanceof Error
            ? e.message
            : "Failed to load"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setActing("approve");
    setError(null);
    try {
      await approveGuardianConsent(token);
      setDone("approved");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setActing(null);
    }
  }

  async function handleWithdraw() {
    if (
      !confirm(
        "정말 동의를 철회하시겠습니까? 해당 미성년자의 계정이 비활성화됩니다."
      )
    )
      return;
    setActing("withdraw");
    setError(null);
    try {
      await withdrawGuardianConsent(token);
      setDone("withdrawn");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Withdraw failed");
    } finally {
      setActing(null);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        로딩 중...
      </main>
    );
  }

  if (error || !info) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-4 px-6">
        <p className="text-danger text-center">{error ?? "링크를 찾을 수 없습니다."}</p>
        <Link href="/" className="btn-secondary text-sm">
          홈으로
        </Link>
      </main>
    );
  }

  const isExpired = new Date(info.expires_at) < new Date();
  const alreadyConsented = info.consented_at !== null;
  const isWithdrawn = info.withdrawn_at !== null;

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12">
      <header className="mb-8">
        <span className="badge-primary">Guardian</span>
        <h1 className="text-3xl font-bold mt-3">보호자 동의</h1>
      </header>

      {info.minor && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">미성년자 정보</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-text-muted">닉네임</dt>
            <dd>@{info.minor.display_name}</dd>
            <dt className="text-text-muted">이메일</dt>
            <dd>{info.minor.email}</dd>
            <dt className="text-text-muted">출생 연도</dt>
            <dd>{info.minor.birth_year}</dd>
            <dt className="text-text-muted">국가</dt>
            <dd>{info.minor.country_code}</dd>
          </dl>
        </div>
      )}

      <div className="card p-6 mb-6 text-sm text-text-secondary space-y-3">
        <p>
          Domo는 글로벌 미술 작가 소셜 네트워크입니다. 위 미성년자가 Domo
          플랫폼을 사용하려면 보호자 동의가 필요합니다.
        </p>
        <p>
          동의하시면 미성년자가 다음 기능을 사용할 수 있습니다.
        </p>
        <ul className="list-disc pl-5 space-y-1 text-text-muted">
          <li>작품 감상 및 팔로우</li>
          <li>블루버드 후원 (소액 결제)</li>
          <li>제한된 금액의 경매 입찰 (₩100,000 이하)</li>
          <li>신고 및 커뮤니티 참여</li>
        </ul>
        <p className="text-warning">
          ⚠ 동의 후에도 언제든 이 링크로 돌아와 동의를 철회할 수 있습니다.
        </p>
      </div>

      {error && (
        <div className="card border-danger p-3 text-danger text-sm mb-4">
          {error}
        </div>
      )}

      {done === "approved" && (
        <div className="card border-primary p-4 text-primary text-sm text-center mb-4">
          ✓ 동의가 완료되었습니다. 미성년자 계정이 활성화되었습니다.
        </div>
      )}
      {done === "withdrawn" && (
        <div className="card border-danger p-4 text-danger text-sm text-center mb-4">
          동의가 철회되었습니다.
        </div>
      )}

      <div className="space-y-2">
        {isExpired && !alreadyConsented && (
          <div className="card border-warning p-3 text-warning text-sm text-center">
            ⚠ 이 링크는 만료되었습니다.
          </div>
        )}

        {!alreadyConsented && !isExpired && !isWithdrawn && (
          <button
            onClick={handleApprove}
            disabled={acting !== null}
            className="btn-primary w-full disabled:opacity-50"
          >
            {acting === "approve" ? "처리 중..." : "✓ 동의합니다"}
          </button>
        )}

        {alreadyConsented && !isWithdrawn && (
          <button
            onClick={handleWithdraw}
            disabled={acting !== null}
            className="bg-danger text-white rounded-full px-5 py-2.5 w-full text-sm font-medium disabled:opacity-50"
          >
            {acting === "withdraw" ? "처리 중..." : "동의 철회"}
          </button>
        )}

        {isWithdrawn && (
          <p className="text-text-muted text-sm text-center">
            이미 철회된 동의입니다.
          </p>
        )}
      </div>

      <p className="text-text-muted text-xs text-center mt-8">
        본인이 요청한 것이 아니라면 이 페이지를 닫아주세요.
      </p>
    </main>
  );
}
