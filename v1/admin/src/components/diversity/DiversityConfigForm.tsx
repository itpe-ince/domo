"use client";

import { useEffect, useState } from "react";
import { DiversityConfigOut, DiversityConfigPatch } from "@/lib/api";

interface DiversityConfigFormProps {
  config: DiversityConfigOut;
  onSave: (patch: DiversityConfigPatch) => Promise<void>;
}

const DEFAULTS: Required<DiversityConfigPatch> = {
  emerging_artist_boost: 1.2,
  genre_min_diversity: 3,
  region_min_diversity: 2,
  top_k_window: 20,
};

interface ParamSliderProps {
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  unit: string;
  value: number;
  onChange: (v: number) => void;
}

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v));
}

function formatValue(v: number, step: number) {
  if (step < 1) return parseFloat(v.toFixed(2));
  return Math.round(v);
}

function ParamSlider({
  label,
  description,
  min,
  max,
  step,
  defaultValue,
  unit,
  value,
  onChange,
}: ParamSliderProps) {
  // Local input string for controlled number input (allows typing mid-edit)
  const [inputStr, setInputStr] = useState(String(value));

  // Keep input string in sync when parent value changes (e.g. reset)
  useEffect(() => {
    setInputStr(String(step < 1 ? value.toFixed(2) : Math.round(value)));
  }, [value, step]);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    setInputStr(e.target.value);
    const parsed = parseFloat(e.target.value);
    if (!isNaN(parsed)) {
      onChange(formatValue(parsed, step));
    }
  }

  function handleInputBlur() {
    const parsed = parseFloat(inputStr);
    const clamped = formatValue(
      isNaN(parsed) ? value : clamp(parsed, min, max),
      step
    );
    onChange(clamped);
    setInputStr(String(step < 1 ? clamped.toFixed(2) : clamped));
  }

  function handleRangeChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = formatValue(parseFloat(e.target.value), step);
    onChange(v);
    setInputStr(String(step < 1 ? v.toFixed(2) : v));
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <label className="text-sm font-medium text-admin-fg">{label}</label>
        <div className="flex items-center gap-1">
          <input
            type="number"
            min={min}
            max={max}
            step={step}
            value={inputStr}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            className="w-20 text-right text-sm border border-admin-border rounded px-2 py-1 bg-admin-bg text-admin-fg focus:outline-none focus:ring-1 focus:ring-admin-accent"
            aria-label={label}
          />
          <span className="text-xs text-admin-muted">{unit}</span>
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleRangeChange}
        className="w-full accent-admin-accent"
        aria-label={label}
      />
      <div className="flex justify-between text-xs text-admin-muted">
        <span>최솟값 {min}</span>
        <span className="text-admin-accent/70">권장값 {defaultValue}</span>
        <span>최댓값 {max}</span>
      </div>
      <p className="text-xs text-admin-muted">{description}</p>
    </div>
  );
}

type LocalValues = Required<DiversityConfigPatch>;

function buildLocalValues(config: DiversityConfigOut): LocalValues {
  return {
    emerging_artist_boost: config.emerging_artist_boost,
    genre_min_diversity: config.genre_min_diversity,
    region_min_diversity: config.region_min_diversity,
    top_k_window: config.top_k_window,
  };
}

const PARAM_LABELS: Record<keyof DiversityConfigPatch, string> = {
  emerging_artist_boost: "신진작가 부스팅 배수",
  genre_min_diversity: "장르 최소 다양성",
  region_min_diversity: "지역 최소 다양성",
  top_k_window: "Top-K 윈도우 크기",
};

