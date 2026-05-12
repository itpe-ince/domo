---
name: phase10-CO-1 complete
description: Phase 10 CO-1 — Phase 9 carry-over 11항목 6 PR atomic 청산 완료
type: project
---

Phase 10 CO-1: 11개 carry-over 항목 → 6 atomic PR 청산 완료 (2026-05-05)

**Why:** K-wave1 §5 Gap Analysis에서 식별된 11개 잔존 항목 일괄 청산. alembic 신규 없음.

**How to apply:** 다음 Phase에서 이 작업이 완료된 것으로 전제하고 시작.

PR별 변경 파일:
- PR-1: v1/backend/docs/TESTING_NOTES.md (신규) — skip 사유 3건 명시
- PR-2 backend: app/core/rate_limit.py (post_caption_regenerate/post_caption_override 키), app/api/posts.py (rate_limit dep 추가), tests/unit/test_post_caption_override.py (신규, 9 테스트)
- PR-2 frontend: FeedItem/GalleryView alt 이미 완료 확인 (기존 코드에 이미 반영)
- PR-3: src/components/DocentSection.tsx (신규 분리), app/posts/[id]/page.tsx (import 교체, inline 제거), app/posts/[id]/edit/page.tsx (신규), i18n 5 locale edit_page 키 7개 추가
- PR-4: src/lib/api.ts FeedAlgo "v2" | "auto" 추가
- PR-5: scripts/i18n-key-audit.sh (신규), package.json lint:i18n 스크립트, .github/workflows/i18n-check.yml (신규)
- PR-6: v1/docs/operations/ml-experiments-policy.md (신규), TESTING_NOTES.md ml_experiments 섹션 추가

테스트 실행 권한이 없어 pytest/tsc 결과는 사용자가 직접 확인 필요.
