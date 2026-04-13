# 위치/지도 API 적용 가이드 — Kakao Maps

**대상**: Domo 포스트 등록 시 위치 태그 기능
**추천 API**: Kakao Maps JavaScript SDK + REST API
**대안 (글로벌 확장)**: Mapbox GL JS + Geocoding API

---

## 1. Kakao Maps API 키 발급

### Step 1: Kakao Developers 가입
1. https://developers.kakao.com 접속
2. 카카오 계정으로 로그인
3. "내 애플리케이션" → "애플리케이션 추가하기"

### Step 2: 앱 생성
- 앱 이름: `Domo Lounge`
- 사업자명: (개인 또는 회사명)

### Step 3: 키 확인
- **JavaScript 키**: 프론트엔드 지도 표시용
- **REST API 키**: 백엔드 장소 검색용

### Step 4: 플랫폼 등록
- "플랫폼" 탭 → "Web" → 사이트 도메인 추가
  - `http://localhost:3700` (개발)
  - `https://domo.tuzigroup.com` (운영, 나중에 추가)

---

## 2. 프론트엔드 — 지도 표시 + 장소 검색

### 2.1 SDK 로드

`frontend/src/app/layout.tsx` 또는 `_document.tsx`에 추가하지 않고,
**지도가 필요한 컴포넌트에서만 동적 로드**:

```typescript
// frontend/src/lib/kakaoMap.ts

const KAKAO_JS_KEY = process.env.NEXT_PUBLIC_KAKAO_JS_KEY || "";

let loadPromise: Promise<void> | null = null;

export function loadKakaoMapSDK(): Promise<void> {
  if (loadPromise) return loadPromise;
  if (typeof window === "undefined") return Promise.resolve();
  if (window.kakao?.maps) return Promise.resolve();

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_JS_KEY}&libraries=services&autoload=false`;
    script.onload = () => {
      window.kakao.maps.load(() => resolve());
    };
    script.onerror = reject;
    document.head.appendChild(script);
  });

  return loadPromise;
}

// TypeScript 타입 선언 (최소)
declare global {
  interface Window {
    kakao: {
      maps: {
        load: (callback: () => void) => void;
        LatLng: new (lat: number, lng: number) => any;
        Map: new (container: HTMLElement, options: any) => any;
        Marker: new (options: any) => any;
        services: {
          Places: new () => {
            keywordSearch: (
              keyword: string,
              callback: (result: any[], status: string) => void
            ) => void;
          };
          Status: { OK: string };
        };
      };
    };
  }
}
```

### 2.2 장소 검색 컴포넌트

```typescript
// frontend/src/components/LocationPicker.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import { loadKakaoMapSDK } from "@/lib/kakaoMap";

export type LocationData = {
  name: string;
  address: string;
  lat: number;
  lng: number;
};

interface LocationPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (location: LocationData) => void;
}

