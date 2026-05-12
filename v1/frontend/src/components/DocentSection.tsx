"use client";

/**
 * DocentSection — K-5 도슨트 섹션 컴포넌트 (CO-1 PR-3 분리)
 *
 * 분리 출처: /app/posts/[id]/page.tsx L120~211 inline 컴포넌트
 * Props: { docent, locale, isArtist }
 *
 * - 작가 직접 해설(artist_docent_text)은 항상 최상단 표시
 * - AI 도슨트는 토글 방식으로 표시 (접힘 기본값)
 * - opted_out=true 이면 AI 도슨트 블록 숨김
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { DocentView } from "@/lib/api";

export interface DocentSectionProps {
  docent: DocentView;
  locale?: string;
  isArtist?: boolean;
}

export function DocentSection({ docent }: DocentSectionProps) {
  const { t } = useI18n();
  const [aiExpanded, setAiExpanded] = useState(false);

  const hasArtistDocent = Boolean(docent.artist_docent_text);
  const hasAiDocent = Boolean(docent.ai_docent_text) && !docent.ai_docent_opted_out;

  // 도슨트 섹션 자체를 숨김 (둘 다 없는 경우)
  if (!hasArtistDocent && !hasAiDocent) return null;

  return (
    <section
      aria-labelledby="docent-heading"
      className="card p-5 space-y-4"
    >
      <h3
        id="docent-heading"
        className="text-sm font-semibold text-text-secondary uppercase tracking-wide"
      >
        {t("docent.title") || "작품 해설"}
      </h3>

      {/* 작가 직접 해설 — 우선 표시 */}
      {hasArtistDocent && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-primary">
              {t("docent.artist_label") || "작가의 말"}
            </span>
            <span className="text-xs text-text-muted">
              · {t("docent.by_artist") || "작가 직접 작성"}
            </span>
          </div>
          <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
            {docent.artist_docent_text}
          </p>
        </div>
      )}

      {/* AI 도슨트 토글 */}
      {hasAiDocent && (
        <div className="space-y-2">
          <button
            onClick={() => setAiExpanded((prev) => !prev)}
            aria-expanded={aiExpanded}
            aria-controls="ai-docent-content"
            className="flex items-center gap-2 text-xs text-text-secondary hover:text-primary transition-colors"
          >
            <span aria-hidden="true">{aiExpanded ? "▲" : "▼"}</span>
            <span>
              {aiExpanded
                ? (t("docent.toggle_hide") || "AI 도슨트 해설 접기")
                : (t("docent.toggle_show") || "AI 도슨트 해설 보기")}
            </span>
          </button>

          {aiExpanded && (
            <div
              id="ai-docent-content"
              className="space-y-3 pt-1"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-secondary">
                  {t("docent.ai_label") || "AI 도슨트"}
                </span>
                <span className="text-xs bg-surface-alt text-text-muted px-2 py-0.5 rounded-full">
                  {t("docent.ai_disclaimer") || "이 해설은 AI가 생성했습니다"}
                </span>
              </div>
              <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                {/* locale_docent: 현재 locale 번역, 없으면 한국어 fallback */}
                {docent.locale_docent ?? docent.ai_docent_text}
              </p>
              {docent.locale_docent === null && docent.ai_docent_text && (
                <p className="text-xs text-text-muted italic">
                  {t("docent.locale_only_ko") || "한국어로만 제공됩니다"}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
