/**
 * useExchangeRates — B'-1 multi-currency-foundation
 *
 * Fetches exchange rates from GET /v1/exchange-rates and caches in memory.
 * Also listens to "domo-currency-changed" event to re-render consumers.
 *
 * Returns:
 *   rates     — USD-based rate map (e.g. { USD: 1, KRW: 1300, EUR: 0.92, JPY: 150 })
 *   currency  — current preferred currency from localStorage
 *   loading   — true while initial fetch is in progress
 *   error     — fetch error if any
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import type { ExchangeRates } from "@/lib/format";
import { getPreferredCurrency } from "@/lib/format";
import type { SupportedCurrency } from "@/components/CurrencySwitcher";
import { CURRENCY_CHANGED_EVENT } from "@/components/CurrencySwitcher";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1";

// Module-level cache so rates are shared across instances
let _cachedRates: ExchangeRates | null = null;
let _fetchedAt: number | null = null;
const RATES_TTL_MS = 5 * 60 * 1000; // 5 minutes (matches server Redis TTL)

export function useExchangeRates() {
  const [rates, setRates] = useState<ExchangeRates | null>(_cachedRates);
  const [currency, setCurrency] = useState<SupportedCurrency>("USD");
  const [loading, setLoading] = useState(!_cachedRates);
  const [error, setError] = useState<Error | null>(null);

  const fetchRates = useCallback(async () => {
    // Use cached rates if fresh
    if (_cachedRates && _fetchedAt && Date.now() - _fetchedAt < RATES_TTL_MS) {
      setRates(_cachedRates);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/exchange-rates?base=USD`);
      if (!res.ok) throw new Error(`exchange-rates fetch failed: ${res.status}`);
      const json = await res.json();
      const fetched: ExchangeRates = json.data?.rates ?? {};
      _cachedRates = fetched;
      _fetchedAt = Date.now();
      setRates(fetched);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      // Fallback rates so UI doesn't break
      if (!_cachedRates) {
        _cachedRates = { USD: 1, KRW: 1300, EUR: 0.92, JPY: 150 };
        setRates(_cachedRates);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setCurrency(getPreferredCurrency());
    fetchRates();

    function onCurrencyChange(e: Event) {
      const evt = e as CustomEvent<SupportedCurrency>;
      setCurrency(evt.detail);
    }
    window.addEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
    return () => window.removeEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
  }, [fetchRates]);

  return { rates, currency, loading, error };
}
