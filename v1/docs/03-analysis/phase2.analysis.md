# Domo Phase 0~2 Gap Analysis

> **분석일**: 2026-04-11
> **대상**: Phase 0(스캐폴딩) + Phase 1(컨텐츠/심사) + Phase 2(거래)
> **에이전트**: bkit:gap-detector
> **결과**: **95% 매칭** — Phase 3 진입 가능

## 1. 종합 매칭률

| 영역 | 점수 |
|------|:----:|
| 데이터 모델 (Phase 2 신규) | 97% |
| API (Phase 2 신규) | 95% |
| 비즈니스 로직 §6.1~6.6 | 94% |
| 권한 매트릭스 (Phase 2 신규) | 100% |
| Phase 0~1 P0 회귀 | 100% |
| 프론트엔드 (Phase 2 화면) | 88% |
| **종합** | **95%** |

## 2. Phase 0~1 P0 픽스 회귀 0건

| ID | 항목 | 상태 |
|----|------|:----:|
| G1 | 디지털 아트 verdict | 유지 |
| G2 | pending_review 노출 제한 | 유지 |
| Aux | Google mock email fallback | 유지 |
| 부수 | 작가 승인 시 ArtistProfile 자동 생성 | 유지 |

## 3. Phase 2 매칭 결과 (F5/F6/F7)

| 기능 | 매칭 | 핵심 |
|------|:----:|------|
| F5 일회성 후원 | 93% | sponsorships, mock confirm, 익명/visibility, 셀프 차단 — `/users/{id}/sponsorships`만 누락 |
| F6 정기 후원 | 100% | cancel_at_period_end 정책 §6.6 정확, webhook 처리 포함 |
| F7 경매 + 즉시구매 + 주문 | 96% | FOR UPDATE 락, lazy + cron 자동 전이, §6.4 차순위 이전 (최대 2회) 정확, S-new-1 즉시구매 시 경매 자동 cancel |

## 4. Phase 3 진입 권장 픽스 (P0/P1)

P0 없음. P1 2건만 1일 내 처리 가능:

| ID | 항목 | 예상 |
|----|------|:----:|
| GAP-S1 | `GET /users/{id}/sponsorships` (visibility 마스킹) | 0.5일 |
| Phase1-G4 | `GET /notifications` + `PATCH /notifications/{id}/read` | 0.5일 |

## 5. Out of Scope (Phase 3)

- 영상 업로드 화면, posts PATCH/DELETE, media upload
- reports/warnings 정식 테이블 + /admin/reports* + /admin/appeals
- /admin/dashboard/revenue, /admin/dashboard/stats
- /admin/settings UI
- 정기 후원 관리 화면
- Stripe 실 연동, Stripe Tax, USD/다중 통화
- /users/me PATCH, followers/following 목록
- 미성년자 보호자 동의
- 작가 인덱스 점수, 추천 알고리즘 고도화

## 6. 결론

Phase 0~2 핵심 거래 플로우(후원 → 정기 후원 → 경매 → 즉시구매 → 미결제 cron → 차순위 이전 → 결제)가 end-to-end로 동작하며 설계 §2.2/§3.2/§6.1~6.6과 95% 일치합니다.

**Phase 3 진입 가능**. GAP-S1 + Phase1-G4 (총 1일)을 Phase 3 작업과 병행하면 매칭률 ~97%로 상승합니다.
