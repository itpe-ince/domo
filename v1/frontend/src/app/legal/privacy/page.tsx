"use client";

import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12">
      <Link href="/" className="text-text-secondary text-sm hover:text-primary">
        ← 홈
      </Link>
      <header className="mt-6 mb-8">
        <span className="badge-primary">Legal</span>
        <h1 className="text-3xl font-bold mt-3">개인정보 처리방침</h1>
        <p className="text-text-muted text-sm mt-1">
          버전 v1-draft · 시행일 2026-04-11
        </p>
        <div className="card border-warning p-3 mt-4 text-warning text-xs">
          ⚠ 본 문서는 초안입니다. 법률 자문 검토 후 확정됩니다.
        </div>
      </header>

      <section className="space-y-6 text-text-secondary text-sm leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            1. 수집하는 개인정보 항목
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>필수: 이메일, 표시 이름, SNS 로그인 식별자</li>
            <li>선택: 프로필 사진, 자기소개, 국가, 언어, 생년월일(미성년 판정)</li>
            <li>작가 신청 시: 학교, 포트폴리오 URL, 소개 영상, 자기소개문</li>
            <li>거래 시: 결제 식별자(Stripe), 주문/후원 이력</li>
            <li>자동 수집: 접속 IP, User-Agent, 쿠키(세션 유지)</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            2. 개인정보의 수집 및 이용 목적
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>회원 가입 및 관리 — 본인 식별, 로그인 유지</li>
            <li>작가 심사 및 승인 — 포트폴리오 검토</li>
            <li>거래 처리 — 후원/경매/주문/결제/정산</li>
            <li>콘텐츠 제공 — 피드, 추천, 알림</li>
            <li>신고 및 분쟁 처리 — 신고 접수, 제재 이력 관리</li>
            <li>법적 의무 이행 — 세법, 전자상거래법 등</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            3. 개인정보의 보유 및 이용 기간
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>회원 탈퇴 시: 요청 후 30일 유예 → 익명화 처리</li>
            <li>거래 기록: 전자상거래법에 따라 5년 보관</li>
            <li>로그인 기록: 3개월</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            4. 개인정보 제3자 제공
          </h2>
          <p>
            Domo는 다음 경우 외에는 개인정보를 제3자에게 제공하지 않습니다.
          </p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>이용자가 사전에 동의한 경우</li>
            <li>법령의 규정에 의거하거나 수사 목적으로 법적 절차에 따른 경우</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            5. 개인정보 처리 위탁
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Stripe, Inc. — 결제 처리</li>
            <li>Amazon Web Services — 미디어 스토리지 및 CDN</li>
            <li>Firebase (Google LLC) — 웹 푸시 알림</li>
            <li>Resend / Amazon SES — 이메일 발송</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            6. 이용자의 권리 (GDPR / 국내 개인정보보호법)
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>열람권: 계정 설정 → 내 데이터 내보내기로 전체 조회 가능</li>
            <li>정정권: 프로필 편집 기능</li>
            <li>삭제권: 계정 삭제 요청 (30일 유예 후 영구 삭제)</li>
            <li>이전권: JSON 형식으로 개인 데이터 다운로드</li>
            <li>처리 제한 요청: 고객 지원으로 문의</li>
          </ul>
          <p className="mt-2">
            <Link href="/me/account" className="text-primary underline">
              계정 설정
            </Link>
            에서 위 권리를 즉시 행사할 수 있습니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            7. 개인정보 보호책임자
          </h2>
          <p>
            이메일: privacy@tuzigroup.com
            <br />
            (실 서비스 시 확정)
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            8. 변경 이력
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>v1-draft (2026-04-11) — 초안 작성</li>
          </ul>
        </div>
      </section>
    </main>
  );
}
