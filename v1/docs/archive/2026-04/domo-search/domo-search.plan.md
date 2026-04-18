# Plan — Domo Search (통합 검색)

**Feature**: domo-search
**Created**: 2026-04-12
**Phase**: Plan
**Status**: Draft
**Owner**: (TBD)

---

## 1. Problem Statement

현재 Domo 프로토타입에서 사용자가 특정 작가/작품/장르를 찾으려면 **탐색 페이지의 장르/타입 필터만** 제공된다. 검색창이 없어 다음 사용 경험이 불가능하다:

- "@maria_rio" 같은 작가 핸들/이름으로 직접 찾기
- "sunrise lima" 같은 키워드로 제목/태그/설명 검색
- "painting under $200" 같은 복합 조건 검색
- 특정 경매 상태 ("ending soon") 검색

설계 문서 `design.md §5`에는 이미 `GET /posts/search?q=`와 `GET /users/search?q=` 엔드포인트가 **명시되어 있으나 미구현**. 이 Gap을 메우는 것이 본 사이클의 핵심.

### 사용자 피드백 배경

- 탐색 페이지의 필터만으로는 "내가 아는 작가를 다시 찾기" 플로우가 어색
- 작가 심사 승인 후 홍보를 받은 지인이 앱에 들어왔을 때 "이 작가 이름이 뭐더라"로 검색하는 케이스 없음
- 비로그인 방문자가 SNS 추천 링크로 랜딩 후 다른 유사 작가 탐색이 어려움

---

## 2. Goals & Non-Goals

### Goals (반드시 포함)

1. **글로벌 검색창** — 사이드바/모바일 탭바에서 언제든 접근 가능한 검색 진입점
2. **통합 검색 결과 페이지** `/search?q=...` — 작가/포스트/작품 3개 섹션 탭
3. **백엔드 검색 API**
   - `GET /users/search?q={keyword}&role={user|artist}` — 작가/유저 검색
   - `GET /posts/search?q={keyword}&type=...&genre=...&sort=...` — 포스트/작품 검색
4. **기본 매칭 로직** (프로토타입): SQL `ILIKE` 기반 부분 매칭
   - `users`: `display_name`, `bio`
   - `posts`: `title`, `content`, `tags` (JSON array)
5. **검색 히스토리** (로컬 스토리지 기반, 최근 10개)
6. **빈 상태 & 에러 UX**: 결과 없음 화면, 추천 키워드 제시
7. **반응형**: 데스크탑/모바일 동일한 사용성

### Non-Goals (제외)

- **한국어 형태소 분석** — 프로토타입은 ILIKE로 충분, Elastic/Meilisearch 도입은 Phase 5 검토
- **오타 허용(fuzzy)** — 향후 개선
- **검색어 자동완성(typeahead)** — Phase 2 이후 추가
- **검색 기반 개인화** — 본 사이클 범위 밖
- **이미지/색상 검색** — 장기 로드맵
- **다국어 번역 검색** — Phase 6 이후 (언어 감지와 함께)

---

## 3. User Stories

### Priority 1 (Must)

**US-1**: 비로그인 방문자가 SNS 링크로 랜딩 → 작가 이름을 기억하고 있음 → 검색창에 "maria" 입력 → 결과에서 @maria_rio 프로필로 이동 → 팔로우 유도

**US-2**: 로그인 사용자가 홈에서 특정 장르 작품을 보다가 → 검색창에 "sunset oil painting" 입력 → 제목/태그 매칭 포스트 목록 확인 → 마음에 드는 작품 구매

**US-3**: 사용자가 검색 결과 탭에서 작가 / 포스트 / 경매 작품을 각각 볼 수 있다

### Priority 2 (Should)

**US-4**: 최근 검색어가 검색창 포커스 시 드롭다운으로 표시되어 재검색 용이

**US-5**: 검색 결과 없을 때 "다른 키워드를 시도하거나 탐색 페이지로 이동" CTA

### Priority 3 (Could)

**US-6**: 검색 쿼리 파라미터(`?q=...&tab=posts`)로 공유 가능한 링크

---

## 4. Scope & Constraints

### In-Scope

- 백엔드: `posts.py`에 `/posts/search`, `users.py`에 `/users/search`
- 프론트: `components/SearchBar.tsx` 신규, `app/search/page.tsx` 신규
- 사이드바/모바일 탭바에 검색 진입점 추가
- 모바일: 별도 `/search` 모달 또는 풀스크린 페이지
- 최근 검색 localStorage 저장

### Out-of-Scope

- 검색 로그 수집 (분석용)
- 인기 검색어 순위
- 검색 A/B 테스트 인프라

### Technical Constraints

- PostgreSQL `ILIKE` 성능 한계 — 포스트 10K개 미만에서는 문제 없음. 이후 pg_trgm GIN 인덱스 고려
- `tags` 컬럼은 JSON array — `jsonb_array_elements_text`로 평탄화하여 ILIKE
- Rate limiting 필요 (검색 남용 방지) — 기존 Redis INCR 인프라 재사용
- 최소 쿼리 길이 2자 이상 (백엔드 검증)

### Design System Constraints

- 기존 두쫀쿠 다크 테마 (`#1A1410` 배경 + `#A8D76E` primary) 유지
- SearchBar는 `card` 컴포넌트 + `primary` 포커스 링
- Tailwind 브레이크포인트 (`sm`/`md`/`xl`) 기존 패턴 따름

---

