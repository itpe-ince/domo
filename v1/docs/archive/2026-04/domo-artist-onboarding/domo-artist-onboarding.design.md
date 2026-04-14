# Design — Domo Artist Onboarding Phase 1 (프로필 필드 확장)

**Feature**: domo-artist-onboarding (Phase 1)
**Created**: 2026-04-14
**Phase**: Design
**Plan Reference**: [domo-artist-onboarding.plan.md](../../01-plan/features/domo-artist-onboarding.plan.md)

---

## 1. Data Model 변경

### 1.1 artist_applications 테이블 확장

```sql
-- 신규 필드
ALTER TABLE artist_applications ADD COLUMN department VARCHAR(100);
ALTER TABLE artist_applications ADD COLUMN graduation_year INT;
ALTER TABLE artist_applications ADD COLUMN is_enrolled BOOLEAN DEFAULT TRUE;
ALTER TABLE artist_applications ADD COLUMN genre_tags TEXT[];
ALTER TABLE artist_applications ADD COLUMN enrollment_proof_url TEXT;
ALTER TABLE artist_applications ADD COLUMN representative_works JSONB;
ALTER TABLE artist_applications ADD COLUMN exhibitions JSONB;
ALTER TABLE artist_applications ADD COLUMN awards JSONB;
```

### 1.2 artist_profiles 테이블 확장

```sql
ALTER TABLE artist_profiles ADD COLUMN department VARCHAR(100);
ALTER TABLE artist_profiles ADD COLUMN graduation_year INT;
ALTER TABLE artist_profiles ADD COLUMN is_enrolled BOOLEAN DEFAULT TRUE;
ALTER TABLE artist_profiles ADD COLUMN genre_tags TEXT[];
ALTER TABLE artist_profiles ADD COLUMN exhibitions JSONB;
ALTER TABLE artist_profiles ADD COLUMN awards JSONB;
ALTER TABLE artist_profiles ADD COLUMN representative_works JSONB;
```

### 1.3 badge_level 명칭 변경

| 이전 | 이후 | 표시 |
|---|---|---|
| `emerging` | `student` | 🎓 학생 작가 |
| `featured` | `emerging` | ✨ 신진 작가 |
| `popular` | `recommended` | 🕊 추천 작가 |
| `master` | `popular` | 🔥 인기 작가 |

기존 데이터 마이그레이션: `UPDATE artist_profiles SET badge_level = 'student' WHERE badge_level = 'emerging'`

### 1.4 JSONB 필드 구조

**representative_works**:
```json
[
  {
    "title": "Sunrise in Lima",
    "description": "리마의 아침 햇살을 담은 유화",
    "image_url": "https://...",
    "dimensions": "50x70cm",
    "medium": "Oil on canvas",
    "year": 2026
  }
]
```

**exhibitions**:
```json
[
  { "title": "서울시립미술관 신진작가전", "year": 2025, "description": "단체전" }
]
```

**awards**:
```json
[
  { "title": "대한민국 미술대전 입선", "year": 2025, "description": "" }
]
```

### 1.5 Alembic 마이그레이션

```
0013_artist_onboarding.py
  - artist_applications: 8개 컬럼 추가
  - artist_profiles: 7개 컬럼 추가
  - badge_level 데이터 마이그레이션 (emerging → student)
```

---

## 2. API 설계

### 2.1 POST /artists/apply 확장

```python
class RepresentativeWork(BaseModel):
    title: str
    description: str | None = None
    image_url: str
    dimensions: str | None = None
    medium: str | None = None
    year: int | None = None

class ExhibitionEntry(BaseModel):
    title: str
    year: int | None = None
    description: str | None = None

class ArtistApplicationCreate(BaseModel):
    # 기존 (유지)
    school: str                                    # 필수로 변경
    portfolio_urls: list[str] | None = None
    intro_video_url: str | None = None
    statement: str = Field(..., max_length=200)     # 200자 제한, 필수

    # 신규
    department: str                                 # 학과 (필수)
    graduation_year: int                            # 졸업연도 (필수)
    is_enrolled: bool = True                        # 재학 중 여부
    genre_tags: list[str] = Field(..., min_length=1, max_length=5)  # 1~5개
    enrollment_proof_url: str                       # 증빙 파일 URL (필수)
    representative_works: list[RepresentativeWork] = Field(
        ..., min_length=3, max_length=6             # 대표 작품 3~6개 (필수)
    )
    exhibitions: list[ExhibitionEntry] | None = None  # 전시 이력 (선택)
    awards: list[ExhibitionEntry] | None = None       # 수상 이력 (선택)

    # 폐기
    # sample_images → representative_works로 대체
```

### 2.2 ArtistApplicationOut 확장

기존 필드 + 신규 필드 모두 포함. `sample_images`는 호환성 유지를 위해 잠시 남기되 deprecated 표시.

### 2.3 관리자 승인 시 ArtistProfile 생성 변경

`admin.py:approve_application`에서 신규 필드를 ArtistProfile로 복사:

