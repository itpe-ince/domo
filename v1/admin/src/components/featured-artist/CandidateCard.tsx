"use client";

import { useState } from "react";
import { FeaturedArtistCandidate, CandidateStatus } from "@/lib/api";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { RejectReasonModal } from "./RejectReasonModal";

interface CandidateCardProps {
  candidate: FeaturedArtistCandidate;
  onApprove: (id: string) => Promise<void>;
  onPublish: (id: string) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
  actionLoading: { id: string; action: "approve" | "publish" | "reject" } | null;
}

const BORDER_STYLES: Record<CandidateStatus, string> = {
  pending:   "border border-admin-border",
  approved:  "border-2 border-green-500",
  published: "border-2 border-blue-500",
  rejected:  "border border-red-500 opacity-60",
  expired:   "border border-admin-border opacity-40",
};

const BADGE_MAP: Partial<Record<CandidateStatus, { label: string; className: string }>> = {
  approved:  { label: "승인됨", className: "bg-green-500/10 text-green-400 border border-green-500/30" },
  published: { label: "발행됨", className: "bg-blue-500/10 text-blue-400 border border-blue-500/30" },
  rejected:  { label: "거부됨", className: "bg-red-500/10 text-red-400 border border-red-500/30" },
  expired:   { label: "만료됨", className: "bg-admin-border/20 text-admin-muted border border-admin-border" },
};

function Avatar({ name, url }: { name: string; url: string | null }) {
  const initial = name?.[0]?.toUpperCase() ?? "?";
  if (url) {
    return (
      <img
        src={url}
        alt={name}
        className="h-10 w-10 rounded-full object-cover flex-shrink-0"
      />
    );
  }
  return (
    <div className="h-10 w-10 rounded-full bg-admin-accent/20 flex items-center justify-center text-admin-accent text-sm font-semibold flex-shrink-0">
      {initial}
    </div>
  );
}

export function CandidateCard({
  candidate,
  onApprove,
  onPublish,
  onReject,
  actionLoading,
}: CandidateCardProps) {
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const { id, status, artist_id, artist_name, artist_avatar_url, follower_count, composite_score, reasoning } = candidate;

  const isThisCard = actionLoading?.id === id;
  const approveLoading = isThisCard && actionLoading?.action === "approve";
  const publishLoading = isThisCard && actionLoading?.action === "publish";
  const rejectLoading = isThisCard && actionLoading?.action === "reject";
  const anyLoading = !!actionLoading;

  // 버튼 활성/비활성 규칙
  const approveDisabled = anyLoading || status !== "pending";
  const publishDisabled = anyLoading || status !== "approved";
  const rejectDisabled = anyLoading || status === "published" || status === "expired";

  const badge = BADGE_MAP[status];
  const borderClass = BORDER_STYLES[status] ?? BORDER_STYLES.pending;

  async function handleRejectConfirm(reason: string) {
    await onReject(id, reason);
    setRejectModalOpen(false);
  }

  const profileUrl = `http://localhost:3700/artists/${artist_id}`;

  return (
    <>
      <div className={`bg-admin-surface rounded-xl p-5 relative ${borderClass} transition-all duration-200`}>
        {/* 상태 배지 (우상단) */}
        {badge && (
          <span className={`absolute top-3 right-3 text-[11px] font-medium px-2 py-0.5 rounded-full ${badge.className}`}>
            {badge.label}
          </span>
        )}

        {/* 아바타 + 이름 */}
        <div className="flex items-start gap-3 mb-4">
          <Avatar name={artist_name} url={artist_avatar_url} />
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-admin-fg truncate">@{artist_name}</div>
            <div className="text-[11px] text-admin-muted mt-0.5">
              팔로워 {follower_count.toLocaleString()}명
            </div>
          </div>
        </div>

        {/* 선정 점수 */}
        <div className="mb-3">
          <div className="text-[11px] text-admin-muted mb-0.5">선정 점수</div>
          <div className="text-xl font-bold text-admin-fg">{composite_score.toFixed(2)}</div>
        </div>

        {/* ScoreBreakdown */}
        <div className="mb-3">
          <ScoreBreakdown reasoning={reasoning} />
        </div>

        {/* 신진작가 배지 (sponsor_count=0) */}
        {reasoning.sponsor_count === 0 && (
          <div className="mb-3">
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
              후원자 없음
            </span>
          </div>
        )}

        {/* 거부 사유 표시 (rejected 상태) */}
        {status === "rejected" && reasoning.reject_reason && (
          <div className="mb-3 p-2 rounded-lg bg-red-500/5 border border-red-500/20">
            <div className="text-[11px] text-red-400 font-medium mb-0.5">거부 사유</div>
            <div className="text-[11px] text-admin-muted">{reasoning.reject_reason}</div>
          </div>
        )}

        {/* 프로필 링크 */}
        <a
          href={profileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[12px] text-admin-accent hover:underline mb-4"
        >
          프로필 보기 →
        </a>

        {/* 액션 버튼 */}
        <div className="flex gap-2">
          <button
            onClick={() => !approveDisabled && onApprove(id)}
            disabled={approveDisabled}
            className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {approveLoading ? "처리 중..." : "승인"}
          </button>
          <button
            onClick={() => !publishDisabled && onPublish(id)}
            disabled={publishDisabled}
            className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {publishLoading ? "처리 중..." : "발행"}
          </button>
          <button
            onClick={() => !rejectDisabled && setRejectModalOpen(true)}
            disabled={rejectDisabled}
            className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-lg bg-red-600/80 text-white hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            거부
          </button>
        </div>
      </div>

      <RejectReasonModal
        open={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        onConfirm={handleRejectConfirm}
        loading={rejectLoading}
      />
    </>
  );
}
