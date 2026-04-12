"use client";

import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen px-6 py-12 max-w-3xl mx-auto">
      <Link href="/" className="text-text-secondary text-sm hover:text-primary">
        ← 홈
      </Link>
      <header className="mt-6 mb-8">
        <span className="badge-primary">Legal</span>
        <h1 className="text-3xl font-bold mt-3">이용약관</h1>
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
            제1조 (목적)
          </h2>
          <p>
            본 약관은 Domo(이하 "회사")가 제공하는 글로벌 신진 미술 작가 SNS ·
            후원 · 경매 서비스(이하 "서비스")의 이용과 관련하여 회사와 이용자의
            권리, 의무 및 책임사항을 규정함을 목적으로 합니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제2조 (정의)
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>"작가" — 심사를 거쳐 작품을 업로드·판매할 수 있는 이용자</li>
            <li>"컬렉터" — 작품을 구매하거나 후원하는 이용자</li>
            <li>
              "블루버드" — 플랫폼 내 후원 단위 (기본 1블루버드 = 1,000원)
            </li>
            <li>"상품 포스트" — 판매 또는 경매 가능한 작품 게시물</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제3조 (회원가입)
          </h2>
          <p>
            이용자는 SNS 로그인을 통해 회원가입할 수 있습니다. 만 14세 미만은
            법정대리인의 동의가 필요합니다(국가별 연령 기준 상이).
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제4조 (작가 심사)
          </h2>
          <p>
            작가 권한은 관리자의 심사를 거쳐 부여됩니다. 회사는 포트폴리오
            검토를 통해 승인 또는 거절을 결정합니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제5조 (거래)
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>일회성 후원 및 정기 후원 (블루버드)</li>
            <li>경매 (영국식 오름경매, 낙찰 후 3일 결제 기한)</li>
            <li>즉시구매 (작가가 지정한 고정 가격)</li>
            <li>
              미결제 시 낙찰이 차순위 입찰자에게 이전될 수 있으며, 미결제
              이용자는 경고가 누적됩니다.
            </li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제6조 (수수료)
          </h2>
          <p>회사는 다음 수수료를 부과합니다. 수수료율은 시스템 설정으로 변경 가능하며 변경 시 공지합니다.</p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>후원 수수료: 5%</li>
            <li>경매 수수료: 10%</li>
            <li>즉시구매 수수료: 8%</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제7조 (제재)
          </h2>
          <p>
            회사는 다음 사유로 이용자에게 경고를 발급할 수 있으며, 경고 3회
            누적 시 계정이 정지됩니다. 이용자는 이의를 제기할 수 있습니다.
          </p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>부적절한 콘텐츠 게시</li>
            <li>낙찰 후 결제 기한 초과</li>
            <li>허위 또는 AI 생성 작품 업로드</li>
            <li>타인 비방 또는 저작권 침해</li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제8조 (환불)
          </h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>디지털 상품(블루버드 후원)은 원칙적으로 환불 불가</li>
            <li>
              정기 후원 해지 시 당월까지는 유지되며 다음 달부터 결제가
              중단됩니다.
            </li>
            <li>
              실물 작품은 작가와 구매자 간 분쟁 발생 시 회사는 조정 역할만
              수행하며 직접 개입하지 않습니다.
            </li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제9조 (배송)
          </h2>
          <p>
            실물 작품의 배송은 작가와 구매자 간 직접 처리되며, 회사는 배송 중
            발생한 분실/파손에 대한 책임을 지지 않습니다.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            제10조 (책임 제한)
          </h2>
          <p>
            회사는 천재지변, 전쟁, 네트워크 장애 등 불가항력으로 인한 서비스
            중단에 대해 책임을 지지 않습니다.
          </p>
        </div>
      </section>
    </main>
  );
}