## 5. Proposed Approach (High-Level)

### 5.1 API 설계 (상세는 Design 단계에서)

```
GET /posts/search
  ?q=<keyword>           # 필수, 2자 이상
  &genre=<string>        # 선택
  &type=general|product  # 선택
  &sort=latest|popular   # 선택 (default: latest)
  &limit=20              # max 50
  &cursor=<opaque>       # 페이징

GET /users/search
  ?q=<keyword>           # 필수, 2자 이상
  &role=user|artist      # 선택
  &limit=20
```

### 5.2 Matching SQL (프로토타입)

```sql
-- Posts
WHERE status = 'published'
  AND (
    title ILIKE '%' || :q || '%'
    OR content ILIKE '%' || :q || '%'
    OR EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(tags) AS tag
      WHERE tag ILIKE '%' || :q || '%'
    )
  )

-- Users
WHERE display_name ILIKE '%' || :q || '%'
   OR bio ILIKE '%' || :q || '%'
```

### 5.3 프론트 컴포넌트 구조

```
components/
  SearchBar.tsx          # 재사용 검색창 (Sidebar 삽입용)
app/search/
  page.tsx               # 결과 페이지: 탭(작가/포스트/작품) 구조
```

### 5.4 검색창 위치

- **데스크탑**: 사이드바 상단 로고 아래 또는 우측 레일 상단
- **모바일**: 하단 탭바에 🔍 전용 탭 (탐색과 별도) 또는 상단 검색 버튼

→ Design 단계에서 A/B 결정

---

## 6. Success Metrics

### 기능적 성공 기준

- [ ] `/search?q=maria` 페이지가 @maria_rio를 결과에 포함
- [ ] 포스트 제목/내용/태그 중 어느 필드로든 매칭 가능
- [ ] 검색 결과 빈 상태가 명확한 CTA 제공
- [ ] 최근 검색어 드롭다운 동작
- [ ] 모바일/데스크탑 동일 기능 제공

### 품질 기준

- Gap 분석 Match Rate >= 90%
- 검색 응답 시간 < 300ms (10K 포스트 기준, 로컬 DB)
- 빈 쿼리/1자 쿼리 422 에러 반환
- Rate limit: 분당 30회 초과 시 429

### UX 기준

- 검색창 키보드 접근성 (Enter 검색, Esc 닫기)
- 검색 결과 탭 키보드 이동
- 스크린 리더 `aria-label` / `role="searchbox"`

---

## 7. Dependencies & Risks

### Dependencies

- **내부**:
  - 기존 `apiFetch` 인프라
  - 기존 `PostCard` 컴포넌트 재사용
  - 기존 Redis 기반 rate limiting
- **외부**: 없음 (PostgreSQL ILIKE 내장)

### Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| ILIKE 성능 저하 (포스트 > 10K) | 낮음 (프로토타입 단계) | 중 | Phase 5에 pg_trgm GIN 인덱스 추가, 필요 시 Meilisearch 도입 |
| 한글 검색 품질 낮음 (형태소 분석 없음) | 중 | 중 | 이 버전은 "정확 부분 매칭"만 지원, 한계 UX에 명시 |
| 검색어 스팸/악용 | 낮음 | 낮음 | Rate limiting + 최소 길이 검증 |
| 모바일 검색창 UX 결정 미정 (탭 vs 상단) | 중 | 저 | Design 단계에서 A/B 2안 제시 후 사용자 확인 |

---

## 8. Resolved Questions (2026-04-12)

| # | 질문 | 결정 | 근거 |
|---|---|---|---|
| 1 | 검색창 위치 | 데스크탑 사이드바 (로고 아래) + 모바일 하단 탭 (돋보기) | X 현재 레이아웃 참고 |
| 2 | ending soon 필터 | 본 사이클 포함 (`sort=ending_soon`) | design.md §5에 이미 명시 |
| 3 | 결과 탭 | 작가 / 작품 / 포스트 3탭 (기본: 작가) | Domo 핵심 가치 = 작가 발견 |
| 4 | 빈 상태 | 비슷한 키워드 + 추천 작가 3명 + 탐색 CTA | 이탈 최소화, 기존 추천 로직 재사용 |
| 5 | 검색 로그 | `search_logs` 테이블 + API 로깅 포함, 분석 연동은 다음 사이클 | 추천 알고리즘 데이터 선행 수집 필요 |

---

## 9. Timeline (Rough Estimate)

| Phase | 작업 | 예상 |
|---|---|---|
| Design | API 계약, 컴포넌트 구조, 와이어프레임 | 0.5d |
| Do — Backend | `/users/search`, `/posts/search` 구현 + 테스트 | 0.5d |
| Do — Frontend | SearchBar 컴포넌트 + 결과 페이지 + 통합 | 1d |
| Check | Gap 분석 | 0.5h |
| Act (필요 시) | 개선 이터레이션 | 0.5d |
| Report + Archive | 완료 보고서 | 0.5h |

**총합**: 약 2~3일 (단일 세션 내 완료 가능)

---

## 10. Next Step

✅ `/pdca design domo-search`로 Design 단계 진입

Design 단계에서 다룰 것:
- API 요청/응답 스키마 (JSON 예시 포함)
- SearchBar / SearchPage / 결과 탭 컴포넌트 계층
- 데스크탑/모바일 와이어프레임 (X의 검색 탭 참고)
- 빈 상태 & 에러 상태 세부 디자인
- localStorage 스키마 (최근 검색어)
