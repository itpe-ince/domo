"use client";

import { useState } from "react";
import { ApplyArtistInput, applyArtist } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { LoginModal } from "@/components/LoginModal";
import { StepBasicInfo } from "@/components/artist-apply/StepBasicInfo";
import { StepWorks } from "@/components/artist-apply/StepWorks";
import { StepPortfolio } from "@/components/artist-apply/StepPortfolio";
import { StepHistory } from "@/components/artist-apply/StepHistory";
import type { ApplicationFormData } from "@/components/artist-apply/types";

type Step = 1 | 2 | 3 | 4;

const INITIAL_FORM: ApplicationFormData = {
  school: "",
  department: "",
  graduation_year: 2026,
  is_enrolled: true,
  genre_tags: [],
  edu_email: "",
  edu_email_verified: false,
  representative_works: [
    { title: "", image_url: "", description: "", dimensions: "", medium: "", year: 2026 },
    { title: "", image_url: "", description: "", dimensions: "", medium: "", year: 2026 },
    { title: "", image_url: "", description: "", dimensions: "", medium: "", year: 2026 },
  ],
  statement: "",
  enrollment_proof_url: "",
  portfolio_urls: "",
  intro_video_url: "",
  exhibitions: [],
  awards: [],
};

export default function ApplyArtistPage() {
  const { me, loading: meLoading } = useMe();
  const [loginOpen, setLoginOpen] = useState(false);
  const [step, setStep] = useState<Step>(1);
  const [form, setForm] = useState<ApplicationFormData>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function updateForm(partial: Partial<ApplicationFormData>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  if (!meLoading && !me) {
    return (
      <>
        <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-bold mb-4">작가 심사 신청</h1>
          <p className="text-text-muted mb-4">로그인 후 신청할 수 있습니다.</p>
          <button onClick={() => setLoginOpen(true)} className="btn-primary">로그인</button>
        </main>
        <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} redirectTo="/artists/apply" />
      </>
    );
  }

  if (me?.role === "artist") {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12">
        <div className="card p-6">
          <h2 className="text-lg font-bold">이미 작가입니다</h2>
          <p className="text-text-muted text-sm mt-2">{me.email}님은 승인된 작가입니다.</p>
        </div>
      </main>
    );
  }

  if (success) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-4">🎨</div>
        <h2 className="text-2xl font-bold mb-2">심사 신청 완료</h2>
        <p className="text-text-muted">관리자 검토 후 결과를 알림으로 알려드립니다.</p>
      </main>
    );
  }

  function canNext(): boolean {
    if (step === 1) return !!form.school && !!form.department && form.genre_tags.length >= 1;
    if (step === 2) return form.representative_works.filter((w) => w.title && w.image_url).length >= 3;
    if (step === 3) return form.statement.length > 0 && form.statement.length <= 200 && !!form.enrollment_proof_url;
    return true;
  }

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      const input: ApplyArtistInput = {
        school: form.school,
        department: form.department,
        graduation_year: form.graduation_year,
        is_enrolled: form.is_enrolled,
        genre_tags: form.genre_tags,
        statement: form.statement,
        enrollment_proof_url: form.enrollment_proof_url,
        representative_works: form.representative_works.filter((w) => w.title && w.image_url),
        portfolio_urls: form.portfolio_urls.split(/[\n,]/).map((s) => s.trim()).filter(Boolean) || undefined,
        intro_video_url: form.intro_video_url || undefined,
        exhibitions: form.exhibitions.length ? form.exhibitions : undefined,
        awards: form.awards.length ? form.awards : undefined,
      };
      await applyArtist(input);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "신청 실패");
    } finally {
      setSubmitting(false);
    }
  }

  const stepLabels = ["기본 정보", "대표 작품", "포트폴리오", "이력"];

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-2">작가 심사 신청</h1>
      <p className="text-text-muted text-sm mb-6">Step {step}/4 — {stepLabels[step - 1]}</p>

      <div className="flex gap-1 mb-8">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className={`h-1 flex-1 rounded-full ${s <= step ? "bg-primary" : "bg-surface-hover"}`} />
        ))}
      </div>

      {error && <div className="card border-danger p-3 text-danger text-sm mb-4">{error}</div>}

      {step === 1 && <StepBasicInfo data={form} onChange={updateForm} />}
      {step === 2 && <StepWorks data={form} onChange={updateForm} />}
      {step === 3 && <StepPortfolio data={form} onChange={updateForm} />}
      {step === 4 && <StepHistory data={form} onChange={updateForm} />}

      <div className="flex justify-between mt-8">
        {step > 1 ? (
          <button onClick={() => setStep((step - 1) as Step)}
            className="text-sm text-text-muted hover:text-text-primary">← 이전</button>
        ) : <div />}
        {step < 4 ? (
          <button onClick={() => setStep((step + 1) as Step)} disabled={!canNext()}
            className="btn-primary text-sm disabled:opacity-50">다음 →</button>
        ) : (
          <button onClick={handleSubmit} disabled={submitting}
            className="btn-primary text-sm disabled:opacity-50">
            {submitting ? "제출 중..." : "심사 신청"}
          </button>
        )}
      </div>
    </main>
  );
}
