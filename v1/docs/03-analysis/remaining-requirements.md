# 잔여 요건 전수 점검 — Domo Lounge (최종 업데이트)

**Date**: 2026-04-18 (updated)
**DB 마이그레이션**: 0001 ~ 0020 (20개 모두 실행됨)
**백엔드 API**: 20개 라우터
**프론트 페이지**: 20개
**모델**: 15개

---

## 1. 구현 완료 (33개)

| # | 고객 요구 | 상태 |
|---|---|---|
| ✅ | 넷플릭스 갤러리 뷰 + View 모드 분리 | GalleryView + 피드 분리 |
| ✅ | 블루버드 $1 USD + 수수료 10% 통일 | 전 모델 USD |
| ✅ | 작가 심사 4단계 위저드 + 확장 필드 13개 | artist-apply 컴포넌트 6개 |
| ✅ | 학교 이메일 인증 (.edu) | 인증 코드 발송/확인 |
| ✅ | 학교 관리 (마스터 테이블 + CRUD) | 시드 12교 + admin 관리 |
| ✅ | 졸업 후 자동 전환 (크론잡) | badge_cron_loop |
| ✅ | 등급 체계 (student/emerging/recommended/popular) | 자동 + 수동 변경 |
| ✅ | TOP 10 랭킹 API | /rankings/artists + /artworks |
| ✅ | 경매 + 즉시구매 | 둘 다 지원 |
| ✅ | 경매 기간 3/7/14일 제한 | duration_days validator |
| ✅ | 구매자 수수료 10% | buyer_fee 자동 계산 |
| ✅ | 에스크로 정산 (배송→검수→정산) | ship/inspect/dispute API |
| ✅ | 익명 후원 + 공개 범위 + 정기 후원 | Sponsorship + Subscription |
| ✅ | 팔로우/팔로잉 + 알림 | Follow + Notification |
| ✅ | DM 불가 (확정) | 의도적 미구현 |
| ✅ | 디지털 아트 제외 | 판독 큐 |
| ✅ | 신고/제재 3-strike + 이의 제기 | Report + Warning + Appeal |
| ✅ | GDPR 삭제 + 미성년 보호자 동의 | gdpr_cron + GuardianConsent |
| ✅ | 통합 검색 3탭 + 필터/정렬 | SearchBar + SearchPage |
| ✅ | 미디어 리치 에디터 7개 툴바 | MediaToolbar 7 컴포넌트 |
| ✅ | 메이킹 영상 | is_making_video + 갤러리 섹션 |
| ✅ | oEmbed (YouTube/Instagram/TikTok/X) | /media/oembed |
| ✅ | 스케줄 게시 (예약) | scheduled_at + schedule_cron |
| ✅ | 위치 태그 | location_name/lat/lng |
| ✅ | i18n (한국어+영어) + 13개 파일 | I18nProvider + 언어 전환 |
| ✅ | 자동 번역 (Ollama AI / Google) | 어댑터 + 캐시 + 관리자 설정 |
| ✅ | 관리자 앱 분리 (포트 3800) | 8페이지 |
| ✅ | 영상 용량 200MB | VIDEO_MAX 변경 |
| ✅ | 작품 북마크 (관심) | bookmarks API 3개 |
| ✅ | 시리즈/컬렉션 CRUD | collections API 5개 |
| ✅ | 온보딩 장르 선택 | preferred_genres + 칩 UI |
| ✅ | 추천 이유 표시 | recommendation_reason (following/trending) |
| ✅ | 활동 로그 수집 | user_activity_logs + /activity/track |
| ✅ | 다통화 환산 | /activity/exchange-rate + /convert |
| ✅ | 레이아웃 통일 | 전 페이지 max-w-3xl |

---

## 2. P3 — 대규모 기획 필요 (10개)

| # | 항목 | 고객 요구 | 의존성 | 추천 시기 |
|---|---|---|---|---|
| P3-1 | **커뮤니티/그룹** | 학교/장르/나라별 | 별도 PDCA | 베타 런칭 후 |
| P3-2 | **본인인증 KYC** | 작가+컬렉터 | Toss/PASS/Stripe Identity 계약 | 결제 라이브 전 필수 |
| P3-3 | **주간/월간 정산 배치** | 검수 후 즉시만 | 결제 인프라 | 운영 시작 전 |
| P3-4 | **외부 배송 추적** | 상태값만 | CJ/FedEx API | 실물 거래 활성화 시 |
| P3-5 | **후원자 리워드** | 뱃지만 | 기획 필요 | 후원 활성화 후 |
| P3-6 | **B2B 리포트** | 비공개 | 기획 필요 | 학교/갤러리 파트너십 |
| P3-7 | **AI 채팅 고객 지원** | ❌ | 외부 서비스 | 유저 1000+ |
| P3-8 | **라이브 스트리밍** | ❌ | 영상 인프라 | 장기 로드맵 |
| P3-9 | **모바일 앱** | 웹 반응형 | React Native/PWA | 2차 출시 |
| P3-10 | **2차 언어** (ja/zh/es) | 한+영 완료 | 번역 파일 추가 | 글로벌 확장 시 |

---

## 3. 프로토타입 완성도

```
프로토타입 완성도: ██████████████████░░ 90%

구현 완료: 33/43 항목 (77%)
P3 잔여: 10항목 (대부분 외부 의존성 또는 장기 로드맵)
DB 마이그레이션: 20개 모두 실행
백엔드 API 라우터: 20개
프론트 페이지: 20개
모델: 15개
크론잡: 4개 (경매/GDPR/스케줄/배지)
```

### 프로토타입으로서 고객 시연 가능한 상태:
- ✅ 넷플릭스 갤러리 + X 스타일 피드
- ✅ 작가 심사 신청 (4단계 위저드 + 학교 인증)
- ✅ 작품 등록 (미디어 리치 에디터)
- ✅ 경매 + 즉시구매 + 구매자 수수료 + 에스크로
- ✅ 블루버드 후원 ($1 USD)
- ✅ 검색 + 북마크 + 팔로우
- ✅ 관리자 패널 (유저/학교/콘텐츠/거래)
- ✅ 한국어/영어 전환 + AI 번역
