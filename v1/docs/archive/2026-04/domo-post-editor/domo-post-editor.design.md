# Design — Domo Post Editor (미디어 리치 에디터)

**Feature**: domo-post-editor
**Created**: 2026-04-13
**Phase**: Design
**Plan Reference**: [domo-post-editor.plan.md](../../01-plan/features/domo-post-editor.plan.md)

---

## 1. Data Model 변경

### 1.1 posts 테이블 확장

```sql
-- 기존 posts 테이블에 추가
ALTER TABLE posts ADD COLUMN scheduled_at TIMESTAMPTZ;          -- 예약 게시 시간
ALTER TABLE posts ADD COLUMN location_name VARCHAR(200);        -- 장소명
ALTER TABLE posts ADD COLUMN location_lat DOUBLE PRECISION;     -- 위도
ALTER TABLE posts ADD COLUMN location_lng DOUBLE PRECISION;     -- 경도

-- 인덱스
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at) WHERE scheduled_at IS NOT NULL AND status = 'scheduled';
```

### 1.2 posts.status 변경

기존: `'draft' | 'pending_review' | 'published' | 'hidden' | 'deleted'`
추가: **`'scheduled'`** — 예약 상태. `scheduled_at` 도달 시 `published` 또는 `pending_review`로 전환.

### 1.3 Alembic 마이그레이션

```
0011_post_editor_fields.py
  - posts.scheduled_at (TIMESTAMPTZ, nullable)
  - posts.location_name (VARCHAR 200, nullable)
  - posts.location_lat (DOUBLE PRECISION, nullable)
  - posts.location_lng (DOUBLE PRECISION, nullable)
  - idx_posts_scheduled 인덱스
```

### 1.4 tags 자동완성용 — 기존 테이블 활용

별도 테이블 없이 `SELECT DISTINCT unnest(tags) FROM posts WHERE status='published' AND tags IS NOT NULL` 쿼리로 기존 태그 목록 추출. 프로토타입에서 충분.

---

## 2. API 설계

### 2.1 POST /posts 확장

기존 `PostCreate` 스키마에 필드 추가:

```python
class PostCreate(BaseModel):
    # ... 기존 필드
    scheduled_at: datetime | None = None      # 예약 게시 시간 (UTC)
    location_name: str | None = None          # 장소명
    location_lat: float | None = None         # 위도
    location_lng: float | None = None         # 경도
```

**스케줄 동작**:
- `scheduled_at`이 있으면 `status = 'scheduled'` (비공개)
- `scheduled_at`이 없으면 기존 로직 (`pending_review` 또는 `published`)

### 2.2 GET /posts/tags/suggest (신규)

해시태그 자동완성용:

```
GET /posts/tags/suggest?q={prefix}&limit=10
```

**Response**:
```json
{
  "data": ["painting", "portrait", "oil", "landscape", ...]
}
```

**SQL**:
```sql
SELECT DISTINCT tag
FROM (SELECT unnest(tags) AS tag FROM posts WHERE status='published') t
WHERE tag ILIKE :prefix || '%'
ORDER BY tag
LIMIT :limit
```

### 2.3 GET /media/oembed (신규)

URL을 받아 oEmbed 메타데이터 반환:

```
GET /media/oembed?url={encoded_url}
```

**Response**:
```json
{
  "data": {
    "provider": "youtube",
    "title": "Timelapse Painting",
    "thumbnail_url": "https://img.youtube.com/vi/xxx/hqdefault.jpg",
    "author_name": "Maria Lima",
    "embed_html": "<iframe ...>",
    "url": "https://youtube.com/watch?v=xxx"
  }
}
```

**지원 플랫폼별 oEmbed 엔드포인트**:

| 플랫폼 | URL 패턴 | oEmbed API |
|---|---|---|
| YouTube | `youtube.com/watch`, `youtu.be/` | `https://www.youtube.com/oembed?url={url}&format=json` |
| Instagram | `instagram.com/p/`, `/reel/` | `https://graph.facebook.com/v18.0/instagram_oembed?url={url}&access_token={token}` |
| TikTok | `tiktok.com/@*/video/` | `https://www.tiktok.com/oembed?url={url}` |
| X (Twitter) | `x.com/*/status/`, `twitter.com/*/status/` | `https://publish.twitter.com/oembed?url={url}` |

**참고**: Instagram oEmbed는 Facebook Graph API 토큰이 필요. 프로토타입에서는 URL 메타태그 파싱(og:title, og:image)으로 대체.

**에러 처리**:
- URL 매칭 안 됨 → `422 UNSUPPORTED_URL`
- 외부 API 타임아웃 (3초) → fallback 링크 카드 (URL + 도메인명만)
- 유효하지 않은 URL → `422 INVALID_URL`

