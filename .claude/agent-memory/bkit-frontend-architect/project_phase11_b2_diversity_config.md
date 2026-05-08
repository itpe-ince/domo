---
name: phase11-B-2 diversity config UI complete
description: Phase 11 B-2 admin diversity config tuning page shipped; 7 files created/modified in v1/admin
type: project
---

Phase 11 B-2 완료: `/admin/diversity-config` 다양성 설정 튜닝 페이지.

**Why:** K-2 백엔드(diversity_configs 테이블 + GET/PATCH API)에 대응하는 Admin UI — 운영자가 슬라이더로 신진작가 부스팅/장르·지역 다양성 파라미터를 DB 직접 조작 없이 조정.

**How to apply:** 다음 작업(B-1 A/B 테스트 페이지)과 AdminShell "ML Operations" 그룹 공유 — 그룹은 B-2에서 먼저 신설, experiments placeholder 포함.

**Key decisions:**
- Admin app에 TanStack Query 미설치 → 기존 패턴(useState + useCallback) 사용, useDiversityConfig.ts 직접 구현
- DiversityConfigForm 내부에서 saving state 자체 관리 (shell의 patching과 분리)
- candidate_pool_size 슬라이더 제외 (운영자 실수 방지 설계 결정)
- 재설정 버튼: confirm 없이 즉시 PATCH 호출 (design spec 준수)
- KPI 위젯: Phase 11 범위에서 파라미터 기반 목표값 표시 + PostHog 링크; Phase 12에서 /api/admin/diversity-config/stats 연동 예정

**Files (신규/수정):**
- 신규: v1/admin/src/app/diversity-config/page.tsx
- 신규: v1/admin/src/components/diversity/DiversityConfigShell.tsx
- 신규: v1/admin/src/components/diversity/DiversityConfigForm.tsx
- 신규: v1/admin/src/components/diversity/DiversityKPIWidget.tsx
- 신규: v1/admin/src/lib/hooks/useDiversityConfig.ts
- 수정: v1/admin/src/lib/api.ts (DiversityConfigOut, DiversityConfigPatch, adminListDiversityConfigs, adminPatchDiversityConfig 추가)
- 수정: v1/admin/src/components/AdminShell.tsx ("ML Operations" 그룹 신설)
