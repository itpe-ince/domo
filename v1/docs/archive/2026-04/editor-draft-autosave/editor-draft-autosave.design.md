---
template: design
version: 1.0
feature: editor-draft-autosave
date: 2026-04-30
author: itpe-ince (Claude Opus 4.7 + bkit frontend-architect + bkit:bkend-expert agents 병렬 작성)
project: domo
project_version: v1
status: Approved (Design) — Do 진입 가능
parent_plan: editor-draft-autosave.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
oq_resolved: 2026-04-30
---

# editor-draft-autosave Design Document

> **Summary**: 에디터 임시저장을 dual-layer (localStorage 자동 + 서버 draft 명시)로 구현. Backend는 별도 router `/v1/posts/drafts` 신설 + 4개 endpoint, Frontend는 `useDraftAutosave` hook + `DraftRestoreDialog` + `/posts/drafts` 페이지.
>
> **Approach**: Plan §10 OQ 5개 모두 권장 default 채택. Backend `Post.status='draft'` enum이 이미 지원되어 DB 마이그레이션 0개 (인덱스 1개 추가 권장).

---

## 0. Summary of Sub-Agent Designs

본 design 문서는 두 sub-agent의 병렬 결과를 통합:
- **Frontend**: bkit:frontend-architect — `useDraftAutosave` hook, `DraftRestoreDialog`, `/posts/drafts` page, Sidebar 메뉴, i18n 5 locale
- **Backend**: bkit:bkend-expert — `/v1/posts/drafts` 신규 router, Pydantic schemas, partial index, cleanup job

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend                                                         │
│                                                                  │
│  posts/new/page.tsx (CreatePostPageInner)                       │
│    │                                                             │
│    ├── useDraftAutosave(formState, options)                     │
│    │     ├── localStorage write (debounced 2s)  ← Q-3           │
│    │     ├── onBeforeUnload flush                                │
│    │     └── saveToServer() → POST /posts/drafts                 │
│    │                                                             │
│    ├── DraftRestoreDialog (Q-5: 더 최신 timestamp 우선)          │
│    │                                                             │
│    └── header: AutosaveIndicator + "임시저장" btn + drafts link  │
│                                                                  │
│  posts/drafts/page.tsx (신규) ─ listDrafts + DraftCard 목록      │
│  Sidebar.tsx UserDropdown ─ "임시저장 목록" 메뉴 추가 (Q-2)       │
└────────────────────────────┬────────────────────────────────────┘
                             │ apiFetch
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend                                                          │
│                                                                  │
│  /v1/posts/drafts router (신규 — api/drafts.py)                  │
│    POST    /              upsert_draft  (draft_id 있으면 update) │
│    GET     /              list_drafts   (사용자 본인만)           │
│    GET     /{draft_id}    get_draft     (소유자 검증, 404 if not)│
│    DELETE  /{draft_id}    delete_draft  (hard delete + cascade)  │
│                                                                  │
│  /v1/posts (기존 — api/posts.py:200)                             │
│    POST에 from_draft_id 추가 → 발행 후 같은 트랜잭션에서 draft 삭제│
│                                                                  │
│  models/post.py — Post.status='draft' 이미 지원 ✓                │
│  alembic/versions/0035_draft_limit_index.py (partial index)      │
│  services/draft_cleanup_jobs.py (90일 미수정 자동 삭제)          │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 흐름 (dual-layer)**

```
사용자 입력
   │
   ├─ 2초 debounce ─▶ localStorage[domo-draft-{userId}-{new|draftId}]
   │                  (비로그인도 동작, 오프라인 안전망)
   │
   └─ "임시저장" 클릭 ─▶ POST /v1/posts/drafts ─▶ 서버 draft (status='draft')

페이지 재진입
  hasLocalDraft || ?draft=id ──▶ DraftRestoreDialog → 폼 자동 채우기

발행 성공
  POST /v1/posts (from_draft_id 포함) ──▶ 같은 트랜잭션에서 draft 삭제
  + clearDraft() ──▶ localStorage.removeItem
```

---

## 2. Backend Design

### 2.1 Architecture Decision

