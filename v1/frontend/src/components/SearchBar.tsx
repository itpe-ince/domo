"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { useI18n } from "@/i18n";
import { useRecentSearches } from "@/lib/useRecentSearches";
import { SearchIcon } from "./icons";

interface SearchBarProps {
  compact?: boolean;
  className?: string;
}

export function SearchBar({ compact = false, className = "" }: SearchBarProps) {
  const { t } = useI18n();
  const router = useRouter();
  const { items: recent, add, remove, clear } = useRecentSearches();
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState(-1);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) {
      setFocusIdx(-1);
      return;
    }
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  function submit(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    add(trimmed);
    setOpen(false);
    setValue("");
    router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!open || recent.length === 0) {
      if (e.key === "Enter") {
        e.preventDefault();
        submit(value);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusIdx((i) => (i + 1) % recent.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusIdx((i) => (i <= 0 ? recent.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (focusIdx >= 0 && focusIdx < recent.length) {
        submit(recent[focusIdx]);
      } else {
        submit(value);
      }
    }
  }

  if (compact) {
    return (
      <button
        onClick={() => router.push("/search")}
        className={`flex items-center justify-center p-3 rounded-full hover:bg-surface-hover transition-colors text-text-secondary ${className}`}
        aria-label={t("common.search")}
      >
        <SearchIcon />
      </button>
    );
  }

  return (
    <div ref={ref} className={`relative ${className}`}>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
          <SearchIcon size={18} />
        </span>
        <input
          ref={inputRef}
          type="text"
          role="searchbox"
          aria-label={t("common.search")}
          aria-expanded={open && recent.length > 0}
          aria-controls={listId}
          aria-activedescendant={
            focusIdx >= 0 ? `${listId}-${focusIdx}` : undefined
          }
          placeholder={t("common.search")}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setFocusIdx(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          className="w-full bg-surface rounded-full pl-10 pr-10 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {value && (
          <button
            onClick={() => {
              setValue("");
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs"
            aria-label={t("common.delete")}
          >
            ✕
          </button>
        )}
      </div>

      {open && recent.length > 0 && (
        <div
          id={listId}
          role="listbox"
          aria-label={t("search.recentSearches")}
          className="absolute top-full mt-1 left-0 right-0 card p-2 z-40 shadow-xl"
        >
          <div className="flex items-center justify-between px-2 py-1 mb-1">
            <span className="text-xs text-text-muted font-semibold">
              최근 검색
            </span>
            <button
              onClick={() => {
                clear();
                setOpen(false);
              }}
              className="text-xs text-text-muted hover:text-primary"
            >
              전체 삭제
            </button>
          </div>
          {recent.map((q, idx) => (
            <div
              key={q}
              id={`${listId}-${idx}`}
              role="option"
              aria-selected={focusIdx === idx}
              className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm ${
                focusIdx === idx
                  ? "bg-surface-hover"
                  : "hover:bg-surface-hover"
              }`}
              onClick={() => submit(q)}
            >
              <span className="truncate text-text-primary">{q}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  remove(q);
                }}
                className="text-text-muted hover:text-text-primary text-xs ml-2 flex-shrink-0"
                aria-label={`"${q}" 삭제`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