export function LocationPicker({ open, onClose, onSelect }: LocationPickerProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [sdkReady, setSdkReady] = useState(false);
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const markerRef = useRef<any>(null);

  useEffect(() => {
    if (!open) return;
    loadKakaoMapSDK().then(() => setSdkReady(true));
  }, [open]);

  useEffect(() => {
    if (!sdkReady || !mapRef.current || !open) return;
    const { kakao } = window;
    const center = new kakao.maps.LatLng(37.5665, 126.978); // 서울 기본
    mapInstance.current = new kakao.maps.Map(mapRef.current, {
      center,
      level: 5,
    });
  }, [sdkReady, open]);

  function handleSearch() {
    if (!query.trim() || !sdkReady) return;
    setLoading(true);
    const places = new window.kakao.maps.services.Places();
    places.keywordSearch(query, (result, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        setResults(result.slice(0, 5));
      } else {
        setResults([]);
      }
      setLoading(false);
    });
  }

  function handleSelect(place: any) {
    const lat = parseFloat(place.y);
    const lng = parseFloat(place.x);

    // 지도 이동 + 마커
    if (mapInstance.current) {
      const pos = new window.kakao.maps.LatLng(lat, lng);
      mapInstance.current.setCenter(pos);
      if (markerRef.current) markerRef.current.setMap(null);
      markerRef.current = new window.kakao.maps.Marker({
        position: pos,
        map: mapInstance.current,
      });
    }

    onSelect({
      name: place.place_name,
      address: place.road_address_name || place.address_name,
      lat,
      lng,
    });
    onClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
         onClick={onClose}>
      <div className="card w-full max-w-lg p-4 space-y-3"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold">위치 선택</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="장소 검색 (예: 서울시립미술관)"
            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
            autoFocus
          />
          <button onClick={handleSearch} className="btn-primary text-sm">
            검색
          </button>
        </div>

        {/* 지도 영역 */}
        <div ref={mapRef} className="w-full h-48 rounded-lg bg-surface-hover" />

        {/* 검색 결과 */}
        {loading && <p className="text-text-muted text-sm">검색 중...</p>}
        {results.length > 0 && (
          <ul className="space-y-1 max-h-40 overflow-y-auto">
            {results.map((place, i) => (
              <li key={i}>
                <button
                  onClick={() => handleSelect(place)}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-hover text-sm"
                >
                  <div className="font-medium">{place.place_name}</div>
                  <div className="text-xs text-text-muted">
                    {place.road_address_name || place.address_name}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

### 2.3 환경변수

```bash
# frontend/.env.local
NEXT_PUBLIC_KAKAO_JS_KEY=your_javascript_key_here
```

---

## 3. 백엔드 — 위치 데이터 저장

### 3.1 DB 스키마 변경

```python
# posts 테이블에 추가 (Alembic 마이그레이션)
location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
```

### 3.2 API 변경

```python
# POST /posts 요청 body에 추가
class PostCreate(BaseModel):
    # ... 기존 필드
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
```

---

## 4. 포스트 상세에서 미니맵 표시

```typescript
// PostDetail 컴포넌트 내

{post.location_name && (
  <div className="card p-3">
    <div className="flex items-center gap-2 mb-2">
      <span>📍</span>
      <span className="text-sm font-medium">{post.location_name}</span>
    </div>
    {/* Kakao 정적 지도 이미지 (API 호출 없이 URL로 표시) */}
    <img
      src={`https://dapi.kakao.com/v2/maps/staticmap?appkey=${KAKAO_REST_KEY}&center=${post.location_lng},${post.location_lat}&level=3&size=400x200&marker=pos:${post.location_lng},${post.location_lat}`}
      alt={post.location_name}
      className="w-full h-32 rounded-lg object-cover"
    />
  </div>
)}
```

> **주의**: 정적 지도 이미지는 REST API 키 사용. 프론트에서 호출 시 서버 프록시 또는 백엔드에서 URL 생성 권장.

---

## 5. 글로벌 확장 시 Mapbox 전환 가이드

Kakao Maps는 한국 외 지역 커버리지가 약하므로, 글로벌 확장 시 **어댑터 패턴**으로 전환:

```typescript
// lib/mapProvider.ts

interface MapProvider {
  loadSDK(): Promise<void>;
  searchPlaces(query: string): Promise<LocationData[]>;
  renderMap(container: HTMLElement, center: { lat: number; lng: number }): void;
}

class KakaoMapProvider implements MapProvider { ... }
class MapboxProvider implements MapProvider { ... }

// 환경변수로 전환
const provider = process.env.NEXT_PUBLIC_MAP_PROVIDER === "mapbox"
  ? new MapboxProvider()
  : new KakaoMapProvider();

export default provider;
```

### Mapbox 설정 (참고)
1. https://www.mapbox.com 가입 → Access Token 발급
2. `npm install mapbox-gl` (약 200KB gzipped)
3. Geocoding API: `https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json`
4. 월 50K 맵 로드 무료, Geocoding 월 100K 무료

---

## 6. 체크리스트

- [ ] Kakao Developers 앱 생성 + JavaScript 키 발급
- [ ] `NEXT_PUBLIC_KAKAO_JS_KEY` 환경변수 설정
- [ ] `LocationPicker` 컴포넌트 구현
- [ ] `posts` 테이블에 `location_*` 컬럼 추가 (Alembic)
- [ ] `PostCreate` 스키마에 위치 필드 추가
- [ ] 포스트 상세에서 위치 + 미니맵 표시
- [ ] (선택) 어댑터 패턴으로 Mapbox 전환 준비