```python
ArtistProfile(
    # 기존
    user_id=user.id,
    application_id=app_obj.id,
    verified_by=admin.id,
    school=app_obj.school,
    intro_video_url=app_obj.intro_video_url,
    portfolio_urls=app_obj.portfolio_urls,
    statement=app_obj.statement,

    # 신규
    department=app_obj.department,
    graduation_year=app_obj.graduation_year,
    is_enrolled=app_obj.is_enrolled,
    genre_tags=app_obj.genre_tags,
    representative_works=app_obj.representative_works,
    exhibitions=app_obj.exhibitions,
    awards=app_obj.awards,

    # 등급: 재학 중이면 student, 아니면 emerging
    badge_level="student" if app_obj.is_enrolled else "emerging",
)
```

### 2.4 GET /users/{id} 프로필 응답 확장

artist_profile 응답에 신규 필드 포함:

```json
{
  "data": {
    "id": "...",
    "display_name": "maria_lima",
    "role": "artist",
    "artist_profile": {
      "school": "Lima Art Academy",
      "department": "서양화과",
      "graduation_year": 2026,
      "is_enrolled": true,
      "genre_tags": ["painting", "oil", "landscape"],
      "badge_level": "student",
      "badge_label": "🎓 학생 작가",
      "representative_works": [...],
      "exhibitions": [...],
      "awards": [...],
      "portfolio_urls": [...],
      "intro_video_url": "...",
      "statement": "..."
    }
  }
}
```

### 2.5 badge_label 매핑 (프론트/백엔드 공통)

```python
BADGE_LABELS = {
    "student": "🎓 학생 작가",
    "emerging": "✨ 신진 작가",
    "recommended": "🕊 추천 작가",
    "popular": "🔥 인기 작가",
}
```

---

## 3. 프론트엔드 컴포넌트 설계

### 3.1 컴포넌트 계층

```
app/artists/apply/
  page.tsx                    # 리팩터: 4단계 위저드

components/artist-apply/
  StepBasicInfo.tsx            # Step 1: 기본 정보 (학교/학과/졸업/장르)
  StepWorks.tsx                # Step 2: 대표 작품 3~6개
  StepPortfolio.tsx            # Step 3: 자기소개 + 증빙 + 포트폴리오
  StepHistory.tsx              # Step 4: 전시/수상 이력 (선택)
  WorkCard.tsx                 # 개별 작품 입력 카드
  HistoryEntry.tsx             # 전시/수상 입력 행
```

### 3.2 위저드 상태 관리

```typescript
type WizardStep = 1 | 2 | 3 | 4;

// 각 Step 컴포넌트는 props로 데이터와 setter를 받음
interface StepProps {
  data: ApplicationFormData;
  onChange: (partial: Partial<ApplicationFormData>) => void;
  onNext: () => void;
  onPrev?: () => void;
}

type ApplicationFormData = {
  // Step 1
  school: string;
  department: string;
  graduation_year: number;
  is_enrolled: boolean;
  genre_tags: string[];

  // Step 2
  representative_works: RepresentativeWork[];

  // Step 3
  statement: string;
  enrollment_proof_url: string;
  portfolio_urls: string[];
  intro_video_url: string;

  // Step 4
  exhibitions: HistoryItem[];
  awards: HistoryItem[];
};
```

### 3.3 Step 1 — 기본 정보

```
┌──────────────────────────────────────┐
│ 작가 심사 신청  (Step 1/4)           │
│ ● ○ ○ ○  기본 정보                   │
├──────────────────────────────────────┤
│                                      │
│ 소속 학교 *       [              ]   │
│ 학과 *            [              ]   │
│ 졸업(예정) 연도 * [2026  ▼]          │
│ ☑ 현재 재학 중                       │
│                                      │
│ 작업 장르/스타일 * (1~5개 선택)      │
│ [painting] [oil] [landscape] [+]     │
│                                      │
│                          [다음 →]    │
└──────────────────────────────────────┘
```

장르 태그: 기존 GENRES 상수 + 자유 입력 허용

### 3.4 Step 2 — 대표 작품

```
┌──────────────────────────────────────┐
│ Step 2/4 — 대표 작품 (3~6개) *       │
│ ○ ● ○ ○                             │
├──────────────────────────────────────┤
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ ┌──────┐  작품명 * [          ] │ │
│ │ │ 이미지│  설명   [          ]  │ │
│ │ │ 업로드│  크기   [50x70cm   ]  │ │
│ │ │ [📷] │  매체   [Oil on..  ]  │ │
│ │ └──────┘  연도   [2026      ]  │ │
│ │                          [삭제] │ │
│ └──────────────────────────────────┘ │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ 작품 2 ...                       │ │
│ └──────────────────────────────────┘ │
│                                      │
│ [+ 작품 추가] (최대 6개)             │
│                                      │
│                 [← 이전] [다음 →]    │
└──────────────────────────────────────┘
```

이미지 업로드: 기존 `uploadMediaFile` 재사용

### 3.5 Step 3 — 포트폴리오 & 증빙

