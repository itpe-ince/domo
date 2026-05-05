"use client";

/**
 * PayoutRequestModal — optional payout request UI (B-2 optional scope).
 *
 * Renders a modal where artists can request a payout.
 * Calls POST /v1/me/patronage/payout-request (stub in Phase 5;
 * full settlement integration is carry-over to Phase 6).
 */

import React, { useState } from "react";
import { ApiClientError, requestPayout } from "@/lib/api";

interface PayoutRequestModalProps {
  open: boolean;
  onClose: () => void;
  availableBalanceCents: number;
  labels?: {
    title: string;
    balance: string;
    amountLabel: string;
    methodLabel: string;
    methodBank: string;
    methodStripe: string;
    submit: string;
    submitting: string;
    success: string;
    cancel: string;
    placeholder: string;
  };
}

export function PayoutRequestModal({
  open,
  onClose,
  availableBalanceCents,
  labels,
}: PayoutRequestModalProps) {
  const L = {
    title: labels?.title ?? "Request Payout",
    balance: labels?.balance ?? "Available balance",
    amountLabel: labels?.amountLabel ?? "Amount (USD)",
    methodLabel: labels?.methodLabel ?? "Method",
    methodBank: labels?.methodBank ?? "Bank transfer",
    methodStripe: labels?.methodStripe ?? "Stripe",
    submit: labels?.submit ?? "Submit request",
    submitting: labels?.submitting ?? "Submitting...",
    success: labels?.success ?? "Payout request submitted!",
    cancel: labels?.cancel ?? "Cancel",
    placeholder: labels?.placeholder ?? "Amount in USD cents",
  };

  const [amountCents, setAmountCents] = useState("");
  const [method, setMethod] = useState<"bank_transfer" | "stripe">("stripe");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const maxCents = availableBalanceCents;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cents = parseInt(amountCents, 10);
    if (!cents || cents <= 0 || cents > maxCents) {
      setError("Invalid amount");
      return;
    }
    setStatus("submitting");
    setError(null);
    try {
      await requestPayout({ amount_cents: cents, currency: "USD", method });
      setStatus("success");
    } catch (err) {
      const msg =
        err instanceof ApiClientError ? err.message : "Failed to submit payout request";
      setError(msg);
      setStatus("error");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-label={L.title}
    >
      <div className="card p-6 w-full max-w-sm mx-4 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-text-primary">{L.title}</h2>

        <p className="text-sm text-text-muted">
          {L.balance}:{" "}
          <span className="font-semibold text-text-primary tabular-nums">
            ${(maxCents / 100).toFixed(2)}
          </span>
        </p>

        {status === "success" ? (
          <div className="py-6 text-center">
            <p className="text-green-500 font-medium">{L.success}</p>
            <button
              onClick={onClose}
              className="mt-4 text-sm text-primary hover:underline"
            >
              {L.cancel}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-text-muted">{L.amountLabel}</label>
              <input
                type="number"
                min={1}
                max={maxCents}
                value={amountCents}
                onChange={(e) => setAmountCents(e.target.value)}
                placeholder={L.placeholder}
                className="border border-border rounded-lg px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:border-primary"
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-text-muted">{L.methodLabel}</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as "bank_transfer" | "stripe")}
                className="border border-border rounded-lg px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:border-primary"
              >
                <option value="stripe">{L.methodStripe}</option>
                <option value="bank_transfer">{L.methodBank}</option>
              </select>
            </div>

            {error && <p className="text-xs text-red-500">{error}</p>}

            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-text-secondary hover:bg-surface-hover rounded-lg transition-colors"
              >
                {L.cancel}
              </button>
              <button
                type="submit"
                disabled={status === "submitting"}
                className="px-4 py-2 text-sm bg-primary text-background rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {status === "submitting" ? L.submitting : L.submit}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
