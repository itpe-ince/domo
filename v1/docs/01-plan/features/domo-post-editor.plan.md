# Plan — Domo Post Editor 개선 (미디어 리치 에디터)

**Feature**: domo-post-editor
**Created**: 2026-04-13
**Phase**: Plan
**Status**: Confirmed

---

## 1. Problem Statement

현재 등록 페이지(`/posts/new`)는 텍스트(제목/내용) + 파일 업로드(이미지/영상) + YouTube/Vimeo URL 임베드만 지원한다. 최신 SNS 플랫폼(X, Instagram, TikTok)이 제공하는 다양한 미디어 소재를 활용할 수 없어, **실물 작품의 창작 과정을 풍부하게 기록하고 공유**하는 Domo의 핵심 가치에 부족하다.

### 플랫폼 핵심 컨셉

> 디지털 아트 제외. 사람이 직접 스케치북/유화로 그린 **실물 작품**을 사진 촬영하여 등록.
> 그 작품의 **창작 활동을 타임라인**으로 올리거나, **동영상(타임랩스)**으로 올려
> 어떤 방식으로 제작되었는지 플랫폼 사용자들이 볼 수 있도록 미디어를 제공하는 게 핵심.

---

## 2. Goals & Non-Goals

### Goals (이번 사이클)

1. **미디어 툴바 UI** — 텍스트 입력 하단에 아이콘 기반 툴바 배치
2. **GIF 업로드** — 사용자가 직접 GIF 파일을 업로드 (외부 API 검색 없음)
3. **이모지 피커** — 네이티브 브라우저 이모지 또는 경량 피커
4. **oEmbed 확장** — YouTube, Instagram, TikTok, X 4개 플랫폼 URL 자동 감지 + 프리뷰
5. **스케줄 게시** — 경매 시작/판매 시작 시간 예약 (`scheduled_at` 필드)
6. **위치/지도 태그** — 전시회/갤러리/작업실 위치 태그 (지도 API 연동)
7. **해시태그 자동완성** — `#` 입력 시 기존 태그 제안

### Non-Goals (제외)

- 드로잉/스케치 도구 (실물 작품 플랫폼이므로 취지에 맞지 않음)
- GIF 검색 (GIPHY/Tenor API, 사용자가 직접 업로드로 대체)
- 투표/설문 (MVP에서 불필요)
- 리치 텍스트 에디터 (WYSIWYG, 마크다운 — 복잡도 과도)

---

## 3. Resolved Questions

| # | 질문 | 결정 | 근거 |
|---|---|---|---|
| 1 | 드로잉 기능 | 제외 | 디지털 아트 X, 실물 작품 촬영 업로드가 핵심 |
| 2 | GIF 소스 | 사용자 직접 업로드 | 외부 API 의존 없음, 창작 과정 GIF도 직접 제작 |
| 3 | oEmbed 범위 | YouTube, Instagram, TikTok, X | 신진 작가 타겟 SNS 4개로 제한 |
| 4 | 스케줄 | 경매/판매 시작 시간 관리 | 작가가 원하는 시점에 작품 공개+판매 시작 |
| 5 | 위치/지도 | 가장 연계 쉬운 API 활용 + 적용 가이드 | 전시회/갤러리/작업실 위치 태그 용도 |

---

## 4. Feature Detail

### 4.1 미디어 툴바 아이콘

현재의 분산된 업로드 UI를 하단 툴바로 통합:

```
┌──────────────────────────────────────────┐
│ 제목                                      │
├──────────────────────────────────────────┤
│                                          │
│ 내용을 입력하세요...                      │
│                                          │
│ [첨부된 미디어 프리뷰 영역]              │
│                                          │
├──────────────────────────────────────────┤
│ 🖼  GIF  😊  ▶️  📍  ⏰  #              │ ← 미디어 툴바
│ 이미지 GIF 이모지 임베드 위치 스케줄 태그 │
└──────────────────────────────────────────┘
```

