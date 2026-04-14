"use client";

import { HistoryEntry } from "@/lib/api";
import { StepProps } from "./types";
import { HistoryEntryRow } from "./HistoryEntryRow";

export function StepHistory({ data, onChange }: StepProps) {
  function updateExhibition(idx: number, partial: Partial<HistoryEntry>) {
    onChange({
      exhibitions: data.exhibitions.map((x, i) =>
        i === idx ? { ...x, ...partial } : x
      ),
    });
  }

  function updateAward(idx: number, partial: Partial<HistoryEntry>) {
    onChange({
      awards: data.awards.map((x, i) =>
        i === idx ? { ...x, ...partial } : x
      ),
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold mb-3">전시 이력 (선택)</h3>
        {data.exhibitions.map((ex, i) => (
          <HistoryEntryRow
            key={i}
            entry={ex}
            onChange={(partial) => updateExhibition(i, partial)}
            onRemove={() => onChange({ exhibitions: data.exhibitions.filter((_, j) => j !== i) })}
            placeholder="전시명"
          />
        ))}
        <button onClick={() => onChange({ exhibitions: [...data.exhibitions, { title: "" }] })}
          className="text-xs text-primary hover:underline">
          + 전시 추가
        </button>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-3">수상 이력 (선택)</h3>
        {data.awards.map((aw, i) => (
          <HistoryEntryRow
            key={i}
            entry={aw}
            onChange={(partial) => updateAward(i, partial)}
            onRemove={() => onChange({ awards: data.awards.filter((_, j) => j !== i) })}
            placeholder="수상명"
          />
        ))}
        <button onClick={() => onChange({ awards: [...data.awards, { title: "" }] })}
          className="text-xs text-primary hover:underline">
          + 수상 추가
        </button>
      </div>
    </div>
  );
}
