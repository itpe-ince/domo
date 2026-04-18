# Plan — Domo P3 Roadmap (잔여 8개 기능 로드맵)

**Created**: 2026-04-18
**Status**: 기획 완료
**Scope**: P3-1, P3-4 ~ P3-10 (P3-2 KYC, P3-3 정산은 구현 완료)

---

## 완료된 P3

| # | 항목 | 상태 |
|---|---|---|
| ~~P3-2~~ | ~~본인인증 KYC~~ | ✅ 구현 완료 (MockProvider + Toss/Stripe 어댑터) |
| ~~P3-3~~ | ~~정산 배치~~ | ✅ 구현 완료 (주간/월간 + 관리자 승인/지급) |

---

## P3-1: 커뮤니티/그룹

### 개요
학교별, 장르별, 나라별 그룹 — 게시판 형태 (DM 대체)

### 핵심 모델
```
communities (id, name, type, description, cover_image, member_count, created_by)
  type: 'school' | 'genre' | 'country' | 'custom'
community_members (community_id, user_id, role, joined_at)
  role: 'owner' | 'admin' | 'member'
community_posts (id, community_id, author_id, content, media, created_at)
community_comments (id, post_id, author_id, content, created_at)
```

### 자동 그룹 생성
- 학교별: ArtistProfile.school 기준 자동 생성
- 장르별: 시스템 장르(painting/drawing 등) 기본 생성
- 나라별: country_code 기준 자동 생성

### API (10개 예상)
- CRUD: 그룹 생성/조회/수정/삭제
- 멤버: 가입/탈퇴/목록
- 포스트: 작성/목록/댓글

### 작업량: L (3~5일)
### 추천 시기: 베타 런칭 후 유저 100명+
### 의존성: 없음 (자체 구현)

---

## P3-4: 외부 배송 추적

### 개요
실물 작품 배송 상태를 외부 택배 API로 추적

### 접근 방식
- 어댑터 패턴: MockShipping → CJLogistics → FedEx → DHL
- Order에 `tracking_number`, `shipping_carrier` 필드 추가
- 택배사 API 폴링 또는 Webhook으로 상태 업데이트

### 주요 택배사 API
| 택배사 | API | 글로벌 | 비용 |
|---|---|---|---|
| CJ대한통운 | REST API | 한국 | 무료 |
| FedEx | Track API | 글로벌 | 무료 (계정 필요) |
| Aftership | 통합 API | 900+ 택배사 | $11/월~ |

### 추천: Aftership (통합 API, 글로벌 커버리지)

### 작업량: M (2일)
### 추천 시기: 실물 거래 10건+ 발생 후
### 의존성: Aftership 또는 택배사 API 계약

---

## P3-5: 후원자 리워드

### 개요
후원 금액/횟수에 따른 리워드 제공 — 뱃지, 포스터, 작가 카드, 감사 메시지

### 모델
```
sponsor_rewards (id, artist_id, tier, name, description, min_bluebirds, reward_type)
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  reward_type: 'badge' | 'poster' | 'card' | 'message' | 'custom'
sponsor_reward_claims (id, reward_id, sponsor_id, status, claimed_at)
```

### 플로우
1. 작가가 리워드 티어 설정 (예: 10블루버드=뱃지, 50=포스터)
2. 후원자가 누적 달성 시 자동 해금
3. 후원자가 리워드 수령 요청
4. 작가가 배송/발송

### 작업량: M (2~3일)
### 추천 시기: 후원 기능 활성화 후
### 의존성: 없음

---

## P3-6: B2B 리포트

### 개요
학교, 갤러리, 후원사에게 제공하는 비공개 리포트

### 리포트 종류
1. **학교 리포트**: 소속 학생 작가 수, 거래 현황, 랭킹
2. **갤러리 리포트**: 추천 작가 목록, 트렌드 분석
3. **후원사 리포트**: 후원 효과 분석, 작가 성장 데이터

### 구현
- PDF 생성 (WeasyPrint 또는 Puppeteer)
- 관리자 앱에서 리포트 생성 + 다운로드
- 이메일 자동 발송 (월간)

### 작업량: L (3~5일)
### 추천 시기: 학교/갤러리 파트너십 체결 후
### 의존성: PDF 생성 라이브러리

---

## P3-7: AI 채팅 고객 지원

### 개요
이메일 + AI 챗봇 + 카카오톡 채널 연동

