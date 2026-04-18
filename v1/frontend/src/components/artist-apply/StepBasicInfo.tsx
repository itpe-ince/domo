"use client";

import { useEffect, useRef, useState } from "react";
import {
  confirmEduVerification,
  SchoolSearchResult,
  searchSchools,
  sendEduVerification,
} from "@/lib/api";
import { GENRES, StepProps } from "./types";

export function StepBasicInfo({ data, onChange }: StepProps) {
  // School search
  const [schoolQuery, setSchoolQuery] = useState(data.school);
  const [schoolResults, setSchoolResults] = useState<SchoolSearchResult[]>([]);
  const [showSchoolDropdown, setShowSchoolDropdown] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Edu email verification
  const [eduEmail, setEduEmail] = useState(data.edu_email);
  const [verifyCode, setVerifyCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [schoolName, setSchoolName] = useState("");

  useEffect(() => {
    if (!schoolQuery || schoolQuery.length < 1) {
      setSchoolResults([]);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await searchSchools(schoolQuery);
        setSchoolResults(results);
        setShowSchoolDropdown(true);
      } catch {
        setSchoolResults([]);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [schoolQuery]);

  function selectSchool(school: SchoolSearchResult) {
    onChange({ school: school.name_ko });
    setSchoolQuery(school.name_ko);
    setSelectedDomain(school.email_domain);
    setSchoolName(school.name_ko);
    setShowSchoolDropdown(false);
    // Pre-fill email domain
    if (!eduEmail.includes("@")) {
      setEduEmail(`@${school.email_domain}`);
    }
  }

  async function handleSendCode() {
    if (!eduEmail || !eduEmail.includes("@")) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      const res = await sendEduVerification(eduEmail);
      setCodeSent(true);
      setSchoolName(res.school_name);
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : "발송 실패");
    } finally {
      setVerifying(false);
    }
  }

  async function handleConfirmCode() {
    if (!verifyCode || verifyCode.length !== 6) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      await confirmEduVerification(eduEmail, verifyCode);
      onChange({ edu_email: eduEmail, edu_email_verified: true });
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : "인증 실패");
    } finally {
      setVerifying(false);
    }
  }

  function addGenre(tag: string) {
    const t = tag.trim().toLowerCase();
    if (t && !data.genre_tags.includes(t) && data.genre_tags.length < 5) {
      onChange({ genre_tags: [...data.genre_tags, t] });
    }
  }

  return (
    <div className="space-y-4">
      {/* School search */}
      <div className="relative">
        <label className="block text-sm text-text-secondary mb-1">소속 학교 *</label>
        <input
          type="text"
          value={schoolQuery}
          onChange={(e) => {
            setSchoolQuery(e.target.value);
            onChange({ school: e.target.value });
          }}
          onFocus={() => schoolResults.length > 0 && setShowSchoolDropdown(true)}
          placeholder="학교명 검색 (예: 서울대, Parsons)"
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none"
        />
        {showSchoolDropdown && schoolResults.length > 0 && (
          <div className="absolute top-full mt-1 left-0 right-0 card p-1 z-40 shadow-xl max-h-40 overflow-y-auto">
            {schoolResults.map((s) => (
              <button
                key={s.id}
                onClick={() => selectSchool(s)}
                className="w-full text-left px-3 py-2 rounded text-sm hover:bg-surface-hover"
              >
                <div className="font-medium">{s.name_ko}</div>
                <div className="text-xs text-text-muted">{s.name_en} · {s.email_domain} · {s.country_code}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Department */}
      <div>
        <label className="block text-sm text-text-secondary mb-1">학과 *</label>
        <input
          type="text"
          value={data.department}
          onChange={(e) => onChange({ department: e.target.value })}
          placeholder="서양화과"
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none"
        />
      </div>

      {/* Graduation + Enrollment */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-text-secondary mb-1">졸업(예정) 연도 *</label>
          <input
            type="number"
            value={data.graduation_year}
            onChange={(e) => onChange({ graduation_year: Number(e.target.value) })}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none"
          />
        </div>
        <div className="flex items-end pb-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={data.is_enrolled}
              onChange={(e) => onChange({ is_enrolled: e.target.checked })}
              className="accent-primary"
            />
            현재 재학 중
          </label>
        </div>
      </div>

      {/* Edu Email Verification */}
      <div className="card p-4 space-y-3">
        <label className="block text-sm font-semibold">학교 이메일 인증</label>
        <p className="text-xs text-text-muted">
          등록된 학교의 이메일로 인증하면 "🎓 학교 인증 작가" 배지가 부여됩니다.
        </p>

        {data.edu_email_verified ? (
          <div className="flex items-center gap-2 text-sm text-primary">
            <span>✓ {data.edu_email} 인증 완료</span>
            {schoolName && <span className="text-text-muted">({schoolName})</span>}
          </div>
        ) : (
          <>
            <div className="flex gap-2">
              <input
                type="email"
                value={eduEmail}
                onChange={(e) => setEduEmail(e.target.value)}
                placeholder="학교이메일@snu.ac.kr"
                className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
              />
              <button
                onClick={handleSendCode}
                disabled={verifying || !eduEmail.includes("@")}
                className="btn-primary text-xs whitespace-nowrap disabled:opacity-50"
              >
                {verifying ? "..." : codeSent ? "재발송" : "인증 코드 발송"}
              </button>
            </div>

            {codeSent && (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="6자리 인증 코드"
                  maxLength={6}
                  className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none tracking-widest text-center"
                />
                <button
                  onClick={handleConfirmCode}
                  disabled={verifying || verifyCode.length !== 6}
                  className="btn-primary text-xs whitespace-nowrap disabled:opacity-50"
                >
                  {verifying ? "..." : "확인"}
                </button>
              </div>
            )}

            {verifyError && (
              <p className="text-xs text-danger">{verifyError}</p>
            )}

            <p className="text-xs text-text-muted">
              * 학교 이메일 인증은 선택사항이지만, 인증 시 심사 우선 처리됩니다.
            </p>
          </>
        )}
      </div>

      {/* Genre tags */}
      <div>
        <label className="block text-sm text-text-secondary mb-1">작업 장르/스타일 * (1~5개)</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {data.genre_tags.map((t) => (
            <span key={t} className="flex items-center gap-1 bg-surface rounded-full px-2.5 py-0.5 text-xs">
              {t}
              <button
                onClick={() => onChange({ genre_tags: data.genre_tags.filter((g) => g !== t) })}
                className="text-text-muted hover:text-danger"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {GENRES.filter((g) => !data.genre_tags.includes(g))
            .slice(0, 5)
            .map((g) => (
              <button
                key={g}
                onClick={() => addGenre(g)}
                disabled={data.genre_tags.length >= 5}
                className="text-xs px-2.5 py-1 rounded-full bg-surface hover:bg-surface-hover text-text-secondary disabled:opacity-30"
              >
                + {g}
              </button>
            ))}
        </div>
      </div>
    </div>
  );
}
