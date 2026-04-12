"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  fetchMe,
  fetchSystemSettings,
  loginWithMockEmail,
  SystemSettingView,
  tokenStore,
  updateSystemSetting,
} from "@/lib/api";

const KEY_LABELS: Record<string, string> = {
  bluebird_unit_price: "🕊 블루버드 단가",
  platform_fee_sponsorship: "후원 수수료율",
  platform_fee_auction: "경매 수수료율",
  platform_fee_buy_now: "즉시구매 수수료율",
  auction_payment_deadline_days: "경매 결제 기한",
  warning_threshold: "경고 누적 임계값",
};

export default function SystemSettingsPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [settings, setSettings] = useState<SystemSettingView[]>([]);
  const [draftJson, setDraftJson] = useState<Record<string, string>>({});
  const [acting, setActing] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loginEmail, setLoginEmail] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      if (!tokenStore.get()) {
        setMe(null);
        return;
      }
      const u = await fetchMe();
      setMe(u);
      if (u.role !== "admin") return;
      const list = await fetchSystemSettings();
      setSettings(list);
      const drafts: Record<string, string> = {};
      for (const s of list) {
        drafts[s.key] = JSON.stringify(s.value, null, 2);
      }
      setDraftJson(drafts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(key: string) {
    setError(null);
    setSavedKey(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(draftJson[key] || "{}");
    } catch {
      setError(`${key}: 잘못된 JSON 형식`);
      return;
    }
    setActing(key);
    try {
      const updated = await updateSystemSetting(key, parsed);
      setSettings((prev) =>
        prev.map((s) => (s.key === key ? updated : s))
      );
      setDraftJson((prev) => ({
        ...prev,
        [key]: JSON.stringify(updated.value, null, 2),
      }));
      setSavedKey(key);
      setTimeout(() => setSavedKey((k) => (k === key ? null : k)), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setActing(null);
    }
  }

  async function handleLogin() {
    try {
      const u = await loginWithMockEmail(loginEmail.trim());
      setMe(u);
      void load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 max-w-4xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">Admin</span>
          <h1 className="text-3xl font-bold mt-3">시스템 설정</h1>
          <p className="text-text-secondary text-sm mt-1">
            런타임 설정 — 변경 즉시 새 거래에 적용됩니다
          </p>
        </div>
        <nav className="flex gap-2">
          <Link href="/admin/dashboard" className="btn-ghost text-sm">
            대시보드
          </Link>
        </nav>
      </header>

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="admin@domo.example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {me && me.role !== "admin" && (
        <div className="card p-6">
          <p className="text-text-secondary">
            관리자 권한이 필요합니다. 현재 역할: <code>{me.role}</code>
          </p>
        </div>
      )}

      {error && (
        <div className="card border-danger p-4 mb-4 text-danger text-sm">
          {error}
        </div>
      )}

      {me && me.role === "admin" && (
        <>
          {loading ? (
            <div className="text-text-muted text-center py-8">로딩 중...</div>
          ) : settings.length === 0 ? (
            <div className="card p-12 text-center text-text-muted">
              설정 항목이 없습니다.
            </div>
          ) : (
            <ul className="space-y-4">
              {settings.map((s) => (
                <li key={s.key} className="card p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-text-muted text-xs mb-1">
                        {s.key}
                      </div>
                      <h3 className="font-semibold">
                        {KEY_LABELS[s.key] ?? s.key}
                      </h3>
                    </div>
                    <span className="text-text-muted text-xs">
                      수정:{" "}
                      {s.updated_at &&
                        new Date(s.updated_at).toLocaleString("ko-KR")}
                    </span>
                  </div>
                  <textarea
                    value={draftJson[s.key] ?? ""}
                    onChange={(e) =>
                      setDraftJson((prev) => ({
                        ...prev,
                        [s.key]: e.target.value,
                      }))
                    }
                    rows={3}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm font-mono mb-3 focus:border-primary outline-none resize-none"
                  />
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleSave(s.key)}
                      disabled={acting === s.key}
                      className="btn-primary text-xs disabled:opacity-50"
                    >
                      {acting === s.key ? "저장 중..." : "저장"}
                    </button>
                    {savedKey === s.key && (
                      <span className="text-primary text-xs">✓ 저장됨</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </main>
  );
}
