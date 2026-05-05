---
name: Phase 6 A-7 Storytelling Hub
description: A-7 완료: /stories hub + /users/[id]/timeline + 5 locale i18n 27 keys; tsc 0
type: project
---

A-7 Storytelling Hub 완료 (2026-05-04).

**What:** `/stories` 메인 허브 3-section 레이아웃 + `/users/[id]/timeline` 작가별 자동 타임라인.

**Why:** README 비전 "스토리텔링" 직접 구현 — 작가 성장 사례(남미 대학생 류) 큐레이션 + 미디어 허브.

**How to apply:** A-7은 backend 없이 순수 프론트엔드. 기존 fetchArtistIndex(rank 1 = Featured), fetchExplore, fetchReceivedSponsorships, fetchArtistRanking를 클라이언트에서 합성해 milestone 생성.

## 신규/수정 파일

**신규:**
- `src/lib/hooks/useArtistTimeline.ts` — milestone 합성 hook (6종 milestone)
- `src/components/stories/MilestoneCard.tsx` — 단일 마일스톤 카드
- `src/components/stories/ArtistTimeline.tsx` — 세로 타임라인 UI
- `src/components/stories/FeaturedArtistHero.tsx` — Featured artist hero card
- `src/components/stories/MediaCoverageGrid.tsx` — 외부 미디어 노출 grid (MVP hardcoded)
- `src/app/stories/page.tsx` — 메인 허브 3-section
- `src/app/users/[id]/timeline/page.tsx` — 작가별 타임라인

**수정:**
- `src/components/icons.tsx` — BookOpenIcon 추가
- `src/components/Sidebar.tsx` — nav.stories 항목 추가 (BookOpenIcon)
- `src/lib/analytics/events.ts` — StoryViewEvent 추가 (FeaturedArtistClickEvent, MediaCoverageClickEvent는 이미 다른 A-7 병행 작업에서 추가됨)
- `src/i18n/{ko,en,ja,zh,es}.json` — stories.* (12 keys) + timeline.* (13 keys) + nav.stories = 27 keys × 5 locale = 135 entries

## Milestones 종류 (6종)
- `joined` — Domo 합류 (가장 이른 포스트 날짜 proxy)
- `first_post` — 첫 작품 공개
- `first_bluebird` — 첫 Blue Bird 후원 받음
- `rank_top_1000 / top_100 / top_10` — artist_index tier 진입
- `highlight_post` — 인기 작품 (likes + bluebird 기준 top 3)

## A-6 통합
- artist_index rank 1 → Featured Artist Hero
- fetchArtistRanking → tier badge + rank milestone
- fetchArtistIndex → history grid (ranks 2-12)

## PostHog events (3개)
- `story_view` (artist_id optional)
- `featured_artist_click` (artist_id)
- `media_coverage_click` (coverage_id, coverage_type)

## Out of scope (carry-over)
- Dynamic OG image (next/og) — /users/[id]/timeline/opengraph-image.tsx
- Admin featured artist curation UI (/admin/featured-artists)
- backend /v1/featured/artist + /v1/users/{id}/milestones endpoints
- Media coverage from system_settings (hardcoded MVP)