### 2.4 스케줄 크론잡

```python
# app/tasks/scheduler.py (기존 startup 태스크에 추가)

async def publish_scheduled_posts():
    """매분 실행: scheduled_at <= NOW()인 포스트를 published로 전환"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Post).where(
            Post.status == "scheduled",
            Post.scheduled_at <= now,
        )
    )
    for post in result.scalars():
        # 미디어 있으면 pending_review, 없으면 published
        has_visual = any(m.type in ("image", "video") for m in post.media)
        post.status = "pending_review" if has_visual else "published"
        post.scheduled_at = None
    await db.commit()
```

---

## 3. 프론트엔드 컴포넌트 설계

### 3.1 컴포넌트 계층

```
app/posts/new/
  page.tsx                    # 리팩터: 미디어 툴바 통합

components/
  post-editor/
    MediaToolbar.tsx           # 7개 아이콘 툴바
    EmojiPicker.tsx            # 이모지 선택 팝오버
    OEmbedInput.tsx            # URL 입력 + 자동 감지 + 프리뷰
    OEmbedCard.tsx             # 임베드 프리뷰 카드 (플랫폼별)
    SchedulePicker.tsx         # 날짜/시간 선택 (네이티브 input)
    LocationPicker.tsx         # 지도 검색 모달 (가이드 참조)
    TagAutocomplete.tsx        # # 트리거 자동완성
    MediaPreviewList.tsx       # 첨부된 미디어 프리뷰 그리드

lib/
  api.ts                       # fetchOEmbed(), fetchTagSuggestions() 추가
  kakaoMap.ts                  # SDK 동적 로드 (가이드 참조)
```

### 3.2 MediaToolbar

```tsx
interface MediaToolbarProps {
  onImageSelect: (files: FileList) => void;
  onGifSelect: (file: File) => void;
  onEmojiSelect: (emoji: string) => void;
  onEmbedAdd: (embed: OEmbedData) => void;
  onLocationSelect: (location: LocationData) => void;
  onScheduleSet: (date: Date | null) => void;
  onTagStart: () => void;  // # 입력 트리거
  disabled?: boolean;
}
```

아이콘 배치 (좌→우):

```
┌──────────────────────────────────────────────┐
│ [🖼] [GIF] [😊] [▶️] [📍] [⏰] [#] │ [등록]  │
└──────────────────────────────────────────────┘
```

| 위치 | 아이콘 | 컴포넌트 | 동작 |
|---|---|---|---|
| 1 | 🖼 ImageIcon | hidden file input | `accept="image/*,video/*"` multiple |
| 2 | GIF | hidden file input | `accept="image/gif"` single |
| 3 | 😊 | EmojiPicker | 팝오버 → 클릭 시 textarea에 삽입 |
| 4 | ▶️ LinkIcon | OEmbedInput | 팝오버 → URL 입력 → 자동 감지 |
| 5 | 📍 MapPinIcon | LocationPicker | 모달 → Kakao 지도 검색 |
| 6 | ⏰ ClockIcon | SchedulePicker | 팝오버 → datetime-local input |
| 7 | # | TagAutocomplete | 포커스 → 태그 입력 → 드롭다운 |

### 3.3 EmojiPicker

네이티브 브라우저 이모지 사용 (외부 라이브러리 없음):

```tsx
// 카테고리별 자주 쓰는 이모지 30개 하드코딩
const EMOJI_LIST = [
  // 표정
  "😊", "😍", "🥰", "😎", "🤩", "😂", "🥹", "😭",
  // 예술
  "🎨", "🖼️", "🖌️", "✏️", "📸", "🎭", "🌈", "✨",
  // 반응
  "❤️", "🔥", "👏", "💯", "🙌", "🕊️", "💎", "⭐",
  // 기타
  "📍", "🏛️", "🎪", "🌸", "🌅", "🎶",
];
```

팝오버로 표시, 클릭 시 `onEmojiSelect(emoji)` → textarea의 커서 위치에 삽입.

### 3.4 OEmbedInput + OEmbedCard

```tsx
// OEmbedInput: URL 입력 팝오버
interface OEmbedInputProps {
  onAdd: (data: OEmbedData) => void;
  onClose: () => void;
}

// URL 입력 → Enter → fetchOEmbed(url) → 프리뷰 표시 → "추가" 클릭

// OEmbedCard: 프리뷰 렌더링
interface OEmbedCardProps {
  data: OEmbedData;
  onRemove: () => void;
}
```

**OEmbedData 타입**:
```typescript
type OEmbedData = {
  provider: "youtube" | "instagram" | "tiktok" | "x";
  title: string;
  thumbnail_url: string | null;
  author_name: string | null;
  url: string;
};
```

