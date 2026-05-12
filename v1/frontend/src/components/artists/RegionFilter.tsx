"use client";

import { useI18n } from "@/i18n";

// README target regions first (Southeast Asia, LATAM, Eastern Europe, East Asia, North America, Europe)
const REGIONS = [
  { code: "TH", label: "🇹🇭 Thailand" },
  { code: "VN", label: "🇻🇳 Vietnam" },
  { code: "ID", label: "🇮🇩 Indonesia" },
  { code: "PH", label: "🇵🇭 Philippines" },
  { code: "MY", label: "🇲🇾 Malaysia" },
  { code: "PE", label: "🇵🇪 Peru" },
  { code: "BR", label: "🇧🇷 Brazil" },
  { code: "CO", label: "🇨🇴 Colombia" },
  { code: "MX", label: "🇲🇽 Mexico" },
  { code: "AR", label: "🇦🇷 Argentina" },
  { code: "UA", label: "🇺🇦 Ukraine" },
  { code: "PL", label: "🇵🇱 Poland" },
  { code: "RO", label: "🇷🇴 Romania" },
  { code: "KR", label: "🇰🇷 Korea" },
  { code: "JP", label: "🇯🇵 Japan" },
  { code: "CN", label: "🇨🇳 China" },
  { code: "TW", label: "🇹🇼 Taiwan" },
  { code: "US", label: "🇺🇸 United States" },
  { code: "GB", label: "🇬🇧 United Kingdom" },
  { code: "DE", label: "🇩🇪 Germany" },
  { code: "FR", label: "🇫🇷 France" },
];

interface RegionFilterProps {
  value: string;
  onChange: (region: string) => void;
}

export function RegionFilter({ value, onChange }: RegionFilterProps) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-text-secondary">
        {t("artist.index.filter.region")}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
        aria-label={t("artist.index.filter.region")}
      >
        <option value="">{t("artist.index.filter.regionAll")}</option>
        {REGIONS.map((r) => (
          <option key={r.code} value={r.code}>
            {r.label}
          </option>
        ))}
      </select>
    </div>
  );
}
