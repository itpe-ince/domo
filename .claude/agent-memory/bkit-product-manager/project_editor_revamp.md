---
name: domo editor-revamp-roadmap 진행 상태
description: editor-revamp-roadmap의 11개 sub-PDCA 현황 및 실행 전략 (2026-05-03 기준)
type: project
---

에디터 전면 개편 로드맵이 확정되어 순차 실행 중.

**Why:** 사용자가 Phase 1을 sequential로 (#1 → #2 → #3) 실행하기로 결정. 각 sub-PDCA는 별도 plan.md 문서로 본격 진입.

**How to apply:** 로드맵 문서는 `/Users/sangincha/dev/domo/v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`. 각 sub-PDCA plan은 같은 디렉토리에 `{feature}.plan.md`로 생성.

현재 진행:
- #1 `editor-role-gating`: 완료 아카이브 (2026-04-30). Match Rate 98%. 아카이브: `docs/archive/2026-04/editor-role-gating/`
- #2 `editor-draft-autosave`: 완료 아카이브 (2026-04-30). 아카이브: `docs/archive/2026-04/editor-draft-autosave/`
- #3 `editor-responsive-redesign`: 완료 아카이브 (2026-05-01). Match Rate 96%. 아카이브: `docs/archive/2026-05/editor-responsive-redesign/`
  - 산출물: 12 컴포넌트 + 3 hooks + 2 icons + 135 i18n entries. page.tsx 803→547 LOC
  - 5개 통합 지점: useDraftAutosave / DraftRestoreDialog / 멀티탭 경고 / PostTypeSelector / useArtistGate 모두 회귀 0
- #4 `editor-media-ux`: **완료 아카이브 (2026-05-02)**. Match Rate 95%.
  - 아카이브: `docs/archive/2026-05/editor-media-ux/`
  - 산출물: useMediaUploadQueue / MediaPreviewList(재작성) / SortableMediaCard(신규) / MediaUploadProgress(신규) / alembic 0036_media_caption / PATCH /v1/media/{id}
  - 5개 통합 지점: 회귀 0 확인
- #6-image `editor-image-studio`: **완료 아카이브 (2026-05-03)**. Match Rate 96%.
  - 아카이브: `docs/archive/2026-05/editor-image-studio/`
  - 산출물: ImageEditor 모달(Konva) + SortableMediaCard 편집 버튼 + POST /v1/media/{id}/transform + crop_meta jsonb + alembic 0037
- #8 `publish-controls`: **완료 아카이브 (2026-05-03)**. Match Rate 100%.
  - 아카이브: `docs/archive/2026-05/publish-controls/`
  - 산출물: Post.visibility + Post.comments_enabled + Series 모델 + post_series_membership + alembic 0038~0040 + POST /v1/posts/{id}/publish + _visibility_filter_for_viewer + PublishOptionsPanel
- #10 `artist-tier-release`: **Plan 완료 (2026-05-03)**. OQ 10개 사용자 결정 대기.
  - 파일: `v1/docs/01-plan/features/artist-tier-release.plan.md`
  - 핵심: M (4~5일). B-4 "후원자/단골 우선 공개". alembic 0041 (early_access_until + early_access_tier) + _visibility_filter_for_viewer 확장 + tier_release_jobs.py + TierReleasePicker
  - OQ 10개 (권장 default 모두 제시) — 사용자 "권장대로 일괄 수락" 후 /pdca design 진입

Critical Path: 1 ✅ → 2 ✅ → 3 ✅ → 4 ✅ → 6-image ✅ → 8 ✅ → **10 (plan 완료, OQ 대기)** → (완료)
Deferred: #9 `artist-pricing-assist` (데이터 축적 부족)

Lessons learned (#1~#3 기준, #4 이후 적용):
- Plan 단계에서 scope 초과 판단 전 코드 사전 탐색 필수
- OQ 권장 default 표 제시 → 사용자 일괄 수락 패턴 유효
- 5개 통합 지점 체크리스트를 Do 단계 각 Step 완료 후 즉시 실행
- backend 변경 포함 PDCA는 gap-detector 활용 권장 (frontend-only보다 검증 비용 큼)
