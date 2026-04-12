# Domo Phase 0~1 Gap Analysis

> **분석일**: 2026-04-11
> **대상**: Phase 0(스캐폴딩) + Phase 1(컨텐츠 + 작가 심사)
> **에이전트**: bkit:gap-detector
> **결과**: 초기 92% → **P0 픽스 후 약 96%** — Phase 2 진입 가능

## 픽스 적용 현황 (2026-04-11 후속)

| ID | 항목 | 상태 | 비고 |
|----|------|:----:|------|
| G1 | 디지털 아트 판독 큐 + verdict API | ✅ | `GET /admin/posts/digital-art-queue`, `POST /admin/posts/{id}/digital-art-verdict` 추가, 13개 검증 모두 통과 |
| G2 | `GET /posts/{id}` pending_review 노출 제한 | ✅ | published만 공개, pending_review/hidden은 작성자/admin만 조회 |
| 부수 | 시드 유저 + Google mock 로그인 충돌 | ✅ | `auth/sns/google`에 email fallback 추가, 기존 유저에 SNS identity 자동 어댑트 |

---

## 1. 종합 매칭률

| 영역 | 점수 | 비고 |
|------|------|------|
| 데이터 모델 | 98% | `payout_account` JSONB 누락 + `size_bytes` 타입 차이 |
| API | 85% | 디지털 아트 판독 큐, 미디어 업로드, 알림 조회 누락 |
| 비즈니스 로직 | 90% | 피드 interleave 단순화, 판독 후반부 미구현 |
| 권한 매트릭스 | 100% | 설계 §7.2 완전 일치 |
| Design Tokens | 100% | tailwind.config.ts 완전 일치 |
| **종합** | **92%** | Phase 0~1 범위 한정 |

---

## 2. P0 — Phase 2 진입 전 권장 (1~2일)

### G1. 디지털 아트 판독 큐 엔드포인트 누락 [중상]
- **위치**: 설계 §5.7, §3.2 `/admin/posts/digital-art-queue`, `/admin/posts/{id}/digital-art-verdict`
- **현상**: 이미지 포함 포스트가 `pending_review`로 생성되지만 관리자가 `published`로 전환할 경로 없음 → 피드에 영구 미노출
- **영향**: 시드 데이터에서는 직접 `published`로 강제 주입했으나, 실제 사용자가 포스트 작성 시 게시 불가
- **수정**: `app/api/admin.py`에 `GET /admin/posts/digital-art-queue`, `POST /admin/posts/{id}/digital-art-verdict` 추가

### G2. `GET /posts/{id}` pending_review 노출 제한 [중]
- **위치**: `app/api/posts.py:249`
- **현상**: `status not in ('published', 'pending_review')`로 필터링 → 누구나 pending 포스트 조회 가능
- **영향**: 약한 노출 리스크 (디지털 아트 판독 우회)
- **수정**: `published`만 공개, `pending_review`는 작성자/admin만 조회 허용

---

## 3. P1 — 시연 전 바람직 (2~3일)

| ID | 항목 | 위치 | 영향 |
|----|------|------|------|
| G3 | `POST /media/upload` 엔드포인트 | 미구현 | 현재 클라이언트가 URL을 직접 제공해야 함 |
| G4 | `GET /notifications` + 읽음 처리 | 미구현 | Notification row만 쌓이고 UI에서 확인 불가 |
| G5 | `PATCH /users/me` 프로필 편집 | 미구현 | 미성년 정보 수집(§6.9) 전제 |

---

## 4. P2 — 프로토타입 허용 범위 (2차 유보)

| ID | 항목 |
|----|------|
| G6 | `GET /users/{id}/followers`, `/following` 목록 |
| G7 | `PATCH /posts/{id}`, `DELETE /posts/{id}` 수정/삭제 |
| G8 | 피드 `interleave()` 함수 (현재 단순 concat) |
| G9 | 홈 피드를 §4.2 와이어프레임의 X 스타일 3컬럼으로 재구성 |
| G10 | `media_assets.size_bytes`를 BigInteger로 변경 |

---

## 5. Phase 2 진입 조건 평가

| 조건 | 상태 |
|------|:----:|
| 인증/JWT 안정성 | ✅ |
| 권한 미들웨어 일관성 | ✅ |
| 표준 응답 포맷 | ✅ |
| 에러 프레임워크 확장성 | ✅ |
| 핵심 스키마 (users/posts/product_posts) | ✅ |
| 디지털 아트 판독 후반부 | ⚠️ G1 |
| 게시물 노출 정책 | ⚠️ G2 |

**결론**: G1, G2, G4 3개 항목만 우선 해결하면 매칭률 ~96%로 상승 후 Phase 2(블루버드, 경매, Stripe) 진입 가능.

---

## 6. Out of Scope (Phase 2~3, 의도적 제외)

### Phase 2 (거래) — 13개 항목
sponsorships, subscriptions, auctions, bids, orders 테이블 + Stripe 연동 + 후원 모달 + 경매 상세 + 미결제 cron + 경매/결제 에러 코드 6개

### Phase 3 (보완) — 9개 항목
영상 업로드, reports/warnings, 이의 제기, 매출 대시보드, system_settings, 3진 아웃 자동화, 정기 후원 webhook, 미성년자 보호자 연동, 디지털 아트 판독 큐 UI

---

## 7. 다음 액션

1. **P0 픽스 (G1, G2)** → 매칭률 92% → 96%
2. **선택적 P1 픽스 (G4 알림 조회)** → 시연 시 작가 승인 알림 표시 가능
3. **`/pdca iterate domo`** 자동 개선 또는 수동 패치
4. **Phase 2 착수**: sponsorships → auctions → orders → Stripe
