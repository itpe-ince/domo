"use client";

import { useEffect, useRef, useState } from "react";
import { fetchTagSuggestions } from "@/lib/api";

interface TagAutocompleteProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
}

export function TagAutocomplete({ tags, onTagsChange }: TagAutocompleteProps) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [focusIdx, setFocusIdx] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!input.trim() || input.length < 1) {
      setSuggestions([]);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const result = await fetchTagSuggestions(input.trim());
        setSuggestions(result.filter((t) => !tags.includes(t)));
        setShowSuggestions(true);
        setFocusIdx(-1);
      } catch {
        setSuggestions([]);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [input, tags]);

  function addTag(tag: string) {
    const t = tag.trim().toLowerCase();
    if (!t || tags.includes(t)) return;
    onTagsChange([...tags, t]);
    setInput("");
    setSuggestions([]);
    setShowSuggestions(false);
    inputRef.current?.focus();
  }

  function removeTag(tag: string) {
    onTagsChange(tags.filter((t) => t !== tag));
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (focusIdx >= 0 && focusIdx < suggestions.length) {
        addTag(suggestions[focusIdx]);
      } else if (input.trim()) {
        addTag(input);
      }
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    } else if (e.key === "ArrowDown" && showSuggestions) {
      e.preventDefault();
      setFocusIdx((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp" && showSuggestions) {
      e.preventDefault();
      setFocusIdx((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1.5 items-center bg-background border border-border rounded-lg px-3 py-2 focus-within:border-primary">
        {tags.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 bg-surface rounded-full px-2.5 py-0.5 text-xs text-text-primary"
          >
            #{tag}
            <button
              onClick={() => removeTag(tag)}
              className="text-text-muted hover:text-danger"
            >
              ✕
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value.replace(",", ""))}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder={tags.length === 0 ? "태그 입력 (Enter로 추가)" : ""}
          className="flex-1 min-w-[100px] bg-transparent outline-none text-sm text-text-primary placeholder:text-text-muted"
        />
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute top-full mt-1 left-0 right-0 card p-1 z-40 shadow-xl max-h-40 overflow-y-auto">
          {suggestions.map((tag, idx) => (
            <button
              key={tag}
              onMouseDown={(e) => {
                e.preventDefault();
                addTag(tag);
              }}
              className={`w-full text-left px-3 py-1.5 rounded text-sm ${
                focusIdx === idx
                  ? "bg-surface-hover text-primary"
                  : "text-text-primary hover:bg-surface-hover"
              }`}
            >
              #{tag}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
