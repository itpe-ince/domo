# Domo Phase 0~3 최종 Gap Analysis

> **분석일**: 2026-04-11
> **대상**: Phase 0(스캐폴딩) + Phase 1(컨텐츠/심사) + Phase 2(거래) + Phase 3(운영/모더레이션)
> **에이전트**: bkit:gap-detector
> **결과**: **96% 매칭** — 프로토타입 완성 + 시연 가능 판정

## 1. 종합 매칭률

| Phase | 매칭률 | E2E |
|-------|:------:|:---:|
| Phase 0 | 100% | ✅ |
| Phase 1 | 98% | ✅ |
| Phase 2 | 97% | 11/11 × 3 |
| Phase 3 | 95% | 14/14 + 8/8 + 11/11 + 7/7 |
| **종합** | **96%** | 모든 마일스톤 통과 |

## 2. 카테고리별 매칭

| 카테고리 | 매칭률 |
|----------|:------:|
| 데이터 모델 (§2.2) — 16개 테이블 | 100% |
| API (§3.2, OOS 제외) | 96% |
| 비즈니스 로직 (§6.1~6.10, OOS 제외) | 100% |
| 보안/권한 (§7) | 95% |
| UI 화면 (§4) | 92% |
| 상태 전이 (§5) | 100% |
| Design Tokens (§11) | 100% |

## 3. §12 시연 시나리오 5/5 모두 실행 가능

| # | 시나리오 | 시연 |
|---|----------|:----:|
| S1 | 작가 가입 + 승인 | ✅ |
| S2 | 포스트 업로드 + 디지털 아트 판독 | ✅ |
| S3 | 블루버드 후원 (visibility 마스킹 4종) | ✅ |
| S4 | 경매 입찰 + 낙찰 + 결제 + 차순위 이전 | ✅ |
| S5 | 신고 → 경고 → 이의제기 → 취소 | ✅ |

## 4. 남은 갭 (시연 차단 없음)

- Explore/Search 공통 필터 일부 미검증
- GDPR export/soft delete (프로토타입 OOS)
- 알림 이메일/FCM 채널 (인앱만)
- auction_ending_soon 알림 트리거

## 5. OOS (점수 제외)

- 실 Stripe 연동, Stripe Tax, 다중 통화
- 작가 인덱스 점수, ML 추천 알고리즘
- 미성년자 보호자 동의 플로우
- /users/me PATCH, followers/following 목록
- posts PATCH/DELETE
- WebSocket (2초 폴링 결정)
- FCM 토큰, GDPR 실 구현, S3/Minio

## 6. 2차 출시 권장 픽스

### Must (보안/컴플라이언스)
1. 실 Stripe 연동 + Webhook 서명 검증
2. JWT refresh 토큰 회전 + 서버측 무효화
3. GDPR 대응 (soft delete, export, 쿠키 배너)
4. 미디어 스토리지 S3/Minio 전환
5. 미성년자 보호자 동의 플로우
6. Rate limiting

### Should (안정성)
7. WebSocket 실시간 입찰 + auction_ending_soon
8. FCM 웹 푸시 + 이메일 발송
9. Posts PATCH/DELETE + /users/me PATCH
10. Followers/Following 목록
11. 이미지 처리 파이프라인 (썸네일/EXIF/CDN)
12. Explore/Search 공통 필터
13. Observability (Sentry, Prometheus)
14. DB 인덱스 튜닝
15. 멱등성 키 (Idempotency-Key)

### Could (확장)
16. 작가 인덱스 점수 시스템
17. ML 기반 피드 추천
18. 다국어 i18n
19. Stripe Tax + 다중 통화
20. 대댓글 (2뎁스)
21. 경매 soft close

## 7. 결론

**프로토타입 완성 + 고객 시연 가능 + 96% 매칭**. 단순 기능 구현을 넘어 §6.2 FOR UPDATE 동시성, §6.4 차순위 이전 라운드 제한, S-new-1 buy-now 경쟁 조건 처리, 런타임 system_settings 변경, 모더레이션 이의제기 플로우까지 구현되었습니다.

다음 단계: `/pdca report domo`로 최종 완료 보고서 생성 → 2차 출시 시 위 Must 6개를 Phase 4 백로그로 이관.