**별도 router `/v1/posts/drafts` 신규 생성** (기존 `POST /v1/posts` 확장 X). 근거:

1. 기존 `create_post` (`posts.py:200-287`)는 status를 내부 결정. `status="draft"` 파라미터 끼워넣기 시 분기 복잡화
2. Draft는 "본인만 CRUD" 권한 모델 — 발행 포스트와 근본적으로 다름
3. `GET /v1/posts/drafts` 목록은 public posts API와 완전 분리 필요
4. Schema 분리로 product 검증 완화 정책 깔끔

**신규 파일:**
- `app/schemas/draft.py` — Pydantic schemas
- `app/api/drafts.py` — router + 4 endpoints
- `app/services/draft_cleanup_jobs.py` — 90일 자동 cleanup
- `alembic/versions/0035_draft_limit_index.py` — partial index
- `backend/scripts/smoke_test_drafts.sh` — smoke test

### 2.2 DB Schema

**컬럼 추가 0개.** 근거:
- `Post.status='draft'` 이미 지원 ([post.py:43-44](../../../backend/app/models/post.py#L43))
- `Post.updated_at`은 `onupdate=func.now()` 설정됨 ([post.py:60-62](../../../backend/app/models/post.py#L60)) → Q-5 timestamp 비교에 재활용
- `draft_updated_at` 별도 컬럼 불필요

**인덱스 1개 추가 권장:**

`alembic/versions/0035_draft_limit_index.py`
```python
op.create_index(
    "ix_posts_author_status_updated",
    "posts",
    ["author_id", "status", "updated_at"],
    postgresql_where="status = 'draft'",  # partial index
)
```
사용자별 draft 목록 + updated_at 정렬 쿼리를 index-only scan으로 처리. Draft가 아닌 row는 인덱스 미포함 → 크기 최소화.

### 2.3 API Endpoints

#### `POST /v1/posts/drafts` — upsert
```python
@router.post("")
async def upsert_draft(
    body: DraftUpsertBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. body.draft_id 있으면 _get_draft_or_404 → update
    # 2. 없으면 사용자의 draft count 확인
    #    - >= 20개면 가장 오래된 draft 자동 삭제 (B-6 결정)
    #    - 신규 생성: status='draft', digital_art_check='not_required'
    # 3. media: 기존 MediaAsset 전체 삭제 + 새로 삽입 (idempotent)
    # 4. product: type='product'이고 body.product 있으면 ProductPost upsert
    #    type=product 검증은 §2.5 참조 (Q-B1 미해결)
    # 5. commit, return DraftView
```
- Auth required
- Response: `{ "data": DraftView, "meta": { "auto_deleted_draft_id"?: UUID } }`

#### `GET /v1/posts/drafts` — list
```python
@router.get("")
async def list_drafts(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # SELECT WHERE author_id=user.id AND status='draft'
    # ORDER BY updated_at DESC
    # selectinload(Post.media), selectinload(Post.product)
```
- Response: `{ "data": [DraftView], "total": int, "limit": int, "offset": int }`

#### `GET /v1/posts/drafts/{draft_id}` — single
```python
@router.get("/{draft_id}")
async def get_draft(draft_id: UUID, user: User = ..., db: ... = ...):
    post = await _get_draft_or_404(db, draft_id, user.id)
    return {"data": DraftView.model_validate(post).model_dump(mode="json")}
```
- 소유자 불일치 → **404** (403 대신 — enumeration 공격 방지)

#### `DELETE /v1/posts/drafts/{draft_id}` — hard delete
```python
@router.delete("/{draft_id}")
async def delete_draft(draft_id: UUID, ...):
    post = await _get_draft_or_404(db, draft_id, user.id)
    await db.delete(post)  # MediaAsset cascade 자동 삭제
    await db.commit()
    return {"data": {"deleted": True, "id": str(draft_id)}}
```

### 2.4 발행 흐름 변경 (FR-5 자동 삭제)

**옵션 B 채택**: `from_draft_id` 파라미터 + 동일 트랜잭션 삭제. Race condition 방지.

`PostCreate` schema (`schemas/post.py`)에 추가:
```python
from_draft_id: UUID | None = None
```

`create_post` 핸들러 (`posts.py:283` 부근):
```python
# await db.commit() 직전
if body.from_draft_id:
    draft = await db.get(Post, body.from_draft_id)
    if draft and draft.author_id == user.id and draft.status == "draft":
        await db.delete(draft)  # MediaAsset cascade
# await db.commit()  ← 기존 commit이 draft 삭제까지 atomic
```

### 2.5 Validation 비교

| 항목 | Published (`create_post`) | Draft (`upsert_draft`) |
|------|--------------------------|------------------------|
| `title` | Optional (현재 schema) | Optional + 빈 문자열 허용 |
| `content` | Optional | Optional + 빈 문자열 허용 |
| `type` | required | required |
| `product` 필드 | type='product'면 required | Optional |
| **artist 권한 (type='product')** | artist/admin만 | **Q-B1 미해결** — 신규 생성만 검증? draft_id 있는 update는 skip? |
| `digital_art_check` | 미디어 유형으로 자동 결정 | 항상 `'not_required'` |

### 2.6 Pagination & Limit

| 항목 | 값 | 근거 |
|------|----|------|
| 기본 limit | 20 | 기존 posts API 일관성 |
| 최대 limit | 50 | 사용 빈도 낮음 |
| 사용자당 최대 draft | 20개 | NFR-4 |
| **초과 시 정책** | **자동 삭제 (가장 오래된 것)** | 자동저장 침묵 실패 방지 — 응답 `meta.auto_deleted_draft_id` 포함 |

### 2.7 Pydantic Schemas (`app/schemas/draft.py`)

```python
class DraftUpsertBody(BaseModel):
    draft_id: UUID | None = None
    type: str = "general"
    title: str | None = None
    content: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    language: str = "ko"
    media: list[MediaAssetIn] = []
    product: ProductPostIn | None = None
    scheduled_at: datetime | None = None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None

class DraftView(BaseModel):
    id: UUID
    type: str
    title: str | None = None
    content: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    language: str
    media: list[MediaAssetOut] = []
    product: ProductPostOut | None = None
    scheduled_at: datetime | None = None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    created_at: datetime
    updated_at: datetime  # Q-5 충돌 해결 timestamp
    class Config:
        from_attributes = True

class DraftListResponse(BaseModel):
    data: list[DraftView]
    total: int
    limit: int
    offset: int
```

### 2.8 Authorization

소유자 검증 helper:
```python
async def _get_draft_or_404(db, draft_id, user_id) -> Post:
    result = await db.execute(
        select(Post)
        .where(Post.id == draft_id, Post.status == "draft")
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    post = result.scalar_one_or_none()
    if not post or post.author_id != user_id:
        raise ApiError("NOT_FOUND", "Draft not found", http_status=404)
    return post
```

403 대신 404 반환 — draft ID enumeration 공격 방지.

### 2.9 Auto-cleanup (NFR-4 + Plan R-3)

**본 PDCA scope에 포함.** 미래로 미루면 우선순위 낮아질 위험.

`app/services/draft_cleanup_jobs.py` (신규):
```python
DRAFT_TTL_DAYS = 90

async def cleanup_stale_drafts(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DRAFT_TTL_DAYS)
    result = await db.execute(
        delete(Post)
        .where(Post.status == "draft", Post.updated_at < cutoff)
        .returning(Post.id)
    )
    deleted = len(result.fetchall())
    await db.commit()
    return deleted
```

기존 `services/community_jobs.py`, `webhook_cleanup_jobs.py` 패턴 따름. 일 1회 schedule_jobs.py에 등록.

---

## 3. Frontend Design

### 3.1 `useDraftAutosave` Hook (`lib/hooks/useDraftAutosave.ts`, 신규)

```ts
export type DraftState = {
  type: "general" | "product";
  title: string; content: string; genre: string; tags: string[];
  media: CreatePostMedia[]; embeds: OEmbedData[];
  isMakingVideo: boolean; scheduledAt: string;
  locationName: string; locationLat: number | null; locationLng: number | null;
  isAuction: boolean; isBuyNow: boolean; buyNowPrice: number | "";
  dimensions: string; medium: string; year: number | "";
};

export interface UseDraftAutosaveOptions {
  formState: DraftState;
  storageKey: string;        // 'domo-draft-{userId}-new' | '-{userId}-{draftId}' | '-guest-new'
  debounceMs?: number;       // default: 2000 (Q-3)
  draftId?: string;
  enabled?: boolean;
}

export interface UseDraftAutosaveReturn {
  status: "idle" | "saving" | "saved" | "error";
  lastSavedAt: Date | null;
  saveToServer: () => Promise<void>;   // "임시저장" 버튼용
  clearDraft: () => void;              // 발행 후 호출 (Q-4)
  hasLocalDraft: boolean;
  loadLocalDraft: () => DraftState | null;
  discardLocalDraft: () => void;
}
```

**핵심 동작:**
- localStorage debounced write — `setTimeout(write, 2000)` + cleanup
- `beforeunload` 이벤트 → 즉시 flush (페이지 이탈 손실 방지)
- `saveToServer()` → `POST /v1/posts/drafts` (draft_id 있으면 upsert)
- `clearDraft()` → localStorage clear + currentDraftId 초기화 (서버 삭제는 호출부 책임)
- 비로그인도 enabled=true (guest key 사용 후 로그인 시 이전)

**localStorage payload:**
```ts
interface StoredDraft {
  state: DraftState;
  savedAt: string;  // ISO 8601 — Q-5 timestamp 비교용
}
```

**Storage key 전략:**

| 컨텍스트 | key |
|----------|-----|
| 신규 작성 (로그인) | `domo-draft-{me.id}-new` |
| 이어쓰기 (`?draft=xxx`) | `domo-draft-{me.id}-{draftId}` |
| 비로그인 | `domo-draft-guest-new` |

### 3.2 `DraftRestoreDialog` (`components/DraftRestoreDialog.tsx`, 신규)

```ts
interface DraftRestoreDialogProps {
  open: boolean;
  localDraft: { state: DraftState; savedAt: string } | null;
  serverDraft: { state: DraftState; savedAt: string; id: string } | null;
  onRestore: (draft: DraftState, sourceId?: string) => void;
  onDiscard: () => void;       // localStorage만 삭제
  onDiscardAll: () => void;    // localStorage + 서버 draft 둘 다
}
```

**Q-5 결정 로직:** localDraft + serverDraft 모두 존재 시
- 더 최신 timestamp → "이어쓰기 (권장)" default focus
- 더 오래된 것 → "이전 버전 복원" 보조 버튼
- 하나만 있으면 → 단순 2-action

**UI:**
```
┌──────────────────────────────────────────┐
│  임시저장된 내용 복원                        │
│  이전에 작성하던 내용이 있습니다.              │
│                                          │
│  [더 최신] 로컬 저장 · 3분 전              │
│  [이전] 서버 저장 · 2026-04-28 오전 10:20  │
│                                          │
│  [이어쓰기 (권장)]  [이전 버전 복원]  [새로 작성] │
│                              [둘 다 삭제]  │
└──────────────────────────────────────────┘
```

기존 `LoginModal.tsx` 패턴 (`fixed inset-0 z-50` div + Backdrop) 사용. 외부 라이브러리 X.

### 3.3 `/posts/drafts` 페이지 (`app/posts/drafts/page.tsx`, 신규)

```tsx
export const dynamic = "force-dynamic";

export default function DraftsPage() {
  return <Suspense fallback={...}><DraftsPageInner /></Suspense>;
}

function DraftsPageInner() {
  // listDrafts() fetch
  // DraftCard: title || content 첫 80자 || "(제목 없음)"
  //            updated_at 상대 시간 + media[0] thumbnail
  //            type badge ("일반" | "상품")
  //            액션: "이어쓰기" → /posts/new?draft={id}, "삭제" → deleteDraft
  // 빈 상태 UI: "아직 임시저장된 글이 없습니다" + 신규 작성 CTA
  // 페이지네이션: 1차는 단순 fetch (NFR-4 max 20개), 향후 "더 보기"
}
```

### 3.4 `posts/new/page.tsx` 통합

기존 474줄 + 약 80줄 추가 예상.

**추가 import:**
```ts
import { useDraftAutosave, readLocalStorageDraft, type DraftState } from "@/lib/hooks/useDraftAutosave";
import { getDraft, saveDraft, deleteDraft } from "@/lib/api";
import { DraftRestoreDialog } from "@/components/DraftRestoreDialog";
```

**추가 state:**
```ts
const draftParam = searchParams.get("draft");
const [showRestoreDialog, setShowRestoreDialog] = useState(false);
const [serverDraftForRestore, setServerDraftForRestore] = useState<...>(null);
const [currentDraftId, setCurrentDraftId] = useState<string | undefined>(draftParam ?? undefined);
```

**hook 호출:**
```ts
const formState: DraftState = { type, title, content, ... };
const storageKey = me ? `domo-draft-${me.id}-${draftParam ?? "new"}` : "domo-draft-guest-new";
const { status: draftStatus, lastSavedAt, saveToServer, clearDraft, ... } = useDraftAutosave({
  formState, storageKey, debounceMs: 2000, draftId: currentDraftId,
});
```

**복원 다이얼로그 트리거 useEffect:**
```ts
useEffect(() => {
  if (meLoading) return;
  const local = readLocalStorageDraft(storageKey);
  if (!local && !draftParam) return;
  if (draftParam) {
    getDraft(draftParam).then(d => {
      setServerDraftForRestore({ state: buildDraftState(d), savedAt: d.updated_at, id: d.id });
      setShowRestoreDialog(true);
    }).catch(() => { if (local) setShowRestoreDialog(true); });
  } else {
    setShowRestoreDialog(true);
  }
}, [meLoading, storageKey, draftParam]);
```

**handleSubmit 수정 (발행 성공 후 — Q-4):**
```ts
// router.push 전:
clearDraft();
// from_draft_id는 createPost payload에 currentDraftId 포함시켜 전달
// 백엔드가 같은 트랜잭션에서 삭제 (B-4)
```

**헤더 영역 변경 (L262~275 sticky header):**
- 좌측: `<h1>제목</h1>` + AutosaveIndicator
- 우측 그룹:
  - "임시저장 목록" Link → `/posts/drafts` (Q-2)
  - "임시저장" button → `saveToServer()` (Q-1)
  - 기존 "등록" button

```tsx
function AutosaveIndicator({ status, lastSavedAt, t }) {
  if (status === "idle" || !lastSavedAt) return null;
  const relativeTime = formatRelativeTime(lastSavedAt);  // FQ-2
  return (
    <span className="text-xs text-text-muted">
      {status === "saving" && t("post.draft.savingIndicator")}
      {status === "saved" && `${t("post.draft.savedIndicator")} · ${relativeTime}`}
      {status === "error" && <span className="text-danger">{t("post.draft.errorIndicator")}</span>}
    </span>
  );
}
```

### 3.5 Sidebar 사용자 메뉴 변경 (`components/Sidebar.tsx`)

[Sidebar.tsx:267~282](../../../frontend/src/components/Sidebar.tsx#L267) UserDropdown 내부:

```tsx
<Link href={`/users/${me.id}`} ...>프로필</Link>

{/* NEW: 임시저장 목록 */}
<Link href="/posts/drafts" ...>
  <DraftIcon />
  <span>{t("nav.draftsList")}</span>
</Link>

<div className="border-t" />
<button onClick={handleLogout} ...>로그아웃</button>
```

**`DraftIcon` 신규 추가** (`components/icons.tsx`):
```tsx
export function DraftIcon(props) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" {...props}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeDasharray="4 2" />
      <polyline points="14 3 14 8 19 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="12" y2="17" />
    </svg>
  );
}
```

### 3.6 `lib/api.ts` 추가 함수

```ts
// ─── Draft ──────────────────────────────────────────

export type Draft = {
  id: string;
  type: "general" | "product";
  title: string | null;
  content: string | null;
  /* 기타 폼 필드 */
  updated_at: string;  // Q-5 timestamp 비교
};

export type DraftPayload = Partial<Omit<Draft, "id" | "updated_at">> & {
  draft_id?: string;  // upsert 패턴 (Backend §2.3)
};

export async function listDrafts(): Promise<Draft[]>;
export async function getDraft(id: string): Promise<Draft>;
export async function saveDraft(payload: DraftPayload): Promise<Draft>;  // upsert
export async function deleteDraft(id: string): Promise<void>;
```

**Note**: Backend가 POST upsert 단일 endpoint 채택했으므로 `patchDraft` 별도 불필요. `saveDraft({ draft_id, ...payload })` 형식으로 통일. (FQ-1 자체 해결)

### 3.7 토스트 시스템 — 미도입 (옵션 C)

**사전 조사**: 프로젝트에 토스트 없음. `package.json` 의존성 3개뿐.

**결정**: 인라인 인디케이터로 처리 (외부 의존성 추가 X).

근거:
1. 자동저장은 반복적 → 토스트 팝업은 노이즈
2. AutosaveIndicator로 상태 변화 충분 표현
3. "임시저장" 버튼 클릭 결과는 버튼 텍스트 변경(`"저장 중..." → "저장됨"`)으로 피드백
4. `DraftRestoreDialog`는 이미 모달

**오류 처리**: `draftStatus === "error"` 시 인라인 `text-danger` 표시. 중요 오류는 기존 `error` state + `<div className="card border-danger">` 패턴.

### 3.8 멀티탭 충돌 처리 (AC-7)

```ts
useEffect(() => {
  function handleStorage(e: StorageEvent) {
    if (e.key === storageKey && e.newValue && e.oldValue) {
      setMultiTabWarning(true);
    }
  }
  window.addEventListener("storage", handleStorage);
  return () => window.removeEventListener("storage", handleStorage);
}, [storageKey]);
```

경고 배너:
```tsx
{multiTabWarning && (
  <div className="bg-warning/10 border-b border-warning px-4 py-2 text-xs text-warning">
    다른 탭에서 편집 중입니다. 마지막 저장이 우선됩니다.
  </div>
)}
```

### 3.9 i18n Keys (5 locale)

`ko.json` `post` 객체에 `draft` 블록 신규 추가:
```json
"draft": {
  "saveButton": "임시저장",
  "savedIndicator": "저장됨",
  "savingIndicator": "저장 중...",
  "errorIndicator": "저장 실패",
  "lastSavedAgo": "{{time}} 전",
  "restoreDialog": {
    "title": "임시저장된 내용 복원",
    "body": "이전에 작성하던 내용이 있습니다.",
    "continue": "이어쓰기",
    "continueRecommended": "이어쓰기 (권장)",
    "restorePrevious": "이전 버전 복원",
    "discard": "새로 작성",
    "discardAll": "둘 다 삭제"
  },
  "list": {
    "title": "임시저장 목록",
    "empty": "아직 임시저장된 글이 없습니다"
  },
  "deleted": "임시저장 삭제됨"
}
```

`nav` 객체에 추가: `"draftsList": "임시저장 목록"`

5개 locale 번역 표는 frontend agent 응답 §F-9 참조 (구현 시 적용).

---

## 4. Test Specification

### 4.1 Backend Smoke Test (`backend/scripts/smoke_test_drafts.sh`)

기존 `smoke_test_role_gating.sh` 패턴 동일.

8개 시나리오:
1. 인증 없이 create → 401
2. 빈 title/content draft 생성 → 200/201
3. draft_id 포함 update → 200
4. 본인 목록 조회 → 200
5. 단건 조회 → 200
6. 다른 사용자 접근 → 404
7. 삭제 → 200
8. 삭제 후 재조회 → 404

### 4.2 Frontend Manual QA

- [ ] AC-1: F5 새로고침 → DraftRestoreDialog 표시
- [ ] AC-2: "임시저장" 버튼 → AutosaveIndicator "저장됨" + 서버 200
- [ ] AC-5: 발행 성공 → localStorage `domo-draft-*` 키 삭제 (DevTools)
- [ ] AC-6: 비로그인 탭 → localStorage 자동저장 동작
- [ ] AC-7: 두 탭 동시 편집 → 두 번째 탭에 경고 배너 표시
- [ ] Q-3 검증: 입력 후 2초 정지 시 AutosaveIndicator "저장됨" 변경
- [ ] Q-5 검증: 로컬 5분 전, 서버 1시간 전 → 로컬이 default focus

---

## 5. Implementation Order

**Backend (병렬 가능):**
1. `app/schemas/draft.py` — Pydantic schemas
2. `app/schemas/post.py` — `from_draft_id` 1줄 추가
3. `app/api/drafts.py` — router + 4 endpoint + `_get_draft_or_404` helper
4. `app/api/posts.py` `create_post` — `from_draft_id` 처리 (commit 직전)
5. `app/main.py` — drafts router 등록
6. `alembic/versions/0035_draft_limit_index.py` — partial index
7. `app/services/draft_cleanup_jobs.py` + schedule 등록
8. `backend/scripts/smoke_test_drafts.sh`

**Frontend (Backend step 3 완료 후 의존성):**
9. `lib/api.ts` — Draft 타입 + 4개 함수 (`listDrafts`, `getDraft`, `saveDraft`, `deleteDraft`)
10. `lib/hooks/useDraftAutosave.ts` — hook
11. `components/DraftRestoreDialog.tsx`
12. `components/icons.tsx` — DraftIcon 추가
13. `app/posts/new/page.tsx` — hook + dialog + header 변경
14. `app/posts/drafts/page.tsx` — 신규 목록 페이지
15. `components/Sidebar.tsx` — UserDropdown에 "임시저장 목록" 추가
16. `i18n/{ko,en,ja,zh,es}.json` — `post.draft.*` + `nav.draftsList` 키 추가

**검증:**
17. smoke_test_drafts.sh 실행
18. Manual QA 7항목 (위 §4.2)

---

## 6. Open Questions (3개) — RESOLVED (2026-04-30)

사용자 결정: 권장대로 — Q-D1=B, Q-D2=A, Q-D3=A.

### Q-D1. 작가 role 변경 후 기존 product draft 처리 (Backend §2.5)

**문제**: 사용자가 product draft 작성 → 작가 권한 변경(role='user') → 기존 draft 수정 시도 시 행동.

| 옵션 | 동작 |
|------|------|
| **A) Strict** | `upsert_draft`에서 `type=product`면 항상 role 검증 → role 변경 후 update 차단 (목록에는 보이나 에디터에서 에러) |
| **B) Permissive** | 신규 생성만 role 검증, draft_id 있는 update는 skip → role 변경 후에도 기존 draft 수정 가능 (단, 발행은 여전히 차단됨 — `posts.py:206-210`) |

**권장**: B (사용자 친화 + 발행 시점 검증으로 보호 충분). 단순 텍스트 수정/삭제까지 차단할 이유 없음.

### Q-D2. `formatRelativeTime` 유틸 존재 여부 (Frontend FQ-2)

`AutosaveIndicator`의 "저장됨 · 5초 전" 표시에 필요. 프로젝트에 기존 `lib/formatRelativeTime.ts` 유무 Do 단계에서 확인 후 결정:
- 있으면 재사용
- 없으면 신규 작성 (~20줄, `time.*` i18n 키 활용)

`/notifications/page.tsx:15-25`에 인라인 `timeAgo` 함수 있음 — 이를 lib으로 추출 권장.

### Q-D3. cleanup job 실행 위치

`services/draft_cleanup_jobs.py`를 schedule_jobs.py에 등록할지, 별도 cron으로 실행할지.

기존 `webhook_cleanup_jobs.py`, `community_jobs.py` 패턴 확인 후 동일 방식 채택. Do 단계에서 확정.

---

## 7. Migration & Rollout

- **DB**: 마이그레이션 0035만 실행 (partial index — 비차단, 빠름)
- **Backend 무중단 배포 가능** — 기존 `/v1/posts` 엔드포인트는 그대로
- **Frontend feature flag 불요** — drafts 미사용 시 영향 없음
- **Rollback**: 0035 인덱스 drop, drafts router 미등록만 하면 됨

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-30 | Initial integrated design — frontend-architect + bkend-expert 병렬 작성 결과 통합. 3 Open Questions (Q-D1/D2/D3) | itpe-ince / Claude Opus 4.7 |
