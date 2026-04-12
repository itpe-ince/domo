"use client";

import Link from "next/link";

export default function CookiesPage() {
  return (
    <main className="min-h-screen px-6 py-12 max-w-3xl mx-auto">
      <Link href="/" className="text-text-secondary text-sm hover:text-primary">
        ← 홈
      </Link>
      <header className="mt-6 mb-8">
        <span className="badge-primary">Legal</span>
        <h1 className="text-3xl font-bold mt-3">쿠키 정책</h1>
        <p className="text-text-muted text-sm mt-1">
          버전 v1-draft · 시행일 2026-04-11
        </p>
      </header>

      <section className="space-y-6 text-text-secondary text-sm leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            1. 쿠키란?
          </h2>
          <p>
            쿠키는 웹사이트가 방문자의 브라우저에 저장하는 작은 텍스트
            파일입니다. 로그인 상태 유지, 설정 저장 등에 사용됩니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            2. Domo가 사용하는 쿠키
          </h2>
          <div className="space-y-3">
            <div className="card p-3">
              <div className="text-text-primary font-medium">필수 쿠키</div>
              <p className="text-xs mt-1">
                로그인 상태 유지, 세션 관리, 보안 기능. 이 쿠키가 없으면
                서비스가 동작하지 않습니다.
              </p>
              <p className="text-xs text-text-muted mt-2">
                예: <code>domo_access_token</code>,{" "}
                <code>domo_refresh_token</code>,{" "}
                <code>domo_cookie_consent_v1</code>
              </p>
            </div>

            <div className="card p-3">
              <div className="text-text-primary font-medium">분석 쿠키 (선택)</div>
              <p className="text-xs mt-1">
                서비스 개선을 위한 사용 패턴 분석. "모두 허용"을 선택한 경우에만
                사용됩니다.
              </p>
              <p className="text-xs text-text-muted mt-2">
                예: 방문 페이지, 체류 시간, 클릭 경로
              </p>
            </div>
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            3. 쿠키 동의 철회
          </h2>
          <p>
            브라우저 설정에서 Domo 도메인의 로컬 저장소를 삭제하면 쿠키 동의가
            초기화됩니다. 다음 접속 시 쿠키 배너가 다시 표시됩니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            4. 관련 문서
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <Link href="/legal/privacy" className="text-primary underline">
                개인정보 처리방침
              </Link>
            </li>
            <li>
              <Link href="/legal/terms" className="text-primary underline">
                이용약관
              </Link>
            </li>
          </ul>
        </div>
      </section>
    </main>
  );
}