### 접근 방식 (단계별)
1. **1단계**: FAQ 페이지 + 이메일 문의 폼
2. **2단계**: AI 챗봇 (Ollama gemma4 또는 Claude API)
   - 플랫폼 FAQ 자동 응답
   - 주문/정산 상태 조회
   - 복잡한 질문 → 관리자 에스컬레이션
3. **3단계**: 카카오톡 채널 연동

### 작업량: M~L (2단계 기준 3일)
### 추천 시기: 유저 1000명+
### 의존성: Ollama (이미 있음) 또는 Claude API

---

## P3-8: 라이브 스트리밍

### 개요
작가의 작업 과정 실시간 스트리밍

### 접근 방식
| 옵션 | 장점 | 단점 | 비용 |
|---|---|---|---|
| **Mux** | 간편, 글로벌 CDN | 유료 | $0.025/분 |
| **AWS IVS** | AWS 통합 | 설정 복잡 | $0.0085/시간 |
| **YouTube Live 임베드** | 무료, 검증됨 | YouTube 의존 | 무료 |
| **Self-hosted (mediasoup)** | 완전 제어 | 인프라 복잡 | 서버 비용 |

### 추천: YouTube Live 임베드 (1차) → Mux (2차)
1차: 작가가 YouTube Live를 시작하고 URL을 포스트에 임베드
2차: Mux SDK로 인앱 스트리밍

### 작업량: S (YouTube 임베드) / L (Mux 통합)
### 추천 시기: 장기 로드맵
### 의존성: Mux 또는 AWS IVS 계약 (2차)

---

## P3-9: 모바일 앱

### 개요
웹 반응형 → 모바일 네이티브 앱

### 접근 방식
| 옵션 | 장점 | 단점 |
|---|---|---|
| **PWA** | 즉시 적용, 앱스토어 불필요 | 푸시 제한 (iOS), 네이티브 기능 제한 |
| **React Native** | 네이티브 성능, 코드 재사용 | 학습 곡선, 별도 프로젝트 |
| **Expo** | 빠른 개발, OTA 업데이트 | 네이티브 모듈 제한 |
| **Capacitor** | 기존 웹 코드 래핑 | 성능 제한 |

### 추천: PWA (1차 즉시) → React Native/Expo (2차)
1차: `manifest.json` + service worker → 홈 화면 추가
2차: React Native + API 재사용

### 작업량: S (PWA) / XL (React Native)
### 추천 시기: 2차 출시
### 의존성: App Store/Play Store 등록 (2차)

---

## P3-10: 2차 언어 (ja/zh/es)

### 개요
일본어, 중국어(번체), 스페인어 UI 번역 파일 추가

### 구현
- `i18n/ja.json`, `i18n/zh.json`, `i18n/es.json` 추가
- 기존 I18nProvider에 locale 옵션 추가
- 사이드바 언어 전환 확장

### 번역 방식
1. **AI 번역**: Ollama gemma4로 ko.json → ja/zh/es 자동 번역
2. **수동 검수**: 네이티브 스피커 검수 (5% 오류율 보정)
3. **콘텐츠 번역**: 기존 translation.py가 자동 처리 (target_lang 확장)

### 작업량: S (AI 번역 1시간 + 검수)
### 추천 시기: 글로벌 확장 시
### 의존성: 없음 (Ollama 이미 있음)

---

## 우선순위 정리

### Phase A — 즉시 (외부 의존성 없음)

| # | 항목 | 작업량 | 가치 |
|---|---|---|---|
| P3-10 | 2차 언어 (ja/zh/es) | S | 글로벌 접근성 |
| P3-9a | PWA 기본 설정 | S | 모바일 홈 화면 추가 |

### Phase B — 베타 후 (유저 데이터 필요)

| # | 항목 | 작업량 | 조건 |
|---|---|---|---|
| P3-1 | 커뮤니티/그룹 | L | 유저 100+ |
| P3-5 | 후원자 리워드 | M | 후원 활성화 |
| P3-7a | FAQ + 문의 폼 | S | 즉시 |

### Phase C — 거래 활성화 후

| # | 항목 | 작업량 | 조건 |
|---|---|---|---|
| P3-4 | 외부 배송 추적 | M | 실물 거래 10+ |
| P3-6 | B2B 리포트 | L | 파트너십 |

### Phase D — 장기 로드맵

| # | 항목 | 작업량 |
|---|---|---|
| P3-8 | 라이브 스트리밍 | L |
| P3-9b | React Native 앱 | XL |
| P3-7b | AI 챗봇 | M |
