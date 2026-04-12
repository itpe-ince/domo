"use client";

import { useState } from "react";
import {
  ApiClientError,
  confirmSponsorship,
  createSponsorship,
  createSubscription,
} from "@/lib/api";

const UNIT_PRICE_KRW = 1000;

type Mode = "one_time" | "recurring";

export function BluebirdModal({
  artistId,
  artistName,
  postId,
  onClose,
  onSuccess,
}: {
  artistId: string;
  artistName: string;
  postId?: string;
  onClose: () => void;
  onSuccess: (kind: Mode, bluebirdCount: number) => void;
}) {
  const [mode, setMode] = useState<Mode>("one_time");
  const [count, setCount] = useState(5);
  const [message, setMessage] = useState("");
  const [visibility, setVisibility] = useState<
    "public" | "artist_only" | "private"
  >("public");
  const [anonymous, setAnonymous] = useState(false);
  const [step, setStep] = useState<"input" | "paying" | "done">("input");
  const [error, setError] = useState<string | null>(null);

  const total = count * UNIT_PRICE_KRW;

  async function handleSubmit() {
    setError(null);
    setStep("paying");
    try {
      if (mode === "one_time") {
        const created = await createSponsorship({
          artist_id: artistId,
          post_id: postId ?? null,
          bluebird_count: count,
          is_anonymous: anonymous,
          visibility,
          message: message.trim() || undefined,
        });
        await confirmSponsorship(created.sponsorship.id);
      } else {
        await createSubscription({
          artist_id: artistId,
          monthly_bluebird: count,
        });
      }
      setStep("done");
      onSuccess(mode, count);
    } catch (e) {
      const msg =
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Unknown error";
      setError(msg);
      setStep("input");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div>
            <span className="badge-primary">🕊 Bluebird</span>
            <h2 className="text-xl font-semibold mt-2">
              @{artistName}님을 후원
            </h2>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            ✕
          </button>
        </header>

        {/* Mode toggle */}
        <div className="flex bg-background rounded-full p-1 border border-border">
          <button
            onClick={() => setMode("one_time")}
            className={`flex-1 py-2 rounded-full text-sm transition-colors ${
              mode === "one_time"
                ? "bg-primary text-background"
                : "text-text-secondary"
            }`}
          >
            일회성
          </button>
          <button
            onClick={() => setMode("recurring")}
            className={`flex-1 py-2 rounded-full text-sm transition-colors ${
              mode === "recurring"
                ? "bg-primary text-background"
                : "text-text-secondary"
            }`}
          >
            정기 (월)
          </button>
        </div>

        {/* Bluebird count */}
        <div>
          <label className="block text-sm text-text-secondary mb-2">
            블루버드 수량
          </label>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCount((c) => Math.max(1, c - 1))}
              className="btn-secondary text-sm w-10"
              disabled={step !== "input"}
            >
              −
            </button>
            <input
              type="number"
              min={1}
              max={1000}
              value={count}
              onChange={(e) =>
                setCount(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))
              }
              className="flex-1 bg-background border border-border rounded-lg px-4 py-2 text-center text-text-primary focus:border-primary outline-none"
              disabled={step !== "input"}
            />
            <button
              onClick={() => setCount((c) => Math.min(1000, c + 1))}
              className="btn-secondary text-sm w-10"
              disabled={step !== "input"}
            >
              +
            </button>
          </div>
          <div className="text-right text-primary font-semibold mt-2">
            ₩ {total.toLocaleString()}
            {mode === "recurring" && (
              <span className="text-text-muted text-sm font-normal"> / 월</span>
            )}
          </div>
        </div>

        {mode === "one_time" && (
          <>
            <div>
              <label className="block text-sm text-text-secondary mb-1">
                메시지 (선택)
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={2}
                placeholder="작가에게 짧은 응원 메시지를 남겨보세요"
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-primary outline-none resize-none"
                disabled={step !== "input"}
              />
            </div>

            <div>
              <label className="block text-sm text-text-secondary mb-2">
                공개 범위
              </label>
              <div className="space-y-2 text-sm">
                {(
                  [
                    ["public", "전체 공개"],
                    ["artist_only", "작가에게만"],
                    ["private", "비공개"],
                  ] as const
                ).map(([v, label]) => (
                  <label key={v} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="visibility"
                      checked={visibility === v}
                      onChange={() => setVisibility(v)}
                      disabled={step !== "input"}
                      className="accent-primary"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={anonymous}
                onChange={(e) => setAnonymous(e.target.checked)}
                disabled={step !== "input"}
                className="accent-primary"
              />
              <span>익명으로 후원</span>
            </label>
          </>
        )}

        {error && (
          <div className="card border-danger p-3 text-danger text-sm">
            {error}
          </div>
        )}

        {step === "done" ? (
          <div className="card border-primary p-4 text-primary text-sm text-center">
            ✓ {mode === "one_time" ? "후원이 완료되었습니다." : "정기 후원이 시작되었습니다."}
          </div>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={step === "paying"}
            className="btn-primary w-full disabled:opacity-50"
          >
            {step === "paying"
              ? "결제 중..."
              : mode === "one_time"
                ? `🕊 ${count} 블루버드 후원하기`
                : `🕊 매월 ${count} 블루버드 정기 후원`}
          </button>
        )}

        <p className="text-text-muted text-xs text-center">
          Phase 2 prototype — Mock Stripe (실제 결제 없음)
        </p>
      </div>
    </div>
  );
}
