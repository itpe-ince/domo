"use client";

import { useState } from "react";
import { useI18n } from "@/i18n";

const FAQ = [
  {
    q: { ko: "블루버드란 무엇인가요?", en: "What is a Bluebird?", ja: "ブルーバードとは？", zh: "什麼是藍鳥？", es: "¿Qué es un Bluebird?" },
    a: { ko: "블루버드는 $1 단위의 후원 화폐입니다. 좋아하는 작가에게 블루버드를 보내 응원할 수 있습니다.", en: "A Bluebird is a $1 sponsorship unit. Send Bluebirds to support your favorite artists.", ja: "ブルーバードは$1単位の支援通貨です。好きなアーティストに送って応援できます。", zh: "藍鳥是$1為單位的贊助貨幣，可以送給喜歡的藝術家。", es: "Un Bluebird es una unidad de patrocinio de $1. Envía Bluebirds para apoyar a tus artistas favoritos." },
  },
  {
    q: { ko: "작가가 되려면 어떻게 해야 하나요?", en: "How do I become an artist?", ja: "アーティストになるには？", zh: "如何成為藝術家？", es: "¿Cómo me convierto en artista?" },
    a: { ko: "사이드바의 '작가 심사 신청'을 통해 포트폴리오를 제출하세요. 관리자 검토 후 승인됩니다.", en: "Submit your portfolio through 'Artist Application' in the sidebar. It will be reviewed by our admin team.", ja: "サイドバーの「アーティスト審査申請」からポートフォリオを提出してください。", zh: "通過側邊欄的「藝術家申請」提交您的作品集。", es: "Envía tu portafolio a través de 'Solicitud de Artista' en la barra lateral." },
  },
  {
    q: { ko: "경매는 어떻게 진행되나요?", en: "How do auctions work?", ja: "オークションの仕組みは？", zh: "拍賣如何進行？", es: "¿Cómo funcionan las subastas?" },
    a: { ko: "작가가 3/7/14일 기간으로 경매를 등록합니다. 입찰가는 최소 증가금 이상이어야 합니다. 낙찰 후 3일 이내 결제해야 합니다.", en: "Artists set auction durations of 3, 7, or 14 days. Bids must exceed the minimum increment. Payment is due within 3 days of winning.", ja: "作家が3/7/14日の期間でオークションを登録します。入札は最低増分以上である必要があります。", zh: "藝術家設定3/7/14天的拍賣期間。出價須超過最低增額。", es: "Los artistas establecen subastas de 3, 7 o 14 días. Las pujas deben superar el incremento mínimo." },
  },
  {
    q: { ko: "정산은 언제 되나요?", en: "When do I get paid?", ja: "いつ精算されますか？", zh: "何時結算？", es: "¿Cuándo me pagan?" },
    a: { ko: "콜렉터 검수 완료 후, 주간(매주 월요일) 또는 월간(매월 1일) 배치로 정산됩니다.", en: "After buyer inspection, settlements are processed weekly (Monday) or monthly (1st).", ja: "コレクターの検品完了後、週次（月曜）または月次（1日）で精算されます。", zh: "買家驗收完成後，每週一或每月1日結算。", es: "Después de la inspección del comprador, los pagos se procesan semanal o mensualmente." },
  },
  {
    q: { ko: "환불은 가능한가요?", en: "Can I get a refund?", ja: "返金は可能ですか？", zh: "可以退款嗎？", es: "¿Puedo obtener un reembolso?" },
    a: { ko: "배송 후 검수 단계에서 분쟁 신청이 가능합니다. 관리자가 중재합니다.", en: "You can file a dispute during the inspection phase after delivery. Our admin team will mediate.", ja: "配送後の検品段階で紛争申請が可能です。管理者が仲裁します。", zh: "交貨後驗收階段可提出爭議。管理員將進行調解。", es: "Puede presentar una disputa durante la inspección después de la entrega." },
  },
];

export default function SupportPage() {
  const { locale } = useI18n();
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactMessage, setContactMessage] = useState("");
  const [sent, setSent] = useState(false);

  const lang = locale as keyof (typeof FAQ)[0]["q"];

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">
        {locale === "ko" ? "고객 지원" : locale === "ja" ? "サポート" : locale === "zh" ? "客戶支援" : locale === "es" ? "Soporte" : "Support"}
      </h1>

      {/* FAQ */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-4">FAQ</h2>
        <div className="space-y-2">
          {FAQ.map((item, i) => (
            <div key={i} className="card overflow-hidden">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-surface-hover/30 transition-colors"
              >
                <span className="font-medium text-sm">{item.q[lang] || item.q.en}</span>
                <span className="text-text-muted">{openIdx === i ? "−" : "+"}</span>
              </button>
              {openIdx === i && (
                <div className="px-4 pb-4 text-sm text-text-secondary">
                  {item.a[lang] || item.a.en}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Contact Form */}
      <section>
        <h2 className="text-lg font-semibold mb-4">
          {locale === "ko" ? "문의하기" : locale === "ja" ? "お問い合わせ" : "Contact Us"}
        </h2>
        {sent ? (
          <div className="card p-6 text-center">
            <div className="text-4xl mb-3">✉️</div>
            <h3 className="font-bold mb-2">
              {locale === "ko" ? "문의가 접수되었습니다" : "Message sent"}
            </h3>
            <p className="text-text-muted text-sm">
              {locale === "ko" ? "빠른 시일 내 답변 드리겠습니다." : "We'll get back to you soon."}
            </p>
          </div>
        ) : (
          <div className="card p-6 space-y-4">
            <input type="text" value={contactName} onChange={(e) => setContactName(e.target.value)}
              placeholder={locale === "ko" ? "이름" : "Name"}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
            <input type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)}
              placeholder={locale === "ko" ? "이메일" : "Email"}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
            <textarea value={contactMessage} onChange={(e) => setContactMessage(e.target.value)}
              placeholder={locale === "ko" ? "문의 내용" : "Message"} rows={4}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none resize-none" />
            <button
              onClick={() => { if (contactEmail && contactMessage) setSent(true); }}
              disabled={!contactEmail || !contactMessage}
              className="btn-primary w-full disabled:opacity-50"
            >
              {locale === "ko" ? "문의 보내기" : "Send"}
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
