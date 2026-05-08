"use client";

/**
 * PreferencesCard — Phase 10 통합 환경설정 카드
 *
 * 사이드바 하단의 통화 / 언어 / 단순 모드 컨트롤을 카드 하나로 통합.
 *
 * Expanded (xl+): 3행 레이아웃 (아이콘 + 라벨 + 현재값 + chevron/toggle)
 * Collapsed (xl-): 아이콘 3개 가로 배치
 *
 * Popover 위치:
 *   - Expanded: 카드 우측 상단 (right-0 bottom-full mb-1)
 *   - Collapsed: 카드 우측 상단 (right-0 bottom-full mb-2)
 *
 * 한 번에 하나의 popover만 열림.
 * ESC 키 / 외부 클릭으로 닫힘.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useI18n, LOCALE_LABELS, Locale } from "@/i18n";
import { useCognitiveSimpleMode } from "@/lib/hooks/useCognitiveSimpleMode";
import {
  SUPPORTED_CURRENCIES,
  SupportedCurrency,
  CURRENCY_SYMBOLS,
  CURRENCY_CHANGED_EVENT,
  getStoredCurrency,
  setStoredCurrency,
} from "./CurrencySwitcher";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface PreferencesCardProps {
  /** 사이드바 펼친 모드 여부 (xl+) — 컴포넌트 내부 미디어 쿼리로도 처리 */
  expanded?: boolean;
  /** 로그인 상태 (currency 서버 동기화 트리거) */
  isAuthenticated?: boolean;
  className?: string;
}

type PopoverTarget = "currency" | "locale" | null;

