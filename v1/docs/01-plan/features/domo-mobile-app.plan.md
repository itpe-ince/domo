# Plan — Domo Mobile App (React Native)

**Feature**: domo-mobile-app
**Status**: Plan only (Phase D — 장기 로드맵)

---

## 1. 접근 방식

### Phase 1: PWA (✅ 완료)
- manifest.json + theme-color → 홈 화면 추가 가능
- 추가 비용 없음, 즉시 적용

### Phase 2: React Native + Expo
- 기존 백엔드 API 100% 재사용
- UI는 별도 구현 (React Native 컴포넌트)
- Expo로 빠른 프로토타이핑 → 이후 eject 가능

### 기술 스택 (추천)
```
framework: Expo SDK 52+
navigation: React Navigation v7
state: Zustand or React Query
api: 기존 lib/api.ts 패턴 재사용
push: Expo Notifications + FCM
storage: AsyncStorage (토큰)
image: expo-image (캐시 + 프리로드)
```

### 주요 화면
1. 홈 (갤러리 뷰 — 가로 스크롤)
2. 피드 (세로 스크롤 — 포스트 카드)
3. 검색
4. 알림
5. 프로필
6. 작품 상세
7. 경매 상세
8. 후원 모달
9. 등록 (카메라 + 갤러리)
10. 설정

### 작업량: XL (4~8주)
### 추천 시기: 베타 유저 1000명+ 달성 후
### 의존성: Apple Developer ($99/년) + Google Play ($25 일회성)

---

## 2. App Store 등록 체크리스트

- [ ] Apple Developer Program 등록
- [ ] Google Play Console 등록
- [ ] 앱 아이콘/스플래시 스크린 디자인
- [ ] 스크린샷 5장 (iPhone + Android)
- [ ] 개인정보 처리방침 URL (이미 존재)
- [ ] 앱 심사 제출 (Apple 1~3일, Google 1일)