플랫폼별 카드 스타일:
- YouTube: 썸네일 16:9 + 제목 + 채널명 + ▶ 오버레이
- Instagram: 정사각 썸네일 + 캡션 일부 + @author
- TikTok: 세로 썸네일 + 제목 + @author
- X: 텍스트 인용 카드 + @handle + 날짜

### 3.5 SchedulePicker

```tsx
interface SchedulePickerProps {
  value: Date | null;
  onChange: (date: Date | null) => void;
}
```

네이티브 `<input type="datetime-local">` 사용 (외부 라이브러리 없음).
- 최소 시간: 현재 시간 + 5분
- "예약 취소" 버튼 → `null`로 리셋
- 표시: "2026-04-15 15:00에 공개 예정" 배너

### 3.6 TagAutocomplete

```tsx
interface TagAutocompleteProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
}
```

동작:
1. 입력 필드에 타이핑
2. Enter 또는 `,` 입력 → 태그 칩으로 변환
3. 타이핑 중 `fetchTagSuggestions(query)` 호출 (debounce 300ms)
4. 드롭다운에서 선택 또는 새 태그 생성
5. 태그 칩에 X 버튼 → 삭제

### 3.7 MediaPreviewList

기존의 단순 URL 목록을 **시각적 프리뷰 그리드**로 교체:

```
┌────────┐ ┌────────┐ ┌────────┐
│  이미지  │ │  영상   │ │  GIF   │
│ [✕]    │ │ [✕] ▶  │ │ [✕]    │
└────────┘ └────────┘ └────────┘
┌─────────────────────────────────┐
│ ▶ YouTube: Timelapse Painting  [✕] │
│   Maria Lima · youtube.com      │
└─────────────────────────────────┘
```

이미지: 썸네일 프리뷰 (object-fit: cover)
영상: 썸네일 + ▶ 오버레이
GIF: 자동 재생 프리뷰
oEmbed: OEmbedCard 컴포넌트

### 3.8 API 클라이언트 추가

```typescript
// lib/api.ts

export type OEmbedData = {
  provider: string;
  title: string;
  thumbnail_url: string | null;
  author_name: string | null;
  url: string;
};

export async function fetchOEmbed(url: string): Promise<OEmbedData> {
  return apiFetch<OEmbedData>(
    `/media/oembed?url=${encodeURIComponent(url)}`,
    { auth: false }
  );
}

export async function fetchTagSuggestions(
  prefix: string,
  limit = 10
): Promise<string[]> {
  return apiFetch<string[]>(
    `/posts/tags/suggest?q=${encodeURIComponent(prefix)}&limit=${limit}`,
    { auth: false }
  );
}
```

### 3.9 CreatePostInput 확장

```typescript
export type CreatePostInput = {
  // ... 기존 필드
  scheduled_at?: string;           // ISO 8601 UTC
  location_name?: string;
  location_lat?: number;
  location_lng?: number;
};
```

---

## 4. 와이어프레임

### 4.1 등록 페이지 (데스크탑)