export function DiversityConfigForm({ config, onSave }: DiversityConfigFormProps) {
  const [localValues, setLocalValues] = useState<LocalValues>(() =>
    buildLocalValues(config)
  );
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(
    null
  );

  // Sync localValues when config prop changes (after successful save)
  useEffect(() => {
    setLocalValues(buildLocalValues(config));
  }, [config]);

  function handleChange(field: keyof LocalValues) {
    return (v: number) => setLocalValues((prev) => ({ ...prev, [field]: v }));
  }

  // Compute diff between localValues and server config
  type DiffEntry = { field: keyof DiversityConfigPatch; label: string; oldVal: number; newVal: number };
  const diffs: DiffEntry[] = (
    Object.keys(DEFAULTS) as (keyof Required<DiversityConfigPatch>)[]
  ).reduce<DiffEntry[]>((acc, field) => {
    const serverConfig: { [K in keyof Required<DiversityConfigPatch>]: number } = {
      emerging_artist_boost: config.emerging_artist_boost,
      genre_min_diversity: config.genre_min_diversity,
      region_min_diversity: config.region_min_diversity,
      top_k_window: config.top_k_window,
    };
    const serverVal: number = serverConfig[field];
    const localVal: number = localValues[field];
    if (localVal !== serverVal) {
      acc.push({ field, label: PARAM_LABELS[field], oldVal: serverVal, newVal: localVal });
    }
    return acc;
  }, []);

  const hasDiff = diffs.length > 0;

  function showToast(type: "success" | "error", message: string) {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  }

  async function handleSave() {
    if (!hasDiff || saving) return;
    setSaving(true);
    const patch: DiversityConfigPatch = diffs.reduce<DiversityConfigPatch>(
      (acc, { field, newVal }) => ({ ...acc, [field]: newVal }),
      {}
    );
    try {
      await onSave(patch);
      showToast("success", "다양성 설정이 저장되었습니다. 최대 5분 이내 피드에 반영됩니다.");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "저장에 실패했습니다.";
      showToast("error", msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setLocalValues({ ...DEFAULTS });
    setSaving(true);
    try {
      await onSave({ ...DEFAULTS });
      showToast("success", "기본값으로 재설정되었습니다.");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "재설정에 실패했습니다.";
      showToast("error", msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex-1 min-w-0 bg-admin-surface border border-admin-border rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-admin-border">
        <h2 className="text-sm font-semibold text-admin-fg">파라미터 조정</h2>
      </div>

      <div className="px-6 py-5 space-y-7">
        <ParamSlider
          label="신진작가 부스팅 배수"
          description="신진작가 게시물 스코어 배수. 1.0 = 비활성"
          min={1.0}
          max={2.0}
          step={0.05}
          defaultValue={1.2}
          unit="×"
          value={localValues.emerging_artist_boost}
          onChange={handleChange("emerging_artist_boost")}
        />
        <ParamSlider
          label="장르 최소 다양성"
          description="피드 Top-K 내 최소 unique 장르 수"
          min={1}
          max={10}
          step={1}
          defaultValue={3}
          unit="종"
          value={localValues.genre_min_diversity}
          onChange={handleChange("genre_min_diversity")}
        />
        <ParamSlider
          label="지역 최소 다양성"
          description="피드 Top-K 내 최소 unique 지역 수"
          min={1}
          max={10}
          step={1}
          defaultValue={2}
          unit="종"
          value={localValues.region_min_diversity}
          onChange={handleChange("region_min_diversity")}
        />
        <ParamSlider
          label="Top-K 윈도우 크기"
          description="다양성 제약 적용 대상 피드 수"
          min={10}
          max={50}
          step={1}
          defaultValue={20}
          unit="개"
          value={localValues.top_k_window}
          onChange={handleChange("top_k_window")}
        />

        {/* 변경 사항 미리보기 */}
        {hasDiff && (
          <div className="rounded-md border border-admin-border bg-admin-bg px-4 py-3 space-y-1.5">
            <p className="text-xs font-semibold text-admin-fg mb-2">변경 사항 미리보기</p>
            {diffs.map(({ field, label, oldVal, newVal }) => (
              <div key={field} className="flex items-center gap-2 text-sm">
                <span className="text-admin-muted w-40 truncate">{label}</span>
                <span className="text-admin-muted">{typeof oldVal === "number" && oldVal % 1 !== 0 ? oldVal.toFixed(2) : oldVal}</span>
                <span className="text-admin-muted">→</span>
                <span className="text-admin-accent font-semibold">
                  {typeof newVal === "number" && newVal % 1 !== 0 ? newVal.toFixed(2) : newVal}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 버튼 */}
        <div className="flex items-center gap-3 pt-2 border-t border-admin-border">
          <button
            type="button"
            onClick={handleReset}
            disabled={saving}
            className="rounded-md border border-admin-border px-4 py-2 text-sm font-medium text-admin-fg hover:bg-admin-surface-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            기본값으로 재설정
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!hasDiff || saving}
            className="rounded-md bg-admin-accent px-4 py-2 text-sm font-medium text-white hover:bg-admin-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {saving && (
              <svg
                className="h-3.5 w-3.5 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            )}
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>

        {/* Toast */}
        {toast && (
          <div
            role="alert"
            className={`rounded-md px-4 py-2.5 text-sm font-medium ${
              toast.type === "success"
                ? "bg-green-50 text-green-800 border border-green-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {toast.message}
          </div>
        )}
      </div>
    </div>
  );
}