```
┌──────────────────────────────────────┐
│ Step 3/4 — 포트폴리오                │
│ ○ ○ ● ○                             │
├──────────────────────────────────────┤
│                                      │
│ 자기소개 * (200자 이내)              │
│ [                              ]     │
│ [                        142/200]    │
│                                      │
│ 재학/졸업 증빙 *                     │
│ [📎 파일 선택]                       │
│ ✓ 재학증명서.pdf (128KB)             │
│                                      │
│ 포트폴리오 URL (줄바꿈 구분)         │
│ [                              ]     │
│                                      │
│ 소개 영상 URL (선택)                 │
│ [https://youtube.com/...       ]     │
│                                      │
│                 [← 이전] [다음 →]    │
└──────────────────────────────────────┘
```

증빙 업로드: `uploadMediaFile` 재사용, 확장자 .pdf/.jpg/.png 허용

### 3.6 Step 4 — 이력 (선택)

```
┌──────────────────────────────────────┐
│ Step 4/4 — 이력 (선택 사항)          │
│ ○ ○ ○ ●                             │
├──────────────────────────────────────┤
│                                      │
│ 전시 이력                            │
│ ┌────────────────────────────────┐   │
│ │ 전시명  [                    ] │   │
│ │ 연도    [2025] 설명 [       ] │   │
│ │                        [삭제] │   │
│ └────────────────────────────────┘   │
│ [+ 전시 추가]                        │
│                                      │
│ 수상 이력                            │
│ [+ 수상 추가]                        │
│                                      │
│              [← 이전] [심사 신청 →]  │
└──────────────────────────────────────┘
```

### 3.7 관리자 심사 화면 확장

`/admin/applications` 에서 확장된 필드 표시:
- 학교/학과/졸업연도/재학여부
- 장르 태그 칩
- 대표 작품 이미지 그리드 (클릭 확대)
- 증빙 파일 다운로드 링크
- 전시/수상 이력 리스트

---

## 4. API 클라이언트 변경

```typescript
// lib/api.ts

export type RepresentativeWork = {
  title: string;
  description?: string;
  image_url: string;
  dimensions?: string;
  medium?: string;
  year?: number;
};

export type HistoryEntry = {
  title: string;
  year?: number;
  description?: string;
};

export type ApplyArtistInput = {
  school: string;
  department: string;
  graduation_year: number;
  is_enrolled: boolean;
  genre_tags: string[];
  statement: string;
  enrollment_proof_url: string;
  representative_works: RepresentativeWork[];
  portfolio_urls?: string[];
  intro_video_url?: string;
  exhibitions?: HistoryEntry[];
  awards?: HistoryEntry[];
};
```

---

## 5. 구현 순서

| Step | 작업 | 파일 | 의존성 |
|---|---|---|---|
| 1 | Alembic 마이그레이션 (0013) | `alembic/versions/` | 없음 |
| 2 | ArtistApplication 모델 확장 | `models/user.py` | Step 1 |
| 3 | ArtistProfile 모델 확장 | `models/user.py` | Step 1 |
| 4 | 스키마 확장 (Pydantic) | `schemas/artist.py` | Step 2, 3 |
| 5 | POST /artists/apply 핸들러 수정 | `api/artists.py` | Step 4 |
| 6 | 관리자 승인 로직 수정 | `api/admin.py` | Step 4 |
| 7 | GET /users/{id} 프로필 응답 확장 | `api/users.py` | Step 3 |
| 8 | API 클라이언트 타입 수정 | `lib/api.ts` | Step 4 |
| 9 | StepBasicInfo 컴포넌트 | `components/artist-apply/` | 없음 |
| 10 | WorkCard + StepWorks 컴포넌트 | `components/artist-apply/` | 없음 |
| 11 | StepPortfolio 컴포넌트 | `components/artist-apply/` | 없음 |
| 12 | HistoryEntry + StepHistory 컴포넌트 | `components/artist-apply/` | 없음 |
| 13 | 신청 폼 페이지 리팩터 (위저드) | `app/artists/apply/page.tsx` | Step 9~12 |
| 14 | 관리자 심사 화면 확장 | `app/admin/applications/page.tsx` | Step 7 |

**병렬화**: Step 1~7 (백엔드) ∥ Step 9~12 (프론트 컴포넌트)

---

## 6. 테스트 관점

### 백엔드
- `POST /artists/apply` — 신규 필드 모두 저장 확인
- `statement` 201자 → 422 에러
- `representative_works` 2개 → 422 (최소 3개)
- `genre_tags` 6개 → 422 (최대 5개)
- `enrollment_proof_url` 누락 → 422
- 관리자 승인 시 ArtistProfile에 신규 필드 복사 확인
- badge_level: `is_enrolled=true` → `student`, `false` → `emerging`

### 프론트엔드
- 4단계 위저드 이전/다음 네비게이션
- 대표 작품 이미지 업로드 → URL 저장
- 증빙 파일 업로드 (PDF/JPG/PNG)
- 장르 태그 추가/삭제 (1~5개 제한)
- 자기소개 200자 카운터 + 초과 방지
- 전시/수상 동적 추가/삭제
- Step 간 데이터 유지 (브라우저 뒤로가기에도)

---

## 7. 다음 단계

✅ `/pdca do domo-artist-onboarding`으로 Phase 1 구현 착수