```
┌──────────────────────────────────────────────────┐
│ ← 뒤로                         [임시저장] [등록]  │
├──────────────────────────────────────────────────┤
│                                                  │
│ ┌─ 포스트 종류 ──────────────────────────────┐   │
│ │ (● 일반 포스트)  (○ 상품 포스트)           │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ ┌─ 제목 ─────────────────────────────────────┐   │
│ │ Sunrise in Lima — 제작 과정                 │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ ┌─ 내용 ─────────────────────────────────────┐   │
│ │                                            │   │
│ │ 리마의 아침 햇살을 담은 유화입니다.        │   │
│ │ 3주에 걸쳐 완성했어요. 😊                  │   │
│ │                                            │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ ┌─ 첨부 미디어 ──────────────────────────────┐   │
│ │ ┌──────┐ ┌──────┐ ┌──────┐                │   │
│ │ │ 🖼    │ │ 📹 ▶ │ │ GIF  │                │   │
│ │ │ [✕]  │ │ [✕]  │ │ [✕]  │                │   │
│ │ └──────┘ └──────┘ └──────┘                │   │
│ │                                            │   │
│ │ ┌─ YouTube ────────────────────────────┐   │   │
│ │ │ ▶ Sunrise Timelapse  [✕]            │   │   │
│ │ │   Maria Lima · youtube.com           │   │   │
│ │ └──────────────────────────────────────┘   │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ ┌─ 미디어 툴바 ──────────────────────────────┐   │
│ │ [🖼] [GIF] [😊] [🔗] [📍] [⏰] [#]       │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ 📍 서울시립미술관 · 서울 중구 덕수궁길 61        │
│ ⏰ 2026-04-15 15:00에 공개 예정                   │
│                                                  │
│ ┌─ 태그 ─────────────────────────────────────┐   │
│ │ [oil] [landscape] [lima] [+ 태그 추가]     │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ ┌─ 상품 정보 (상품 포스트일 때만) ───────────┐   │
│ │ 장르: painting  크기: 50x70cm              │   │
│ │ 매체: Oil on canvas  연도: 2026            │   │
│ │ ☑ 경매  ☐ 즉시구매                         │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 4.2 미디어 툴바 아이콘 (신규 SVG)

기존 `icons.tsx`에 추가:

| 이름 | 용도 | SVG |
|---|---|---|
| `ImageIcon` | 이미지/영상 | 산+태양 (기존 없으면 추가) |
| `GifIcon` | GIF | "GIF" 텍스트 박스 |
| `SmileIcon` | 이모지 | 웃는 얼굴 |
| `LinkIcon` | 임베드 | 체인 링크 |
| `MapPinIcon` | 위치 | 핀 마커 |
| `ClockIcon` | 스케줄 | 시계 |
| `HashIcon` | 태그 | # 기호 |

---

## 5. 구현 순서

| Step | 작업 | 파일 | 의존성 |
|---|---|---|---|
| 1 | DB 마이그레이션 (scheduled_at, location_*) | `alembic/versions/0011_*` | 없음 |
| 2 | Post 모델 + 스키마 확장 | `models/post.py`, `schemas/post.py` | Step 1 |
| 3 | `POST /posts` 핸들러 수정 (신규 필드 저장) | `api/posts.py` | Step 2 |
| 4 | `GET /posts/tags/suggest` 엔드포인트 | `api/posts.py` | 없음 |
| 5 | `GET /media/oembed` 엔드포인트 | `api/media.py` | 없음 |
| 6 | 스케줄 크론잡 (`publish_scheduled_posts`) | `tasks/scheduler.py` | Step 2 |
| 7 | 프론트 아이콘 추가 (7개) | `components/icons.tsx` | 없음 |
| 8 | `fetchOEmbed`, `fetchTagSuggestions` API 클라이언트 | `lib/api.ts` | Step 4, 5 |
| 9 | `EmojiPicker` 컴포넌트 | `components/post-editor/EmojiPicker.tsx` | 없음 |
| 10 | `OEmbedInput` + `OEmbedCard` | `components/post-editor/OEmbed*.tsx` | Step 8 |
| 11 | `SchedulePicker` 컴포넌트 | `components/post-editor/SchedulePicker.tsx` | 없음 |
| 12 | `LocationPicker` 컴포넌트 | `components/post-editor/LocationPicker.tsx` | Kakao API 키 |
| 13 | `TagAutocomplete` 컴포넌트 | `components/post-editor/TagAutocomplete.tsx` | Step 8 |
| 14 | `MediaPreviewList` 컴포넌트 | `components/post-editor/MediaPreviewList.tsx` | 없음 |
| 15 | `MediaToolbar` 통합 컴포넌트 | `components/post-editor/MediaToolbar.tsx` | Step 9~14 |
| 16 | `posts/new/page.tsx` 리팩터 | `app/posts/new/page.tsx` | Step 15 |
| 17 | PostOut 응답에 신규 필드 포함 + 상세 페이지 표시 | `api/posts.py`, 프론트 | Step 3 |

**병렬화 가능**:
- Step 1~6 (백엔드) ∥ Step 7~14 (프론트 컴포넌트)
- Step 15~17은 순차

---

## 6. 테스트 관점

### 백엔드
- `POST /posts` + `scheduled_at` → status = `scheduled` 확인
- `GET /posts/tags/suggest?q=pai` → `["painting"]` 반환
- `GET /media/oembed?url=https://youtube.com/watch?v=xxx` → 메타데이터 반환
- `GET /media/oembed?url=https://unknown.com` → 422 에러
- oEmbed 외부 API 타임아웃 → fallback 링크 카드
- 스케줄 크론잡: scheduled_at 과거 포스트 → published 전환

### 프론트엔드
- 이미지/영상/GIF 업로드 → 프리뷰 표시
- 이모지 피커 → textarea 커서 위치에 삽입
- YouTube URL 입력 → 프리뷰 카드 렌더링
- 위치 검색 → 장소 선택 → 태그 표시
- 스케줄 설정 → "예약 공개" 배너
- 태그 입력 → 자동완성 드롭다운
- 미디어 프리뷰 그리드 + 삭제 버튼

---

## 7. 다음 단계

✅ `/pdca do domo-post-editor`로 구현 착수 → Step 1부터 순차 진행
