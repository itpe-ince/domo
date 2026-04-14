"use client";

import { RepresentativeWork } from "@/lib/api";
import { StepProps } from "./types";
import { WorkCard } from "./WorkCard";

export function StepWorks({ data, onChange }: StepProps) {
  const works = data.representative_works;

  function updateWork(idx: number, partial: Partial<RepresentativeWork>) {
    onChange({
      representative_works: works.map((w, i) =>
        i === idx ? { ...w, ...partial } : w
      ),
    });
  }

  function addWork() {
    if (works.length >= 6) return;
    onChange({
      representative_works: [
        ...works,
        { title: "", image_url: "", description: "", dimensions: "", medium: "", year: 2026 },
      ],
    });
  }

  function removeWork(idx: number) {
    onChange({ representative_works: works.filter((_, i) => i !== idx) });
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-muted">대표 작품 3~6개를 등록해주세요.</p>
      {works.map((w, i) => (
        <WorkCard
          key={i}
          index={i}
          work={w}
          onChange={(partial) => updateWork(i, partial)}
          onRemove={i >= 3 ? () => removeWork(i) : undefined}
        />
      ))}
      {works.length < 6 && (
        <button onClick={addWork}
          className="w-full py-3 border border-dashed border-border rounded-lg text-sm text-text-muted hover:border-primary hover:text-primary">
          + 작품 추가 (최대 6개)
        </button>
      )}
    </div>
  );
}
