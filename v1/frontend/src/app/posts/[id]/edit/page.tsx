"use client";

/**
 * /posts/[id]/edit — 작가 포스트 편집 페이지 (CO-1 PR-3)
 *
 * K-5 작가 콘솔 보강:
 *  - 도슨트 직접 작성 textarea (artist_docent_text)
 *  - "AI 도슨트 생성" 버튼 + 결과 미리보기
 *  - opt-out 토글 (ai_docent_opted_out)
 *
 * 현재 범위: 도슨트 편집 섹션만 포함 (전체 포스트 편집은 Phase 11 대상)
 */

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  fetchDocent,
  generateDocent,
  patchArtistDocent,
  patchDocentOptOut,
  DocentView,
  DocentGenerateResult,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { LoginModal } from "@/components/LoginModal";

export const dynamic = "force-dynamic";

export default function PostEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t } = useI18n();
  const { me, loading: meLoading } = useMe();
  const [loginOpen, setLoginOpen] = useState(false);

  // 도슨트 상태
  const [docent, setDocent] = useState<DocentView | null>(null);
  const [artistText, setArtistText] = useState("");
  const [optedOut, setOptedOut] = useState(false);
  const [aiPreview, setAiPreview] = useState<string | null>(null);

  // UI 상태
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [savingOptOut, setSavingOptOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // 도슨트 데이터 로드
  useEffect(() => {
    if (!id) return;
    void (async () => {
      try {
        const d = await fetchDocent(id, "ko");
        setDocent(d);
        setArtistText(d.artist_docent_text ?? "");
        setOptedOut(d.ai_docent_opted_out);
        setAiPreview(d.ai_docent_text);
      } catch {
        setError("도슨트 정보를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  // 로그인 미인증 처리
  useEffect(() => {
    if (!meLoading && !me) {
      setLoginOpen(true);
    }
  }, [me, meLoading]);

  // 작가 직접 해설 저장
  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const result = await patchArtistDocent(id, artistText || null);
      setDocent((prev) =>
        prev ? { ...prev, artist_docent_text: result.artist_docent_text } : prev
      );
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setError("저장에 실패했습니다. 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  // AI 도슨트 생성
  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const result: DocentGenerateResult = await generateDocent(id);
      setAiPreview(result.ai_docent_text);
      setDocent((prev) =>
        prev ? { ...prev, ai_docent_text: result.ai_docent_text } : prev
      );
    } catch {
      setError(t("docent.generate_failed") || "도슨트 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setGenerating(false);
    }
  }

  // opt-out 토글
  async function handleOptOutToggle() {
    setSavingOptOut(true);
    setError(null);
    const newValue = !optedOut;
    try {
      const result = await patchDocentOptOut(id, newValue);
      setOptedOut(result.ai_docent_opted_out);
      setDocent((prev) =>
        prev ? { ...prev, ai_docent_opted_out: result.ai_docent_opted_out } : prev
      );
    } catch {
      setError("설정 변경에 실패했습니다.");
    } finally {
      setSavingOptOut(false);
    }
  }

  if (loading || meLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4 animate-pulse">
        <div className="h-6 w-48 bg-surface-hover rounded" />
        <div className="h-32 w-full bg-surface-hover rounded-lg" />
        <div className="h-10 w-32 bg-surface-hover rounded" />
      </div>
    );
  }

  return (
    <>
      {loginOpen && (
        <LoginModal
          open={loginOpen}
          onClose={() => setLoginOpen(false)}
          redirectTo={`/posts/${id}/edit`}
        />
      )}

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* 헤더 */}
        <div className="flex items-center gap-3">
          <Link
            href={`/posts/${id}`}
            className="text-sm text-text-muted hover:text-primary transition-colors"
          >
            ← 작품으로 돌아가기
          </Link>
        </div>

        <h1 className="text-xl font-bold">
          {t("docent.edit_page.section_title") || "도슨트 편집"}
        </h1>

        {/* 오류 메시지 */}
        {error && (
          <div
            role="alert"
            className="card border-danger p-3 text-sm text-danger"
          >
            {error}
          </div>
        )}

        {/* 저장 성공 메시지 */}
        {saveSuccess && (
          <div
            role="status"
            className="card border-primary p-3 text-sm text-primary"
          >
            {t("docent.edit_page.save_success") || "저장되었습니다"}
          </div>
        )}

        {/* ── 작가 직접 작성 섹션 ── */}
        <section className="card p-5 space-y-4">
          <h2 className="text-base font-semibold">
            {t("docent.artist_label") || "작가의 말"}
          </h2>

          <div className="space-y-2">
            <label
              htmlFor="artist-docent-text"
              className="text-sm text-text-secondary"
            >
              {t("docent.edit_page.artist_text_label") || "직접 작성"}
            </label>
            <textarea
              id="artist-docent-text"
              value={artistText}
              onChange={(e) => setArtistText(e.target.value)}
              rows={6}
              placeholder={
                t("docent.edit_page.artist_text_placeholder") ||
                "작품에 대한 이야기를 직접 작성해 주세요. 제작 과정, 영감의 원천, 작품이 담고 있는 의미 등을 자유롭게 서술할 수 있습니다."
              }
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary outline-none resize-none"
            />
            <div className="text-xs text-text-muted text-right">
              {artistText.length}자
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary text-sm px-4 py-2 disabled:opacity-50"
          >
            {saving
              ? "저장 중..."
              : (t("docent.edit_page.save_button") || "저장")}
          </button>
        </section>

        {/* ── AI 도슨트 섹션 ── */}
        <section className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              {t("docent.ai_label") || "AI 도슨트"}
            </h2>
            <span className="text-xs bg-surface-alt text-text-muted px-2 py-0.5 rounded-full">
              {t("docent.ai_disclaimer") || "AI 생성"}
            </span>
          </div>

          {/* opt-out 토글 */}
          <div className="flex items-center justify-between py-2 border-b border-border">
            <div>
              <div className="text-sm font-medium">
                {t("docent.edit_page.opt_out_label") || "AI 도슨트 비활성화"}
              </div>
              <div className="text-xs text-text-muted mt-0.5">
                {optedOut
                  ? (t("docent.disabled_by_artist") || "AI 도슨트가 비활성화되어 있습니다.")
                  : (t("docent.rate_limit_notice") || "AI 도슨트는 1일 2회까지 생성 가능합니다.")}
              </div>
            </div>
            <button
              role="switch"
              aria-checked={optedOut}
              onClick={handleOptOutToggle}
              disabled={savingOptOut}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 ${
                optedOut ? "bg-text-muted" : "bg-primary"
              }`}
            >
              <span className="sr-only">
                {optedOut
                  ? (t("docent.opt_in_label") || "AI 도슨트 활성화")
                  : (t("docent.opt_out_label") || "AI 도슨트 비활성화")}
              </span>
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  optedOut ? "translate-x-1" : "translate-x-6"
                }`}
                aria-hidden="true"
              />
            </button>
          </div>

          {/* AI 도슨트 생성 버튼 */}
          {!optedOut && (
            <div className="space-y-3">
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="btn-secondary text-sm px-4 py-2 disabled:opacity-50"
              >
                {generating
                  ? (t("docent.generating") || "AI가 작품을 분석하는 중...")
                  : (t("docent.edit_page.generate_button") || "AI 도슨트 생성")}
              </button>

              {/* AI 도슨트 미리보기 */}
              {aiPreview && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-text-secondary">
                    {generating ? "생성 중..." : "현재 AI 도슨트 미리보기"}
                  </div>
                  <div className="bg-surface-hover rounded-lg p-3">
                    <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                      {aiPreview}
                    </p>
                  </div>
                </div>
              )}

              {!aiPreview && !generating && (
                <p className="text-sm text-text-muted">
                  아직 AI 도슨트가 생성되지 않았습니다. 버튼을 눌러 생성해 보세요.
                </p>
              )}
            </div>
          )}

          {optedOut && (
            <p className="text-sm text-text-muted">
              AI 도슨트가 비활성화된 상태입니다. 토글을 켜면 다시 활성화됩니다.
            </p>
          )}
        </section>

        {/* 하단 링크 */}
        <div className="flex justify-end">
          <Link
            href={`/posts/${id}`}
            className="text-sm text-text-muted hover:text-primary transition-colors"
          >
            {t("common.back") || "돌아가기"}
          </Link>
        </div>
      </div>
    </>
  );
}
