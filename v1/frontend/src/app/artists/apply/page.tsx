"use client";

import { useEffect, useState } from "react";
import {
  ApiUser,
  ArtistApplication,
  applyArtist,
  fetchMe,
  fetchMyApplications,
  loginWithMockEmail,
  tokenStore,
} from "@/lib/api";

export default function ApplyArtistPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [myApps, setMyApps] = useState<ArtistApplication[]>([]);
  const [loginEmail, setLoginEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [school, setSchool] = useState("");
  const [intro, setIntro] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [statement, setStatement] = useState("");

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    if (!tokenStore.get()) return;
    try {
      const user = await fetchMe();
      setMe(user);
      const apps = await fetchMyApplications();
      setMyApps(apps);
    } catch {
      tokenStore.clear();
      setMe(null);
    }
  }

  async function handleLogin() {
    setError(null);
    try {
      const user = await loginWithMockEmail(loginEmail.trim());
      setMe(user);
      const apps = await fetchMyApplications();
      setMyApps(apps);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      const portfolioUrls = portfolio
        .split(/[\n,]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const created = await applyArtist({
        school: school || undefined,
        intro_video_url: intro || undefined,
        portfolio_urls: portfolioUrls.length ? portfolioUrls : undefined,
        statement: statement || undefined,
      });
      setMyApps((prev) => [created, ...prev]);
      setSchool("");
      setIntro("");
      setPortfolio("");
      setStatement("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Apply failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-2xl mx-auto">
      <div className="mb-10">
        <span className="badge-primary">Artist</span>
        <h1 className="text-3xl font-bold mt-3">작가 심사 신청</h1>
        <p className="text-text-secondary text-sm mt-1">
          포트폴리오와 자기소개를 제출하고 작가 권한을 받으세요.
        </p>
      </div>

      {error && (
        <div className="card border-danger p-4 mb-6 text-danger text-sm">
          {error}
        </div>
      )}

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="email@example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {me && me.role === "artist" && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold">이미 작가입니다</h2>
          <p className="text-text-secondary text-sm mt-2">
            {me.email}님은 이미 승인된 작가입니다.
          </p>
        </div>
      )}

      {me && me.role !== "artist" && (
        <>
          {myApps.some((a) => a.status === "pending") ? (
            <div className="card p-6 mb-6">
              <h2 className="text-lg font-semibold">심사 진행 중</h2>
              <p className="text-text-secondary text-sm mt-2">
                관리자 승인 대기 중입니다. 결과는 알림으로 전달됩니다.
              </p>
            </div>
          ) : (
            <div className="card p-6 mb-6 space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  학교
                </label>
                <input
                  type="text"
                  value={school}
                  onChange={(e) => setSchool(e.target.value)}
                  placeholder="Lima Art Academy"
                  className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary focus:border-primary outline-none"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  소개 영상 URL
                </label>
                <input
                  type="url"
                  value={intro}
                  onChange={(e) => setIntro(e.target.value)}
                  placeholder="https://youtube.com/watch?v=..."
                  className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary focus:border-primary outline-none"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  포트폴리오 URL (줄바꿈으로 구분)
                </label>
                <textarea
                  value={portfolio}
                  onChange={(e) => setPortfolio(e.target.value)}
                  rows={3}
                  placeholder="https://...&#10;https://..."
                  className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary focus:border-primary outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  자기소개
                </label>
                <textarea
                  value={statement}
                  onChange={(e) => setStatement(e.target.value)}
                  rows={5}
                  placeholder="저는 페루 리마에서 활동하는..."
                  className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary focus:border-primary outline-none resize-none"
                />
              </div>

              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary w-full disabled:opacity-50"
              >
                {submitting ? "제출 중..." : "심사 신청"}
              </button>
            </div>
          )}

          {myApps.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold mb-3">신청 이력</h3>
              <div className="space-y-3">
                {myApps.map((a) => (
                  <div key={a.id} className="card p-4 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="badge-primary">{a.status}</span>
                      <span className="text-text-muted text-xs">
                        {new Date(a.created_at).toLocaleString("ko-KR")}
                      </span>
                    </div>
                    {a.review_note && (
                      <p className="text-text-secondary mt-2 text-xs">
                        메모: {a.review_note}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}
