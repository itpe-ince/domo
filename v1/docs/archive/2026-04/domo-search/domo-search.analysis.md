# Gap Analysis — domo-search (통합 검색) v2

**Date**: 2026-04-12
**Feature**: domo-search
**Revision**: v2 (iterate 1회 후 재분석)
**Match Rate**: 🟢 **96.5%** (이전 80.8%)

---

## 1. Iteration 1 — 해결된 Gap

| ID | 항목 | 수정 내용 | 상태 |
|---|---|---|---|
| M1 | SearchLog 인덱스 | `__table_args__`에 `idx_search_logs_user`, `idx_search_logs_query` 추가 | ✅ |
| M2 | posts/users lower 인덱스 | Alembic 마이그레이션에서 `lower(title)`, `lower(display_name)` 인덱스 생성 | ✅ |
| M3 | Alembic 마이그레이션 | `0010_search_logs.py` 생성 (테이블 + 인덱스 4개) | ✅ |
| M4 | cursor 페이지네이션 | `cursor` 파라미터 추가, `limit+1` 패턴으로 `has_more` 판정 | ✅ |
| M5 | 부분 태그 매칭 | `Post.tags.any(func.concat("%", q, "%"))` 패턴 매칭 추가 | ✅ |
| M6 | Rate Limit | `rate_limit("search")` 적용 (30 req/min by IP), `DEFAULT_LIMITS`에 추가 | ✅ |
| M7 | SearchLog user_id | `_optional_user_id`/`_optional_viewer_id`로 로그인 유저 ID 기록 | ✅ |
| M8 | 작가 탭 role 필터 | "전체/작가만" 2버튼 칩 UI 추가 | ✅ |
| M9 | 작품 탭 장르 필터 | 장르 6개 칩 (전체/painting/drawing/photography/sculpture/mixed_media) | ✅ |
| M10 | 정렬 UI | 작품 탭: 최신순/인기순/마감임박, 포스트 탭: 최신순/인기순 | ✅ |
| C1 | SearchLog 비동기 | try/except + warning 로깅으로 응답 차단 방지 | ✅ |
| C2 | 팔로우 버튼 | 작가 검색 결과 각 행에 [팔로우] 버튼 추가 | ✅ |
| C3 | 동적 키워드 추천 | fetchExplore 결과에서 인기 태그 추출, 없으면 fallback | ✅ |

## 2. 잔여 Gap

| ID | 항목 | 영향도 | 상태 |
|---|---|---|---|
| R1 | 팔로우 버튼 API 연동 | 낮음 | 버튼 UI만 있고 `/users/{id}/follow` POST 미연결 (별도 기능) |
| R2 | SearchLog session_id | 낮음 | 비로그인 세션 식별 미구현 (쿠키 인프라 필요) |
| R3 | design.md §4.1/§5 갱신 | 낮음 | 메인 설계 문서에 검색 관련 API 추가 미반영 |

## 3. Match Rate 산정

| 카테고리 | 가중치 | 점수 | 비고 |
|---|---|---|---|
| 데이터 모델 | 20% | 100% | 모델 + 인덱스 + 마이그레이션 완비 |
| API 설계 (백엔드) | 30% | 95% | cursor, rate limit, 태그 매칭 모두 구현. session_id만 미구현 |
| 프론트엔드 컴포넌트 | 30% | 95% | 필터/정렬 UI, 팔로우 버튼, 동적 키워드 완비. 팔로우 API 연동만 미구현 |
| 와이어프레임/레이아웃 | 10% | 100% | Sidebar + MobileTabBar 일치 |
| 구현 순서 완료도 | 10% | 95% | design.md 갱신만 남음 |

**가중 Match Rate**:
```
0.20×100 + 0.30×95 + 0.30×95 + 0.10×100 + 0.10×95
= 20 + 28.5 + 28.5 + 10 + 9.5
= 96.5%
```

**판정**: 🟢 **96.5% — 통과** (80.8% → 96.5%, +15.7%p)

## 4. 다음 단계

✅ 96.5% 달성 → `/pdca report domo-search` 진행 가능
