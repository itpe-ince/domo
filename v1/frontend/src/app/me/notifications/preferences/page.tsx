"use client";

/**
 * /me/notifications/preferences — B'-3 push-email-digest-foundation
 *
 * Per-type opt-in toggle UI for push and email digest notifications.
 * GDPR compliant: all toggles default to off. User must actively enable.
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
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
      <span className="text-sm text-gray-700">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-1 ${
          checked ? "bg-amber-500" : "bg-gray-300"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
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
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-base font-semibold text-gray-900">{title}</h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function NotificationPreferencesPage() {
  const { t } = useI18n();
  const { me: user } = useMe();

  const [prefs, setPrefs] = useState<NotificationPreferencesView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; ok: boolean } | null>(null);

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

  const updatePushMaster = (v: boolean) => {
    save({ push_enabled: v });
  };

  const updateEmailMaster = (v: boolean) => {
    save({ email_enabled: v });
  };

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

  const updateFrequency = (freq: DigestFrequency) => {
    save({ digest_frequency: freq });
  };

  if (!user) {
    return (
      <div className="p-8 text-center text-gray-500">
        {t("notifications.loginRequired")}
      </div>
    );
  }

  if (loading || !prefs) {
    return (
      <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
    );
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-8">
      {/* Toast */}
      {toast && (
        <div
          className={`mb-4 rounded-lg px-4 py-3 text-sm ${
            toast.ok
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {toast.message}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">
          {t("notifications.preferences.title")}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("notifications.preferences.subtitle")}
        </p>
        <p className="mt-2 text-xs text-gray-400">
          {t("notifications.preferences.gdprNote")}
        </p>
      </div>

      <div className="space-y-6">
        {/* Push Notifications */}
        <SectionCard title={t("notifications.preferences.pushSection")}>
          <Toggle
            checked={prefs.push_enabled}
            onChange={updatePushMaster}
            label={t("notifications.preferences.pushEnabled")}
            disabled={saving}
          />

          {prefs.push_enabled && (
            <div className="mt-3 ml-2 space-y-3 border-l-2 border-amber-200 pl-4">
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

        {/* Email Digest */}
        <SectionCard title={t("notifications.preferences.emailSection")}>
          <Toggle
            checked={prefs.email_enabled}
            onChange={updateEmailMaster}
            label={t("notifications.preferences.emailEnabled")}
            disabled={saving}
          />

          {prefs.email_enabled && (
            <>
              {/* Per-type email overrides */}
              <div className="mt-3 ml-2 space-y-3 border-l-2 border-amber-200 pl-4">
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

              {/* Digest frequency selector */}
              <div className="mt-4">
                <p className="mb-2 text-sm font-medium text-gray-700">
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
                          ? "bg-amber-500 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
      </div>
    </div>
  );
}
