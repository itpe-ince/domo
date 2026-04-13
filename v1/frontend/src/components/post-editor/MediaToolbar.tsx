"use client";

import { useRef, useState } from "react";
import { OEmbedData } from "@/lib/api";
import {
  ClockIcon,
  HashIcon,
  ImageIcon,
  LinkIcon,
  MapPinIcon,
  SmileIcon,
} from "../icons";
import { EmojiPicker } from "./EmojiPicker";
import { OEmbedInput } from "./OEmbedInput";
import { SchedulePicker } from "./SchedulePicker";

interface MediaToolbarProps {
  onImageSelect: (files: FileList) => void;
  onGifSelect: (file: File) => void;
  onEmojiInsert: (emoji: string) => void;
  onEmbedAdd: (data: OEmbedData) => void;
  onLocationClick: () => void;
  scheduledAt: string;
  onScheduleChange: (iso: string) => void;
  onTagFocus: () => void;
  disabled?: boolean;
}

export function MediaToolbar({
  onImageSelect,
  onGifSelect,
  onEmojiInsert,
  onEmbedAdd,
  onLocationClick,
  scheduledAt,
  onScheduleChange,
  onTagFocus,
  disabled = false,
}: MediaToolbarProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);
  const gifInputRef = useRef<HTMLInputElement>(null);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [embedOpen, setEmbedOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);

  const btnCls =
    "p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-primary transition-colors disabled:opacity-30";

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-t border-border">
      {/* Image/Video */}
      <button
        type="button"
        onClick={() => imageInputRef.current?.click()}
        disabled={disabled}
        className={btnCls}
        title="이미지/영상"
      >
        <ImageIcon size={20} />
      </button>
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*,video/*"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) onImageSelect(e.target.files);
          e.target.value = "";
        }}
      />

      {/* GIF */}
      <button
        type="button"
        onClick={() => gifInputRef.current?.click()}
        disabled={disabled}
        className={`${btnCls} text-xs font-bold`}
        title="GIF 업로드"
      >
        GIF
      </button>
      <input
        ref={gifInputRef}
        type="file"
        accept="image/gif"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onGifSelect(f);
          e.target.value = "";
        }}
      />

      {/* Emoji */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setEmojiOpen((v) => !v)}
          disabled={disabled}
          className={btnCls}
          title="이모지"
        >
          <SmileIcon size={20} />
        </button>
        <EmojiPicker
          open={emojiOpen}
          onClose={() => setEmojiOpen(false)}
          onSelect={onEmojiInsert}
        />
      </div>

      {/* Embed */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setEmbedOpen((v) => !v)}
          disabled={disabled}
          className={btnCls}
          title="임베드 (YouTube, Instagram, TikTok, X)"
        >
          <LinkIcon size={20} />
        </button>
        <OEmbedInput
          open={embedOpen}
          onClose={() => setEmbedOpen(false)}
          onAdd={onEmbedAdd}
        />
      </div>

      {/* Location */}
      <button
        type="button"
        onClick={onLocationClick}
        disabled={disabled}
        className={btnCls}
        title="위치"
      >
        <MapPinIcon size={20} />
      </button>

      {/* Schedule */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setScheduleOpen((v) => !v)}
          disabled={disabled}
          className={`${btnCls} ${scheduledAt ? "text-primary" : ""}`}
          title="예약 게시"
        >
          <ClockIcon size={20} />
        </button>
        <SchedulePicker
          open={scheduleOpen}
          onClose={() => setScheduleOpen(false)}
          value={scheduledAt}
          onChange={onScheduleChange}
        />
      </div>

      {/* Tags */}
      <button
        type="button"
        onClick={onTagFocus}
        disabled={disabled}
        className={btnCls}
        title="태그"
      >
        <HashIcon size={20} />
      </button>
    </div>
  );
}
