---
name: phase11-B-1 complete
description: Phase 11 B-1 — Admin ML 실험 관리 UI (/experiments) 구현 완료; tsc 0 errors
type: project
---

Phase 11 B-1 (admin A/B 테스트 관리 페이지) 구현 완료. tsc 0 errors, npm run build 성공.

**Why:** K-8 백엔드 API(admin_experiments.py) Phase 10에서 완성, 프론트 미구현 상태 해소.

**How to apply:** AdminShell에 ML Operations 그룹 이미 추가됨. B-2(diversity-config)는 그룹이 있으므로 항목만 추가하면 됨.

## 생성/수정 파일

- `v1/admin/src/app/experiments/page.tsx` — Server wrapper
- `v1/admin/src/components/experiments/ExperimentsShell.tsx` — Client shell (auth gate + filter + 신규 버튼)
- `v1/admin/src/components/experiments/ExperimentsList.tsx` — 카드 리스트 + FilterTabs
- `v1/admin/src/components/experiments/ExperimentCard.tsx` — 개별 실험 카드
- `v1/admin/src/components/experiments/CreateExperimentModal.tsx` — 신규 실험 생성 모달
- `v1/admin/src/components/experiments/PostHogEmbed.tsx` — iframe + fallback
- `v1/admin/src/lib/hooks/useExperiments.ts` — 3 hooks (list, create, results)
- `v1/admin/src/lib/api.ts` — Experiment/ExperimentResults/CreateExperimentPayload 타입 + 3 함수 추가
- `v1/admin/src/components/AdminShell.tsx` — ML Operations 그룹 추가 (이미 linter 반영됨)

## PATCH endpoint 처리

PATCH /admin/experiments/{name} 백엔드 미구현. 일시정지/종료 버튼은 UI에 표시하되 클릭 시 Error throw + group hover tooltip으로 "Phase 12 후속 백엔드 작업 필요" 안내.

## PostHog fallback 동작

NEXT_PUBLIC_POSTHOG_INSIGHTS_BASE_URL 미설정 시 → "PostHog Insights 열기 ↗" 외부 링크. iframe onError 시 자동 fallback.

## i18n 방식

이 프로젝트는 별도 i18n 라이브러리 없이 한국어 직접 하드코드 방식 사용. design 문서의 27 i18n 키는 컴포넌트 내부 한국어 텍스트로 직접 구현됨.
