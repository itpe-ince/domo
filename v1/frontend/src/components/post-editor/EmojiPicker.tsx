"use client";

import { useEffect, useRef, useState } from "react";

const EMOJI_LIST = [
  "😊", "😍", "🥰", "😎", "🤩", "😂", "🥹", "😭",
  "🎨", "🖼️", "🖌️", "✏️", "📸", "🎭", "🌈", "✨",
  "❤️", "🔥", "👏", "💯", "🙌", "🕊️", "💎", "⭐",
  "📍", "🏛️", "🎪", "🌸", "🌅", "🎶",
];

interface EmojiPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (emoji: string) => void;
}

export function EmojiPicker({ open, onClose, onSelect }: EmojiPickerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={ref}
      className="absolute bottom-full mb-2 left-0 card p-3 z-40 shadow-xl w-72"
    >
      <div className="grid grid-cols-6 gap-1">
        {EMOJI_LIST.map((emoji) => (
          <button
            key={emoji}
            onClick={() => {
              onSelect(emoji);
              onClose();
            }}
            className="w-10 h-10 flex items-center justify-center text-xl rounded-lg hover:bg-surface-hover transition-colors"
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  );
}
