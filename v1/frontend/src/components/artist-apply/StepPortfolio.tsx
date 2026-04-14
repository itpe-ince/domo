"use client";

import { useState } from "react";
import { uploadMediaFile } from "@/lib/api";
import { StepProps } from "./types";

export function StepPortfolio({ data, onChange }: StepProps) {
  const [proofUploading, setProofUploading] = useState(false);

  async function handleProofUpload(file: File) {
    setProofUploading(true);
    try {
      const res = await uploadMediaFile(file, false);
      onChange({ enrollment_proof_url: res.url });
    } catch { /* ignore */ }
    finally { setProofUploading(false); }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-text-secondary mb-1">자기소개 * (200자 이내)</label>
        <textarea value={data.statement}
          onChange={(e) => { if (e.target.value.length <= 200) onChange({ statement: e.target.value }); }}
          rows={4} placeholder="저는 리마에서 활동하는 유화 작가입니다..."
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none resize-none" />
        <div className="text-xs text-text-muted text-right">{data.statement.length}/200</div>
      </div>
      <div>
        <label className="block text-sm text-text-secondary mb-1">재학/졸업 증빙 *</label>
        {data.enrollment_proof_url ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-primary">✓ 업로드 완료</span>
            <button onClick={() => onChange({ enrollment_proof_url: "" })}
              className="text-xs text-danger hover:underline">삭제</button>
          </div>
        ) : (
          <label className="inline-flex items-center gap-2 px-4 py-2 bg-surface rounded-lg cursor-pointer hover:bg-surface-hover text-sm">
            {proofUploading ? "업로드 중..." : "📎 파일 선택 (PDF/JPG/PNG)"}
            <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleProofUpload(f); e.target.value = ""; }} />
          </label>
        )}
      </div>
      <div>
        <label className="block text-sm text-text-secondary mb-1">포트폴리오 URL (줄바꿈 구분)</label>
        <textarea value={data.portfolio_urls} onChange={(e) => onChange({ portfolio_urls: e.target.value })}
          rows={3} placeholder={"https://portfolio1.com\nhttps://portfolio2.com"}
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none resize-none" />
      </div>
      <div>
        <label className="block text-sm text-text-secondary mb-1">소개 영상 URL (선택)</label>
        <input type="url" value={data.intro_video_url}
          onChange={(e) => onChange({ intro_video_url: e.target.value })}
          placeholder="https://youtube.com/watch?v=..."
          className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none" />
      </div>
    </div>
  );
}
