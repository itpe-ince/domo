"use client";

/**
 * usePostFormState — editor-responsive-redesign PDCA (#3, Step 1).
 *
 * Groups the 18 form-field useState calls from posts/new/page.tsx into a
 * single hook. UI-only state (uploading, submitting, error, applicationStatus)
 * stays at page level so it doesn't leak into draft autosave or wizard steps.
 *
 * Returns:
 *   - formState: snapshot object matching DraftState (same shape useDraftAutosave consumes)
 *   - setters: 18 stable setStates from React, named identically to the
 *     previous local setters so call sites need no rename
 *   - resetFromDraft(d): apply a DraftState payload across all 18 fields,
 *     replacing the previous 18-line manual handleRestore body
 *
 * Pattern source: design §4.2.
 */
import { useState, type Dispatch, type SetStateAction } from "react";

import type { DraftState } from "@/lib/hooks/useDraftAutosave";
import type { EarlyAccessDuration, EarlyAccessTier, Visibility } from "@/lib/api";

// Each setter is the full React Dispatch<SetStateAction<T>> so callers can
// pass either a value or a `(prev) => next` updater — same contract as the
// previous local useState setters.
export interface PostFormSetters {
  setType: Dispatch<SetStateAction<DraftState["type"]>>;
  setTitle: Dispatch<SetStateAction<string>>;
  setContent: Dispatch<SetStateAction<string>>;
  setGenre: Dispatch<SetStateAction<string>>;
  setTags: Dispatch<SetStateAction<string[]>>;
  setMedia: Dispatch<SetStateAction<DraftState["media"]>>;
  setEmbeds: Dispatch<SetStateAction<DraftState["embeds"]>>;
  setIsMakingVideo: Dispatch<SetStateAction<boolean>>;
  setScheduledAt: Dispatch<SetStateAction<string>>;
  setLocationName: Dispatch<SetStateAction<string>>;
  setLocationLat: Dispatch<SetStateAction<number | null>>;
  setLocationLng: Dispatch<SetStateAction<number | null>>;
  setIsAuction: Dispatch<SetStateAction<boolean>>;
  setIsBuyNow: Dispatch<SetStateAction<boolean>>;
  setBuyNowPrice: Dispatch<SetStateAction<number | "">>;
  setDimensions: Dispatch<SetStateAction<string>>;
  setMedium: Dispatch<SetStateAction<string>>;
  setYear: Dispatch<SetStateAction<number | "">>;
  // publish-controls PDCA #8
  setVisibility: Dispatch<SetStateAction<Visibility>>;
  setCommentsEnabled: Dispatch<SetStateAction<boolean>>;
  setSeriesIds: Dispatch<SetStateAction<string[]>>;
  // artist-tier-release PDCA #10
  setEarlyAccessDuration: Dispatch<SetStateAction<EarlyAccessDuration | null>>;
  setEarlyAccessTier: Dispatch<SetStateAction<EarlyAccessTier | null>>;
}

export interface UsePostFormStateOptions {
  initialType: DraftState["type"];
}

export interface UsePostFormStateReturn {
  formState: DraftState;
  setters: PostFormSetters;
  resetFromDraft: (d: DraftState) => void;
}

export function usePostFormState({
  initialType,
}: UsePostFormStateOptions): UsePostFormStateReturn {
  const [type, setType] = useState<DraftState["type"]>(initialType);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [genre, setGenre] = useState("painting");
  const [tags, setTags] = useState<string[]>([]);
  const [media, setMedia] = useState<DraftState["media"]>([]);
  const [embeds, setEmbeds] = useState<DraftState["embeds"]>([]);

  const [isMakingVideo, setIsMakingVideo] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [locationName, setLocationName] = useState("");
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);

  const [isAuction, setIsAuction] = useState(true);
  const [isBuyNow, setIsBuyNow] = useState(false);
  const [buyNowPrice, setBuyNowPrice] = useState<number | "">("");
  const [dimensions, setDimensions] = useState("");
  const [medium, setMedium] = useState("");
  const [year, setYear] = useState<number | "">(2026);

  // publish-controls PDCA #8
  const [visibility, setVisibility] = useState<Visibility>("public");
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [seriesIds, setSeriesIds] = useState<string[]>([]);

  // artist-tier-release PDCA #10
  const [earlyAccessDuration, setEarlyAccessDuration] = useState<EarlyAccessDuration | null>(null);
  const [earlyAccessTier, setEarlyAccessTier] = useState<EarlyAccessTier | null>(null);

  const formState: DraftState = {
    type,
    title,
    content,
    genre,
    tags,
    media,
    embeds,
    isMakingVideo,
    scheduledAt,
    locationName,
    locationLat,
    locationLng,
    isAuction,
    isBuyNow,
    buyNowPrice,
    dimensions,
    medium,
    year,
    visibility,
    commentsEnabled,
    seriesIds,
    earlyAccessDuration,
    earlyAccessTier,
  };

  const setters: PostFormSetters = {
    setType,
    setTitle,
    setContent,
    setGenre,
    setTags,
    setMedia,
    setEmbeds,
    setIsMakingVideo,
    setScheduledAt,
    setLocationName,
    setLocationLat,
    setLocationLng,
    setIsAuction,
    setIsBuyNow,
    setBuyNowPrice,
    setDimensions,
    setMedium,
    setYear,
    setVisibility,
    setCommentsEnabled,
    setSeriesIds,
    setEarlyAccessDuration,
    setEarlyAccessTier,
  };

  function resetFromDraft(d: DraftState): void {
    setType(d.type);
    setTitle(d.title);
    setContent(d.content);
    setGenre(d.genre);
    setTags(d.tags);
    setMedia(d.media);
    setEmbeds(d.embeds);
    setIsMakingVideo(d.isMakingVideo);
    setScheduledAt(d.scheduledAt);
    setLocationName(d.locationName);
    setLocationLat(d.locationLat);
    setLocationLng(d.locationLng);
    setIsAuction(d.isAuction);
    setIsBuyNow(d.isBuyNow);
    setBuyNowPrice(d.buyNowPrice);
    setDimensions(d.dimensions);
    setMedium(d.medium);
    setYear(d.year);
    // publish-controls PDCA #8 — legacy default for older drafts
    setVisibility(d.visibility ?? "public");
    setCommentsEnabled(d.commentsEnabled ?? true);
    setSeriesIds(d.seriesIds ?? []);
    // artist-tier-release PDCA #10 — legacy default for older drafts
    setEarlyAccessDuration(d.earlyAccessDuration ?? null);
    setEarlyAccessTier(d.earlyAccessTier ?? null);
  }

  return { formState, setters, resetFromDraft };
}
