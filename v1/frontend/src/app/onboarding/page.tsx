"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiClientError,
  ApiUser,
  completeOnboarding,
  fetchMe,
  loginWithMockEmail,
  requestGuardianConsent,
  tokenStore,
} from "@/lib/api";

const COUNTRIES = [
  { code: "KR", label: "Korea" },
  { code: "US", label: "United States" },
  { code: "JP", label: "Japan" },
  { code: "GB", label: "United Kingdom" },
  { code: "DE", label: "Germany" },
  { code: "FR", label: "France" },
  { code: "VN", label: "Vietnam" },
  { code: "PE", label: "Peru" },
  { code: "CO", label: "Colombia" },
  { code: "UA", label: "Ukraine" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loginEmail, setLoginEmail] = useState("");

  const [step, setStep] = useState<"basic" | "guardian" | "done">("basic");
  const [birthYear, setBirthYear] = useState<number | "">("");
  const [countryCode, setCountryCode] = useState("KR");
  const [guardianEmail, setGuardianEmail] = useState("");
  const [guardianName, setGuardianName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    if (!tokenStore.get()) return;
    try {
      setMe(await fetchMe());
    } catch {
      tokenStore.clear();
    }
  }

  async function handleLogin() {
    try {
      setMe(await loginWithMockEmail(loginEmail.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handleSubmitBasic() {
    if (typeof birthYear !== "number") {
      setError("생년을 입력해주세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await completeOnboarding({
        birth_year: birthYear,
        country_code: countryCode,
      });
      if (result.guardian_required) {
        setStep("guardian");
      } else {
        setStep("done");
        setTimeout(() => router.push("/"), 1500);
      }
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitGuardian() {
    if (!guardianEmail.includes("@")) {
      setError("유효한 보호자 이메일을 입력해주세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await requestGuardianConsent({
        guardian_email: guardianEmail,
        guardian_name: guardianName || undefined,
      });
      setStep("done");
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12">
      <header className="mb-8">
        <span className="badge-primary">Welcome</span>
        <h1 className="text-3xl font-bold mt-3">온보딩</h1>
        <p className="text-text-secondary text-sm mt-1">
          가입을 완료하려면 몇 가지 정보가 필요합니다.
        </p>
      </header>

      {error && (
        <div className="card border-danger p-3 text-danger text-sm mb-4">
          {error}
        </div>
      )}

      {!me && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
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

      {me && step === "basic" && (
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold">기본 정보</h2>
          <p className="text-text-secondary text-sm">
            생년 및 거주 국가를 입력해주세요. 미성년 기준은 국가별로 다릅니다
            (KR 14세, US 13세, EU 16세).
          </p>

          <div>
            <label className="block text-sm text-text-secondary mb-1">
              출생 연도
            </label>
            <input
              type="number"
              min={1900}
              max={new Date().getFullYear()}
              value={birthYear}
              onChange={(e) =>
                setBirthYear(e.target.value ? Number(e.target.value) : "")
              }
              placeholder="예: 2000"
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">
              거주 국가
            </label>
            <select
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSubmitBasic}
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? "처리 중..." : "다음"}
          </button>
        </div>
      )}

      {me && step === "guardian" && (
        <div className="card p-6 space-y-4">
          <div className="card border-warning p-3 text-warning text-sm">
            ⚠ 미성년자입니다. 보호자 동의가 필요합니다.
          </div>
          <h2 className="text-lg font-semibold">보호자 동의 요청</h2>
          <p className="text-text-secondary text-sm">
            보호자의 이메일로 동의 매직 링크가 발송됩니다. 보호자가 링크를
            클릭해야 계정이 활성화됩니다.
          </p>

          <div>
            <label className="block text-sm text-text-secondary mb-1">
              보호자 이메일 *
            </label>
            <input
              type="email"
              value={guardianEmail}
              onChange={(e) => setGuardianEmail(e.target.value)}
              placeholder="parent@example.com"
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">
              보호자 이름 (선택)
            </label>
            <input
              type="text"
              value={guardianName}
              onChange={(e) => setGuardianName(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-2 focus:border-primary outline-none"
            />
          </div>

          <button
            onClick={handleSubmitGuardian}
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? "전송 중..." : "매직 링크 발송"}
          </button>
        </div>
      )}

      {me && step === "done" && (
        <div className="card border-primary p-6 text-center">
          <p className="text-primary text-lg font-semibold mb-2">
            ✓ 완료되었습니다
          </p>
          <p className="text-text-secondary text-sm">
            {me.is_minor
              ? "보호자의 동의를 기다려주세요. 동의 완료 시 알림이 전송됩니다."
              : "계정이 활성화되었습니다. 홈으로 이동합니다..."}
          </p>
          <Link href="/" className="btn-secondary text-sm mt-4 inline-block">
            홈으로
          </Link>
        </div>
      )}
    </main>
  );
}
