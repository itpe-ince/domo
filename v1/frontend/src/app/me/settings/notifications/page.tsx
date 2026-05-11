"use client";

/**
 * /me/settings/notifications — 알림 + 뉴스레터 통합 페이지
 * (이전 경로: /me/notifications/preferences + /me/newsletter)
 *
 * Per-type opt-in toggle for push/email notifications (GDPR default: off).
 * Newsletter subscription section appended at the bottom.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useMyNewsletterPreferences } from "@/lib/hooks/useMyNewsletterPreferences";
import {
  fetchNotificationPreferences,
  patchNotificationPreferences,
  NotificationPreferencesView,
  NotificationPreferencesPatch,
} from "@/lib/api";

const NOTIFICATION_TYPES = [
  "auction",
  "sponsorship",
  "engagement",
  "system",
  "digest",
] as const;

type NotificationType = (typeof NOTIFICATION_TYPES)[number];
type DigestFrequency = "weekly" | "biweekly" | "monthly" | "never";

const DIGEST_FREQUENCIES: { value: DigestFrequency; labelKey: string }[] = [
  { value: "weekly", labelKey: "notifications.preferences.frequency.weekly" },
  { value: "biweekly", labelKey: "notifications.preferences.frequency.biweekly" },
  { value: "monthly", labelKey: "notifications.preferences.frequency.monthly" },
  { value: "never", labelKey: "notifications.preferences.frequency.never" },
];

const NEWSLETTER_LOCALES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
] as const;

const NEWSLETTER_FREQUENCIES = [
  { value: "weekly", labelKey: "newsletter.preferences.frequency.weekly" },
  { value: "biweekly", labelKey: "newsletter.preferences.frequency.biweekly" },
  { value: "monthly", labelKey: "newsletter.preferences.frequency.monthly" },
  { value: "never", labelKey: "newsletter.preferences.frequency.never" },
] as const;

function Toggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-center justify-between gap-3 cursor-pointer select-none">
      <span className="text-sm text-text-primary">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 ${
          checked ? "bg-primary" : "bg-border"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-background shadow transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </label>
  );
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <h2 className="mb-4 text-base font-semibold text-text-primary">{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function NotificationsSettingsPage() {
  const { t } = useI18n();
  const { me: user } = useMe();

  // ── 알림 preferences 상태 ──
  const [prefs, setPrefs] = useState<NotificationPreferencesView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; ok: boolean } | null>(null);

  // ── 뉴스레터 preferences 상태 ──
  const {
    preferences: newsletter,
    loading: newsletterLoading,
    saving: newsletterSaving,
    saveError: newsletterSaveError,
    setSubscribed,
    setFrequency: setNewsletterFrequency,
    setLocale: setNewsletterLocale,
  } = useMyNewsletterPreferences();

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetchNotificationPreferences()
      .then(setPrefs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const save = async (patch: NotificationPreferencesPatch) => {
    setSaving(true);
    try {
      const updated = await patchNotificationPreferences(patch);
      setPrefs(updated);
      setToast({ message: t("notifications.preferences.saveSuccess"), ok: true });
    } catch {
      setToast({ message: t("notifications.preferences.saveError"), ok: false });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  const updatePushMaster = (v: boolean) => save({ push_enabled: v });
  const updateEmailMaster = (v: boolean) => save({ email_enabled: v });

  const updatePushType = (type: NotificationType, v: boolean) => {
    const current = prefs?.push_per_type ?? {};
    save({ push_per_type: { [type]: v } });
    setPrefs((p) =>
      p ? { ...p, push_per_type: { ...current, [type]: v } } : p
    );
  };

  const updateEmailType = (type: NotificationType, v: boolean) => {
    const current = prefs?.email_per_type ?? {};
    save({ email_per_type: { [type]: v } });
    setPrefs((p) =>
      p ? { ...p, email_per_type: { ...current, [type]: v } } : p
    );
  };

  const updateFrequency = (freq: DigestFrequency) => save({ digest_frequency: freq });

  if (!user) {
    return (
      <div className="p-8 text-center text-text-muted">
        {t("notifications.loginRequired")}
      </div>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav aria-label="breadcrumb" className="mb-6">
        <Link
          href="/me/settings"
          className="text-text-muted text-sm hover:text-primary"
        >
          ← {t("settings.hub.title")}
        </Link>
      </nav>

      {/* Page header */}
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          {t("notifications.preferences.title")}
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          {t("notifications.preferences.subtitle")}
        </p>
        <p className="mt-2 text-xs text-text-muted">
          {t("notifications.preferences.gdprNote")}
        </p>
      </header>

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className={`mb-4 rounded-lg px-4 py-3 text-sm ${
            toast.ok
              ? "bg-success/10 text-success border border-success/20"
              : "bg-danger/10 text-danger border border-danger/20"
          }`}
        >
          {toast.message}
        </div>
      )}

      {loading || !prefs ? (
        <div className="p-8 text-center text-text-muted">{t("common.loading")}</div>
      ) : (
        <div className="space-y-6">
          {/* ── 섹션 1: 푸시 알림 ── */}
          <SectionCard title={t("notifications.preferences.pushSection")}>
            <Toggle
              checked={prefs.push_enabled}
              onChange={updatePushMaster}
              label={t("notifications.preferences.pushEnabled")}
              disabled={saving}
            />
            {prefs.push_enabled && (
              <div className="mt-3 ml-2 space-y-3 border-l-2 border-primary/20 pl-4">
                {NOTIFICATION_TYPES.map((type) => (
                  <Toggle
                    key={type}
                    checked={
                      prefs.push_per_type[type] !== undefined
                        ? prefs.push_per_type[type]
                        : prefs.push_enabled
                    }
                    onChange={(v) => updatePushType(type, v)}
                    label={t("notifications.preferences.types." + type)}
                    disabled={saving}
                  />
                ))}
              </div>
            )}
          </SectionCard>

          {/* ── 섹션 2: 이메일 알림 ── */}
          <SectionCard title={t("notifications.preferences.emailSection")}>
            <Toggle
              checked={prefs.email_enabled}
              onChange={updateEmailMaster}
              label={t("notifications.preferences.emailEnabled")}
              disabled={saving}
            />
            {prefs.email_enabled && (
              <>
                <div className="mt-3 ml-2 space-y-3 border-l-2 border-primary/20 pl-4">
                  {NOTIFICATION_TYPES.map((type) => (
                    <Toggle
                      key={type}
                      checked={
                        prefs.email_per_type[type] !== undefined
                          ? prefs.email_per_type[type]
                          : prefs.email_enabled
                      }
                      onChange={(v) => updateEmailType(type, v)}
                      label={t("notifications.preferences.types." + type)}
                      disabled={saving}
                    />
                  ))}
                </div>
                <div className="mt-4">
                  <p className="mb-2 text-sm font-medium text-text-primary">
                    {t("notifications.preferences.digestFrequency")}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {DIGEST_FREQUENCIES.map(({ value, labelKey }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => updateFrequency(value)}
                        disabled={saving}
                        className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          prefs.digest_frequency === value
                            ? "bg-primary text-white"
                            : "bg-surface-hover text-text-muted hover:text-text-primary"
                        } disabled:opacity-50`}
                      >
                        {t(labelKey)}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </SectionCard>

          {/* ── 섹션 3: 이메일 다이제스트 (뉴스레터) ── */}
          <SectionCard title={t("newsletter.preferences.title")}>
            {newsletterLoading ? (
              <p className="text-text-muted text-sm">{t("common.loading")}</p>
            ) : newsletter ? (
              <>
                {/* 구독 토글 */}
                <Toggle
                  checked={newsletter.is_subscribed}
                  onChange={(v) => setSubscribed(v)}
                  label={t("newsletter.preferences.subscribe.label")}
                  disabled={newsletterSaving}
                />
                {newsletter.is_subscribed && (
                  <p className="text-xs text-text-muted ml-0">
                    {t("newsletter.preferences.subscribe.hint")}
                  </p>
                )}

                {/* 발송 주기 */}
                <div>
                  <label
                    htmlFor="newsletter-frequency"
                    className="block text-sm font-medium text-text-primary mb-1"
                  >
                    {t("newsletter.preferences.frequency.label")}
                  </label>
                  <select
                    id="newsletter-frequency"
                    value={newsletter.frequency}
                    onChange={(e) =>
                      setNewsletterFrequency(
                        e.target.value as "weekly" | "biweekly" | "monthly" | "never"
                      )
                    }
                    disabled={newsletterSaving}
                    className="w-full max-w-xs rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
                  >
                    {NEWSLETTER_FREQUENCIES.map(({ value, labelKey }) => (
                      <option key={value} value={value}>
                        {t(labelKey)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 발송 언어 */}
                <div>
                  <label
                    htmlFor="newsletter-locale"
                    className="block text-sm font-medium text-text-primary mb-1"
                  >
                    {t("newsletter.preferences.locale.label")}
                  </label>
                  <select
                    id="newsletter-locale"
                    value={newsletter.preferred_locale}
                    onChange={(e) => setNewsletterLocale(e.target.value)}
                    disabled={newsletterSaving}
                    className="w-full max-w-xs rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
                  >
                    {NEWSLETTER_LOCALES.map(({ value, label }) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 마지막 발송일 */}
                {newsletter.last_sent_at && (
                  <p className="text-xs text-text-muted">
                    {t("newsletter.preferences.lastSent", {
                      date: new Date(newsletter.last_sent_at).toLocaleDateString(),
                    })}
                  </p>
                )}

                {/* 구독 해제 안내 */}
                <p className="text-xs text-text-muted">
                  {t("newsletter.preferences.unsubscribeNote")}
                </p>

                {newsletterSaveError && (
                  <p className="text-xs text-danger">{newsletterSaveError}</p>
                )}
              </>
            ) : null}
          </SectionCard>
        </div>
      )}
    </main>
  );
}
