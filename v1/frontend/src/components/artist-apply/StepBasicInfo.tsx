"use client";

import { GENRES, StepProps } from "./types";

export function StepBasicInfo({ data, onChange }: StepProps) {
  function addGenre(tag: string) {
    const t = tag.trim().toLowerCase();
    if (t && !data.genre_tags.includes(t) && data.genre_tags.length < 5) {
      onChange({ genre_tags: [...data.genre_tags, t] });
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-text-secondary mb-1">소속 학교 *</label>
        <input type="text" value={data.school} onChange={(e) => onChange({ school: e.target.value })}
          placeholder="서울대학교"
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
      </div>
      <div>
        <label className="block text-sm text-text-secondary mb-1">학과 *</label>
        <input type="text" value={data.department} onChange={(e) => onChange({ department: e.target.value })}
          placeholder="서양화과"
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-text-secondary mb-1">졸업(예정) 연도 *</label>
          <input type="number" value={data.graduation_year}
            onChange={(e) => onChange({ graduation_year: Number(e.target.value) })}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
        </div>
        <div className="flex items-end pb-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={data.is_enrolled}
              onChange={(e) => onChange({ is_enrolled: e.target.checked })} className="accent-primary" />
            현재 재학 중
          </label>
        </div>
      </div>
      <div>
        <label className="block text-sm text-text-secondary mb-1">작업 장르/스타일 * (1~5개)</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {data.genre_tags.map((t) => (
            <span key={t} className="flex items-center gap-1 bg-surface rounded-full px-2.5 py-0.5 text-xs">
              {t}
              <button onClick={() => onChange({ genre_tags: data.genre_tags.filter((g) => g !== t) })}
                className="text-text-muted hover:text-danger">✕</button>
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {GENRES.filter((g) => !data.genre_tags.includes(g)).slice(0, 5).map((g) => (
            <button key={g} onClick={() => addGenre(g)} disabled={data.genre_tags.length >= 5}
              className="text-xs px-2.5 py-1 rounded-full bg-surface hover:bg-surface-hover text-text-secondary disabled:opacity-30">
              + {g}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
