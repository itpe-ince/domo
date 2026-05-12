"use client";

type SupportedLocale = "ko" | "en" | "ja" | "zh" | "es";

const LOCALE_OPTIONS: SupportedLocale[] = ["ko", "en", "ja", "zh", "es"];

interface LocalePreviewToggleProps {
  value: SupportedLocale;
  onChange: (locale: SupportedLocale) => void;
}

export function LocalePreviewToggle({ value, onChange }: LocalePreviewToggleProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as SupportedLocale)}
      className="text-xs border border-admin-border rounded px-1 py-0.5 bg-admin-surface text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
    >
      {LOCALE_OPTIONS.map((locale) => (
        <option key={locale} value={locale}>
          {locale}
        </option>
      ))}
    </select>
  );
}
