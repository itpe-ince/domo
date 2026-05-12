"use client";

import { useState } from "react";
import { StripeConnectStatus } from "@/lib/api";
import { useStripeConnectStatus } from "@/lib/hooks/usePayouts";

interface StatusDetailModalProps {
  status: StripeConnectStatus;
  onClose: () => void;
}

function StatusDetailModal({ status, onClose }: StatusDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-admin-surface border border-admin-border rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-admin-fg font-semibold text-base">
            Stripe Connect 상태 — {status.artist_name}
          </h2>
          <button
            onClick={onClose}
            className="text-admin-muted hover:text-admin-fg transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        {status.mock_mode && (
          <div className="bg-amber-50 border border-amber-200 text-amber-700 text-[11px] rounded-lg px-3 py-2 mb-4">
            Stripe 실제 연동 전 테스트 데이터입니다.
          </div>
        )}

        <div className="space-y-3">
          <Row label="Artist ID" value={status.artist_id} />
          <Row label="Customer ID" value={status.stripe_customer_id ?? "—"} />
          <Row
            label="Connect Account ID"
            value={status.stripe_connect_account_id ?? "—"}
          />
          <Row
            label="입금 가능"
            value={
              <span
                className={`text-[12px] font-medium ${status.charges_enabled ? "text-green-600" : "text-red-500"}`}
              >
                {status.charges_enabled ? "✓ 가능" : "✗ 불가"}
              </span>
            }
          />
          <Row
            label="출금 가능"
            value={
              <span
                className={`text-[12px] font-medium ${status.payouts_enabled ? "text-green-600" : "text-red-500"}`}
              >
                {status.payouts_enabled ? "✓ 가능" : "✗ 불가"}
              </span>
            }
          />
          {status.requirements.currently_due.length > 0 && (
            <Row
              label="즉시 필요 서류"
              value={
                <ul className="text-[12px] text-admin-danger space-y-0.5">
                  {status.requirements.currently_due.map((r) => (
                    <li key={r}>• {r}</li>
                  ))}
                </ul>
              }
            />
          )}
          {status.requirements.eventually_due.length > 0 && (
            <Row
              label="추후 필요 서류"
              value={
                <ul className="text-[12px] text-admin-muted space-y-0.5">
                  {status.requirements.eventually_due.map((r) => (
                    <li key={r}>• {r}</li>
                  ))}
                </ul>
              }
            />
          )}
          {status.requirements.disabled_reason && (
            <Row
              label="비활성 사유"
              value={
                <span className="text-admin-danger text-[12px]">
                  {status.requirements.disabled_reason}
                </span>
              }
            />
          )}
          {!status.requirements.currently_due.length &&
            !status.requirements.eventually_due.length && (
              <Row label="요구사항" value="없음" />
            )}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-admin-muted border border-admin-border rounded-lg hover:bg-admin-surface-2 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-4">
      <span className="text-[11px] font-semibold text-admin-muted uppercase tracking-wider w-32 flex-shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-[13px] text-admin-fg flex-1">{value}</span>
    </div>
  );
}

export function StripeConnectStatusTab() {
  const { statusMap, loading, error, fetchStatus } = useStripeConnectStatus();
  const [artistIdInput, setArtistIdInput] = useState("");
  const [detailArtistId, setDetailArtistId] = useState<string | null>(null);

  async function handleSearch() {
    const id = artistIdInput.trim();
    if (!id) return;
    const result = await fetchStatus(id);
    if (result) {
      setDetailArtistId(id);
    }
  }

  const detailStatus = detailArtistId ? statusMap[detailArtistId] : null;

  return (
    <div>
      {detailStatus && detailArtistId && (
        <StatusDetailModal
          status={detailStatus}
          onClose={() => setDetailArtistId(null)}
        />
      )}

      {/* 검색 영역 */}
      <div className="flex items-center gap-3 mb-6">
        <input
          type="text"
          value={artistIdInput}
          onChange={(e) => setArtistIdInput(e.target.value)}
          placeholder="Artist ID (UUID) 입력..."
          onKeyDown={(e) => e.key === "Enter" && void handleSearch()}
          className="bg-admin-surface border border-admin-border rounded-lg px-3 py-1.5 text-sm text-admin-fg placeholder-admin-muted focus:outline-none focus:border-admin-accent flex-1 max-w-xs"
        />
        <button
          onClick={() => void handleSearch()}
          disabled={!!loading || !artistIdInput.trim()}
          className="text-[11px] px-3 py-1.5 bg-admin-accent text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? "조회 중..." : "상태 조회"}
        </button>
      </div>

      {error && (
        <div className="text-admin-danger text-sm bg-admin-danger/10 border border-admin-danger/20 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {/* 조회 결과 목록 */}
      {Object.keys(statusMap).length === 0 ? (
        <div className="text-admin-muted text-sm py-12 text-center border border-admin-border rounded-xl">
          Artist ID를 입력하고 상태를 조회하세요.
        </div>
      ) : (
        <div className="border border-admin-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-admin-border bg-admin-surface-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  작가명
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  Customer ID
                </th>
                <th className="px-4 py-2.5 text-center text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  입금
                </th>
                <th className="px-4 py-2.5 text-center text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  출금
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  상태
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(statusMap).map(([id, status]) => (
                <tr
                  key={id}
                  onClick={() => setDetailArtistId(id)}
                  className="border-b border-admin-border last:border-0 hover:bg-admin-surface-2/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 text-admin-fg font-medium text-[13px]">
                    {status.artist_name}
                  </td>
                  <td className="px-4 py-3 text-admin-muted text-[11px] font-mono">
                    {status.stripe_customer_id ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {status.charges_enabled ? (
                      <span className="text-green-600 text-sm">✓</span>
                    ) : (
                      <span className="text-red-500 text-sm">✗</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {status.payouts_enabled ? (
                      <span className="text-green-600 text-sm">✓</span>
                    ) : (
                      <span className="text-red-500 text-sm">✗</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[11px]">
                    {status.mock_mode ? (
                      <span className="text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
                        Mock 모드
                      </span>
                    ) : status.requirements.currently_due.length > 0 ? (
                      <span className="text-red-600 bg-red-50 px-2 py-0.5 rounded">
                        서류 필요 ({status.requirements.currently_due.length}건)
                      </span>
                    ) : (
                      <span className="text-green-600 bg-green-50 px-2 py-0.5 rounded">
                        정상
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