/* ------------------------------------------------------------------ */
/* Chevron icon                                                         */
/* ------------------------------------------------------------------ */

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-3.5 h-3.5 text-text-muted transition-transform ${open ? "rotate-180" : ""}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Compact inline toggle (no label, for the row's right side)          */
/* ------------------------------------------------------------------ */

function InlineToggle({
  id,
  checked,
  onChange,
  ariaLabel,
}: {
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  ariaLabel: string;
}) {
  return (
    <button
      id={id}
      role="switch"
      type="button"
      aria-checked={checked}
      aria-label={ariaLabel}
      onClick={() => onChange(!checked)}
      className={[
        "relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        checked ? "bg-primary border-primary" : "bg-surface border-border",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "pointer-events-none inline-block h-3.5 w-3.5 rounded-full bg-background shadow-sm",
          "transform transition-transform duration-150 mt-px",
          checked ? "translate-x-3.5" : "translate-x-0.5",
        ].join(" ")}
      />
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                       */
/* ------------------------------------------------------------------ */

export function PreferencesCard({
  isAuthenticated = false,
  className = "",
}: PreferencesCardProps) {
  const { t, locale, setLocale } = useI18n();
  const { enabled: simpleMode, toggle: toggleSimpleMode } = useCognitiveSimpleMode();

  const [currency, setCurrency] = useState<SupportedCurrency>("USD");
  const [openPopover, setOpenPopover] = useState<PopoverTarget>(null);

  const cardRef = useRef<HTMLDivElement>(null);

  /* Sync currency from localStorage */
  useEffect(() => {
    setCurrency(getStoredCurrency());

    function onCurrencyChange(e: Event) {
      const evt = e as CustomEvent<SupportedCurrency>;
      setCurrency(evt.detail);
    }
    window.addEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
    return () => window.removeEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
  }, []);

  /* ESC key closes popover */
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenPopover(null);
    }
    if (openPopover) {
      document.addEventListener("keydown", onKeyDown);
      return () => document.removeEventListener("keydown", onKeyDown);
    }
  }, [openPopover]);

  /* Outside click closes popover */
  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        setOpenPopover(null);
      }
    }
    if (openPopover) {
      document.addEventListener("pointerdown", onPointerDown);
      return () => document.removeEventListener("pointerdown", onPointerDown);
    }
  }, [openPopover]);

  const togglePopover = useCallback((target: PopoverTarget) => {
    setOpenPopover((prev) => (prev === target ? null : target));
  }, []);

  async function handleCurrencySelect(c: SupportedCurrency) {
    setStoredCurrency(c);
    setCurrency(c);
    setOpenPopover(null);

    if (isAuthenticated) {
      try {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("domo_access_token")
            : null;
        if (token) {
          await fetch(
            `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1"}/me/preferences/currency`,
            {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ currency: c }),
            }
          );
        }
      } catch {
        // Non-fatal — localStorage is source of truth
      }
    }
  }

  function handleLocaleSelect(l: Locale) {
    setLocale(l);
    setOpenPopover(null);
  }

  /* ---------------------------------------------------------------- */
  /* Currency popover list                                             */
  /* ---------------------------------------------------------------- */

  function CurrencyPopover() {
    return (
      <ul
        role="listbox"
        aria-label={t("currency.switcher.label")}
        className="card p-1 shadow-lg rounded-lg z-40 min-w-[140px]"
      >
        {SUPPORTED_CURRENCIES.map((c) => (
          <li key={c} role="option" aria-selected={c === currency}>
            <button
              type="button"
              onClick={() => handleCurrencySelect(c)}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                c === currency
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-text-secondary hover:bg-surface-hover"
              }`}
            >
              <span className="font-mono w-4 text-center">{CURRENCY_SYMBOLS[c]}</span>
              <span className="font-medium">{c}</span>
              <span className="text-text-muted ml-auto">{t(`currency.label.${c}`)}</span>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  /* ---------------------------------------------------------------- */
  /* Locale popover list                                               */
  /* ---------------------------------------------------------------- */

  function LocalePopover() {
    return (
      <ul
        role="listbox"
        aria-label={t("preferences.locale.label")}
        className="card p-1 shadow-lg rounded-lg z-40 min-w-[140px]"
      >
        {(Object.entries(LOCALE_LABELS) as [Locale, { flag: string; name: string }][]).map(
          ([code, { flag, name }]) => (
            <li key={code} role="option" aria-selected={code === locale}>
              <button
                type="button"
                onClick={() => handleLocaleSelect(code)}
                className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                  code === locale
                    ? "bg-primary/15 text-primary font-medium"
                    : "text-text-secondary hover:bg-surface-hover"
                }`}
              >
                <span className="text-sm">{flag}</span>
                <span>{name}</span>
              </button>
            </li>
          )
        )}
      </ul>
    );
  }

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div ref={cardRef} className={`relative ${className}`}>
      {/* ============================================================ */}
      {/* EXPANDED MODE (xl+): 3-row card                             */}
      {/* ============================================================ */}
      <div className="hidden xl:block bg-surface border border-border rounded-xl overflow-hidden divide-y divide-border/50">

        {/* Row 1: Currency */}
        <div className="relative">
          <button
            type="button"
            onClick={() => togglePopover("currency")}
            aria-label={t("currency.switcher.label")}
            aria-expanded={openPopover === "currency"}
            aria-haspopup="listbox"
            className="w-full flex items-center gap-2 px-3 py-2 hover:bg-surface-hover transition-colors"
          >
            <span className="text-base leading-none" aria-hidden="true">💲</span>
            <span className="text-xs text-text-secondary flex-1 text-left">
              {t("preferences.currency.label")}
            </span>
            <span className="text-xs font-mono font-semibold text-primary">
              {CURRENCY_SYMBOLS[currency]}
              <span className="ml-1 font-sans font-normal text-text-muted">{currency}</span>
            </span>
            <ChevronDown open={openPopover === "currency"} />
          </button>

          {/* Currency popover — opens upward, right-aligned */}
          {openPopover === "currency" && (
            <div className="absolute right-0 bottom-full mb-1 z-40">
              <CurrencyPopover />
            </div>
          )}
        </div>

        {/* Row 2: Locale */}
        <div className="relative">
          <button
            type="button"
            onClick={() => togglePopover("locale")}
            aria-label={t("preferences.locale.label")}
            aria-expanded={openPopover === "locale"}
            aria-haspopup="listbox"
            className="w-full flex items-center gap-2 px-3 py-2 hover:bg-surface-hover transition-colors"
          >
            <span className="text-base leading-none" aria-hidden="true">🌐</span>
            <span className="text-xs text-text-secondary flex-1 text-left">
              {t("preferences.locale.label")}
            </span>
            <span className="text-xs text-text-muted">
              {LOCALE_LABELS[locale].flag} {LOCALE_LABELS[locale].name}
            </span>
            <ChevronDown open={openPopover === "locale"} />
          </button>

          {/* Locale popover — opens upward, right-aligned */}
          {openPopover === "locale" && (
            <div className="absolute right-0 bottom-full mb-1 z-40">
              <LocalePopover />
            </div>
          )}
        </div>

        {/* Row 3: Simple mode toggle */}
        <div className="flex items-center gap-2 px-3 py-2">
          <span className="text-base leading-none" aria-hidden="true">👁️</span>
          <span className="text-xs text-text-secondary flex-1">
            {t("preferences.simpleMode.label")}
          </span>
          <InlineToggle
            id="preferences-simple-mode-expanded"
            checked={simpleMode}
            onChange={toggleSimpleMode}
            ariaLabel={t("preferences.simpleMode.label")}
          />
        </div>
      </div>

      {/* ============================================================ */}
      {/* COLLAPSED MODE (xl-): 3 icon buttons in a row               */}
      {/* ============================================================ */}
      <div className="xl:hidden flex items-center justify-center gap-1 bg-surface border border-border rounded-xl px-1 py-1">

        {/* Currency icon button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => togglePopover("currency")}
            aria-label={t("currency.switcher.label")}
            aria-expanded={openPopover === "currency"}
            aria-haspopup="listbox"
            className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-surface-hover transition-colors"
          >
            <span
              className="font-mono font-bold text-sm"
              style={{ color: openPopover === "currency" ? undefined : undefined }}
            >
              {CURRENCY_SYMBOLS[currency]}
            </span>
          </button>

          {/* Currency popover — opens upward */}
          {openPopover === "currency" && (
            <div className="absolute bottom-full mb-2 left-0 z-40">
              <CurrencyPopover />
            </div>
          )}
        </div>

        {/* Locale icon button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => togglePopover("locale")}
            aria-label={t("preferences.locale.label")}
            aria-expanded={openPopover === "locale"}
            aria-haspopup="listbox"
            className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-surface-hover transition-colors"
            title={LOCALE_LABELS[locale].name}
          >
            <span className="text-base leading-none">{LOCALE_LABELS[locale].flag}</span>
          </button>

          {/* Locale popover — opens upward */}
          {openPopover === "locale" && (
            <div className="absolute bottom-full mb-2 left-0 z-40">
              <LocalePopover />
            </div>
          )}
        </div>

        {/* Simple mode toggle icon button */}
        <button
          type="button"
          role="switch"
          aria-checked={simpleMode}
          aria-label={t("preferences.simpleMode.label")}
          onClick={() => toggleSimpleMode(!simpleMode)}
          className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
            simpleMode
              ? "bg-primary/15 text-primary"
              : "hover:bg-surface-hover text-text-muted"
          }`}
        >
          <span className="text-base leading-none">👁️</span>
        </button>
      </div>
    </div>
  );
}