| 아이콘 | 기능 | 동작 |
|---|---|---|
| 🖼 | 이미지/영상 첨부 | file input 트리거 (image/*, video/*) |
| GIF | GIF 업로드 | file input 트리거 (image/gif만) |
| 😊 | 이모지 | 피커 팝오버 → 텍스트에 삽입 |
| ▶️ | 임베드 | URL 입력 모달 → 자동 oEmbed 감지 |
| 📍 | 위치 | 지도 검색 모달 → 장소 선택 |
| ⏰ | 스케줄 | 날짜/시간 피커 → 예약 시간 설정 |
| # | 해시태그 | 태그 입력 → 자동완성 드롭다운 |

### 4.2 oEmbed 자동 감지

URL 패턴 매칭으로 플랫폼 감지:

| 플랫폼 | URL 패턴 | 프리뷰 |
|---|---|---|
| YouTube | `youtube.com/watch?v=`, `youtu.be/` | 썸네일 + 제목 카드 |
| Instagram | `instagram.com/p/`, `instagram.com/reel/` | 이미지 + 캡션 카드 |
| TikTok | `tiktok.com/@*/video/` | 썸네일 + 작성자 카드 |
| X (Twitter) | `x.com/*/status/`, `twitter.com/*/status/` | 텍스트 + 프로필 카드 |

프론트에서 URL 패턴 감지 → 백엔드 `/media/oembed?url=` 엔드포인트에서 메타데이터 반환.

### 4.3 스케줄 게시 (경매/판매 시작 관리)

- **`scheduled_at`** 필드를 `posts` 테이블에 추가
- `scheduled_at`이 설정되면 포스트 상태 = `scheduled` (비공개)
- 백엔드 크론잡이 매분 체크 → `scheduled_at <= NOW()`인 포스트를 `published`로 전환
- 경매의 경우 `auctions.start_at`도 동일 시간으로 설정

### 4.4 위치/지도

- 장소 검색 → 위치명 + 좌표(lat/lng) 저장
- `posts` 테이블에 `location_name`, `location_lat`, `location_lng` 추가
- 포스트 상세에서 미니맵 표시

---

## 5. 위치/지도 API 플랫폼 비교

| API | 무료 티어 | 장점 | 단점 |
|---|---|---|---|
| **Kakao Maps** | 월 30만 콜 무료 | 한국 주소 정확, 한국어 네이티브 | 해외 커버리지 약함 |
| **Google Maps** | 월 $200 크레딧 (약 28K 콜) | 글로벌 커버리지, 가장 풍부한 데이터 | 가격 비쌈, API 키 필수 |
| **Mapbox** | 월 50K 로드 무료 | 커스텀 디자인 우수, 성능 좋음 | Places API 별도 |
| **Naver Maps** | 월 10만 콜 무료 | 한국 정확도 높음 | 해외 미지원 |
| **OpenStreetMap + Nominatim** | 완전 무료 | 오픈소스, API 키 불필요 | 상업 이용 시 자체 서버 권장 |

### 추천: **Kakao Maps** (1순위) + **Mapbox** (글로벌 확장 시)

**근거**:
- Domo 타겟 사용자가 동남아/라틴/동유럽 신진 작가이지만, 초기 프로토타입은 한국 중심
- Kakao Maps가 **가장 쉬운 연동** (JavaScript SDK CDN 한 줄 + REST API)
- 월 30만 콜 무료 → 프로토타입에 충분
- 글로벌 확장 시 Mapbox로 전환 (어댑터 패턴 적용)

---

## 6. Dependencies & Risks

### Dependencies

| 항목 | 종류 | 상태 |
|---|---|---|
| Kakao Maps API 키 | 외부 | 발급 필요 (https://developers.kakao.com) |
| `scheduled_at` DB 마이그레이션 | 내부 | Alembic 추가 |
| `location_*` DB 마이그레이션 | 내부 | Alembic 추가 |
| oEmbed 메타데이터 파싱 | 내부 | 백엔드 httpx로 구현 |

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| oEmbed 외부 URL 파싱 실패/타임아웃 | 중 | 3초 타임아웃 + fallback 링크 카드 |
| Kakao Maps API 키 미발급 시 | 중 | 위치 기능만 비활성화, 나머지 정상 동작 |
| 스케줄 크론잡 정확도 | 낮 | 1분 간격 → 최대 1분 지연 허용 |

---

## 7. Success Metrics

- [ ] 미디어 툴바 7개 아이콘 모두 동작
- [ ] GIF 파일 업로드 + 프리뷰 표시
- [ ] YouTube/Instagram/TikTok/X URL 붙여넣기 → 자동 프리뷰 카드
- [ ] 이모지 피커에서 선택 → 텍스트 삽입
- [ ] 위치 검색 → 장소 선택 → 포스트에 위치 태그 표시
- [ ] 스케줄 설정 → 예약 시간에 자동 공개
- [ ] `#` 입력 시 기존 태그 자동완성 드롭다운

---

## 8. Next Step

✅ 위치/지도 API 적용 가이드 생성 → `/pdca design domo-post-editor`
