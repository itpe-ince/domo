---
name: auction-promotion-suite PR3 complete
description: Frontend PR3 for #11 auction-promotion-suite shipped — AuctionCountdown, AuctionShareCard, ShareIcon, PostCard + FeedItem D-1h countdown, posts/[id] full widget + share button, 16 i18n keys x 5 locales, tsc 0 errors
type: project
---

PR3 (Frontend) of #11 auction-promotion-suite shipped 2026-05-04.

**Why:** Phase 4 final PDCA. Backend PR1+PR2 complete (73 pytest passing). Frontend PR3 completes the feature.

**Files created:**
- `src/components/AuctionCountdown.tsx` — adaptive 60s/1s interval widget, SSR-safe, a11y role="timer"
- `src/components/AuctionShareCard.tsx` — z-[60] modal, POST share-card API, clipboard fallback, cache busting

**Files modified:**
- `src/components/icons.tsx` — ShareIcon (share-2 SVG pattern)
- `src/lib/api.ts` — AuctionView +share_card_url/share_card_generated_at, PostView +active_auction_end_at, AuctionShareCardResponse type, generateAuctionShareCard()
- `src/components/PostCard.tsx` — D-1h compact AuctionCountdown at bottom-left (opposite corner from auction/buy-now badges)
- `src/components/FeedItem.tsx` — D-1h compact AuctionCountdown before engagement bar
- `src/app/posts/[id]/page.tsx` — full AuctionCountdown + AuctionShareCard (owner-only) for active auctions
- `src/i18n/{ko,en,ja,zh,es}.json` — 16 keys each (auction.ended, auction.countdown.*, share.*)

**Integration points verified:** feed (FeedItem), explore (PostCard), search (PostCard), users/[id] (PostCard), posts/[id] embedded

**Key patterns:**
- i18n uses `{{varName}}` template style (double curly braces), NOT `{varName}`
- apiFetch returns `.data` already unwrapped — do NOT double-unwrap
- AuctionShareCard uses `isOwner` prop guard (backend 403s non-owners anyway)
- AuctionCountdown: isUnder1h in deps array causes useEffect re-run at D-1h boundary (R-FE-7)

**How to apply:** Next PDCA: check if backend active_auction_end_at field is being populated in PostView responses from /posts/feed and /posts/explore endpoints.
