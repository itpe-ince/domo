---
name: domo editor-revamp-roadmap 진행 상태
description: editor-revamp-roadmap의 11개 sub-PDCA 현황 및 실행 전략 (2026-04-30 기준)
type: project
---

에디터 전면 개편 로드맵이 확정되어 순차 실행 중.

**Why:** 사용자가 Phase 1을 sequential로 (#1 → #2 → #3) 실행하기로 결정. 각 sub-PDCA는 별도 plan.md 문서로 본격 진입.

**How to apply:** 로드맵 문서는 `/Users/sangincha/dev/domo/v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`. 각 sub-PDCA plan은 같은 디렉토리에 `{feature}.plan.md`로 생성.

현재 진행:
- #1 `editor-role-gating`: 완료 아카이브 (2026-04-29). Match Rate 98%. 아카이브: `docs/archive/2026-04/editor-role-gating/`
- #2 `editor-draft-autosave`: plan.md 작성 완료 (2026-04-30). Open Questions Q-1~Q-5 사용자 답변 대기. 파일: `docs/01-plan/features/editor-draft-autosave.plan.md`
  - 핵심: localStorage-first + 서버 draft 2계층 전략. Post.status='draft' DB 변경 불필요(이미 지원). Draft API 4개 엔드포인트 신규 필요.
- #3 `editor-responsive-redesign`: 미착수

Critical Path: 1 → 2 → 3 → 4 → 6 → 8 → 10 (약 5~6주)
Deferred: #9 `artist-pricing-assist` (데이터 축적 부족)

Lessons learned (#1 기준, #2 이후 적용):
- Plan 단계에서 scope 초과 판단 전 코드 사전 탐색 필수
- 사용자 우려가 scope 벗어나면 새 sub-PDCA로 분리
- 백엔드 사전 조사로 작업 범위 줄면 PDCA 규모 즉시 재평가
