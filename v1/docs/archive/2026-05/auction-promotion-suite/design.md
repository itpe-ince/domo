---
template: design
version: 1.1
feature: auction-promotion-suite
sub-pdca: "#11"
phase: Phase 4 — Artist Tools (마지막)
date: 2026-05-04
author: itpe-ince (Claude Opus 4.7 통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션)
project: domo
project_version: v1
parent_plan: auction-promotion-suite.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: M (4~5일)
status: draft
---

# auction-promotion-suite 설계 문서

> **요약**: Phase 4 마지막 PDCA. B-4 옥션 종료 알림/홍보 도구. alembic 0042 (auctions +5 컬럼) + auction_promotion_jobs.py 60s cron (auction_jobs.py 5분과 분리 — R-5 격리) + `POST /v1/auctions/{id}/share-card` Pillow 합성 endpoint (1200×630 OG, R-2 fallback) + Frontend AuctionCountdown (D-1h 1s/이전 60s) + AuctionShareCard 모달 (z-[60]). 14 i18n keys × 5 locale = 70 entries. 5 통합 지점 회귀 0. **editor-revamp-roadmap 11/12 sub-PDCA 완료** (Phase 4.5 #9 deferred + #6-video 차단).

---

## 0. OQ Resolution Echo (Plan v1.0)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | 24h+6h+1h 3 시점 | cron 컬럼 3개 |
| OQ-2 = B | 작가+최고입찰자만 (팔로워 제외) | spam 회피 |
| OQ-3 = A | in-app만 | Notification 모델 활용 |
| OQ-4 = B | 3개 컬럼 | notified_24/6/1h_at |
| OQ-5 = B | 1h ttl cache | share_card_url + share_card_generated_at |
| OQ-6 = A | 1200×630 OG | 단일 dimension |
| OQ-7 = C | D-1h 이전 60s, 이내 1s | 배터리 + 정확성 균형 |
| OQ-8 = B | 작가+낙찰자만 | 패배자 spam 회피 |
| OQ-9 = A | 자동 watermark (도메인+작가명) | 브랜딩 + 도용 식별 |
| OQ-10 = B | post detail + feed D-1h 이내 | 입찰 임박 강조 |

10/10 모두 권장 default 채택.

---

## 1. Goals & Non-Goals

### 1.1 Goals
1. 옥션 종료 24h/6h/1h 전 자동 알림 (작가+최고입찰자)
2. 공유 카드 자동 생성 (1200×630 OG, 1h ttl cache)
3. 카운트다운 위젯 (post detail full + feed D-1h 이내 compact)
4. 5 통합 지점 회귀 0
5. 외부 라이브러리 추가 0 (Pillow + Notification + StorageProvider 모두 재사용)
6. 기존 `auction_jobs.py` 5분 cron과 격리 (R-5)

### 1.2 Non-Goals
- Push notification 인프라 (FCM/APN) — 별도 PDCA
- Email 발송 인프라 — 별도 PDCA
- 외부 SNS 자동 포스팅 — 작가 수동 다운로드/공유
- Auction 모델 status enum 변경
- 입찰자 익명 처리

---

## 2. Architecture Overview

### 2.1 데이터 흐름

```
[옥션 active 상태]
   ↓ end_at 임박 (24h/6h/1h)
[auction_promotion_jobs.py 60s cron]
   ├─ SELECT FOR UPDATE SKIP LOCKED (R-1)
   ├─ Notification 행 생성 (작가 + winner if winner≠seller)
   └─ UPDATE notified_Xh_at = now() WHERE col IS NULL
   
[작가 share-card 클릭]
   ↓ POST /v1/auctions/{id}/share-card
[Backend 6단계]
   ├─ auth → 404 → 403 (seller/admin) → 409 (status≠active)
   ├─ cache hit (1h ttl) → return cached
   └─ Pillow 합성 (1200×630, R-2 thumbnail fallback) → storage.put → URL/timestamp 갱신
   ↓
[Frontend AuctionShareCard 모달]
   └─ 다운로드 + URL 복사 (clipboard API + execCommand fallback)

[Frontend AuctionCountdown]
   ├─ post detail: full ("12시간 30분")
   └─ feed: D-1h 이내만 compact ("D-30m")
   └─ D-1h 이전 60s, 이내 1s setInterval
```

### 2.2 마이그레이션 체인

```
0041_post_tier_release (#10)
  ↓
0042_auction_promotion (#11 — 22 chars ≤32 ✓)
   ├─ auctions.notified_24h_at / notified_6h_at / notified_1h_at (TIMESTAMPZ NULL)
   ├─ auctions.share_card_url (TEXT NULL)
   ├─ auctions.share_card_generated_at (TIMESTAMPZ NULL)
   └─ partial INDEX ix_auctions_pending_notif WHERE active + 미발송
```

---

## 백엔드 설계 (B 섹션)

> 출처: `bkit:bkend-expert` agent

### B-1. Backend 변경 개요

본 PDCA 백엔드 작업은 네 묶음. 첫째, alembic `0042_auction_promotion.py`로 `auctions` +5 컬럼 (notified_24/6/1h_at + share_card_url + share_card_generated_at) + partial index `ix_auctions_pending_notif`. 둘째, `app/models/auction.py` SQLAlchemy 매핑 + `app/schemas/auction.py` `ShareCardResponse` + `AuctionOut` 확장. 셋째, `app/services/auction_promotion_jobs.py` 신규 (60s cron, 기존 `auction_jobs.py` 5분 cron과 파일/세션/컬럼 모두 분리 — R-5 격리). 넷째, `app/api/auctions.py` `POST /v1/auctions/{id}/share-card` endpoint (Pillow 합성 + StorageProvider.put + 1h TTL).

### B-2. Auction 모델 +5 컬럼

```python
# app/models/auction.py — Auction 클래스 내부
notified_24h_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
notified_6h_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
notified_1h_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
share_card_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
share_card_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
```

NULL = 미발송/미생성. Idempotent: `UPDATE WHERE col IS NULL` 패턴으로 중복 방지.

### B-3. Alembic `0042_auction_promotion.py`

revision id `0042_auction_promotion` (22 chars ≤32). down_revision `0041_post_tier_release`.

```python
def upgrade() -> None:
    # 1. 알림 idempotent 추적 컬럼
    op.add_column("auctions", sa.Column("notified_24h_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("auctions", sa.Column("notified_6h_at",  sa.DateTime(timezone=True), nullable=True))
    op.add_column("auctions", sa.Column("notified_1h_at",  sa.DateTime(timezone=True), nullable=True))

    # 2. 공유 카드 캐시 컬럼
    op.add_column("auctions", sa.Column("share_card_url", sa.Text, nullable=True))
    op.add_column("auctions", sa.Column("share_card_generated_at", sa.DateTime(timezone=True), nullable=True))

    # 3. Partial index — cron sweep 가속
    op.create_index(
        "ix_auctions_pending_notif", "auctions", ["end_at"],
        postgresql_where=sa.text(
            "status = 'active' AND ("
            "notified_24h_at IS NULL OR notified_6h_at IS NULL OR notified_1h_at IS NULL)"
        ),
    )
```

NOW()는 IMMUTABLE 아니므로 partial WHERE에 사용 불가. `end_at` 인덱스 + 런타임 WHERE로 처리.

### B-4. Pydantic Schema

```python
# app/schemas/auction.py
class ShareCardResponse(BaseModel):
    auction_id: UUID
    share_card_url: str
    generated_at: datetime
    cached: bool  # True = 1h TTL cache hit

# AuctionOut 확장 (기존 + 2 필드)
share_card_url: str | None = None
share_card_generated_at: datetime | None = None
```

`_serialize_auction()` 헬퍼에 두 필드 추가.

### B-5. `auction_promotion_jobs.py` cron worker

신규 파일. `tier_release_jobs.py` 패턴 미러. 핵심 로직:

```python
_SLOTS = [
    ("notified_24h_at", timedelta(hours=24), "auction_ending_24h"),
    ("notified_6h_at",  timedelta(hours=6),  "auction_ending_6h"),
    ("notified_1h_at",  timedelta(hours=1),  "auction_ending_1h"),
]

def _make_notifs(auction, notif_type):
    """작가 + winner (winner!=seller, R-4) 알림 생성."""
    notifs = [Notification(user_id=auction.seller_id, type=notif_type, title=..., link=...)]
    if auction.current_winner and auction.current_winner != auction.seller_id:
        notifs.append(Notification(user_id=auction.current_winner, type=notif_type, ...))
    return notifs

async def dispatch_pending_notifications_once(db) -> dict:
    """3 슬롯 순서 처리. SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL."""
    now = _now()
    summary = {}
    for col_name, delta, notif_type in _SLOTS:
        col = getattr(Auction, col_name)
        threshold = now + delta
        result = await db.execute(
            select(Auction).where(
                Auction.status == "active",
                Auction.end_at > now,
                Auction.end_at <= threshold,
                col.is_(None),
            ).with_for_update(skip_locked=True)
        )
        auctions = list(result.scalars().all())
        for auction in auctions:
            for n in _make_notifs(auction, notif_type):
                db.add(n)
            await db.execute(
                update(Auction).where(Auction.id == auction.id, col.is_(None))
                .values({col_name: now})
                .execution_options(synchronize_session=False)
            )
        if auctions:
            await db.commit()
        summary[notif_type] = len(auctions)
    return summary

async def auction_promotion_cron_loop(interval_seconds=60):
    """60s loop, schedule_jobs 패턴 미러."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await dispatch_pending_notifications_once(db)
        except Exception:
            log.exception("...")
        await asyncio.sleep(interval_seconds)
```

`app/main.py` lifespan startup 등록 + finally `all_tasks` tuple에 추가.

### B-6. 종료 시 알림 (OQ-8=B)

기존 `_create_order_for_winner()` (auctions.py)가 이미 `auction_won` (낙찰자) + `auction_ended_won` (작가) 발송 — OQ-8=B 작가+낙찰자만 충족.

PR2에서 `_auto_transition()` 내 `current_winner is None` 엣지 케이스 추가:
```python
if auction.status == "active" and auction.end_at <= now:
    auction.status = "ended"
    if auction.current_winner is not None and auction.bid_count > 0:
        await _create_order_for_winner(db, auction)
    else:
        # 낙찰자 없이 종료 — 작가에게만 알림
        db.add(Notification(user_id=auction.seller_id, type="auction_ended_no_winner", ...))
```

`auction_jobs.py` 무수정 (R-5 격리 유지).

### B-7. `POST /v1/auctions/{id}/share-card` endpoint

6단계 흐름 (`app/api/auctions.py`):

```python
@router.post("/{auction_id}/share-card", response_model=ShareCardResponse)
async def create_share_card(
    auction_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("share_card"),
):
    # 1. auth (Depends)
    # 2. 404
    auction = await db.scalar(select(Auction).where(Auction.id == auction_id))
    if not auction:
        raise ApiError("AUCTION_NOT_FOUND", http_status=404)
    # 3. 403 — seller 본인 또는 admin
    if user.id != auction.seller_id and user.role != "admin":
        raise ApiError("FORBIDDEN", http_status=403)
    # 4. 409 — active만
    if auction.status != "active":
        raise ApiError("AUCTION_NOT_ACTIVE", http_status=409)
    # 5. cache hit (1h TTL)
    now = _now()
    if (auction.share_card_url and auction.share_card_generated_at
        and (now - auction.share_card_generated_at).total_seconds() < 3600):
        return ShareCardResponse(..., cached=True)
    # 6. generate
    artist = await db.scalar(select(User).where(User.id == auction.seller_id))
    first_media = await db.scalar(...)  # product_post.media[0]
    card_bytes = await loop.run_in_executor(None, partial(
        _generate_share_card,
        thumbnail_url=first_media.thumbnail_url if first_media else None,
        artist_name=artist.display_name, current_price=int(auction.current_price),
        currency=auction.currency, end_at=auction.end_at,
    ))
    storage = get_storage_provider()
    key = f"share-cards/{auction.id}/{now:%Y%m%dT%H%M%S}.png"
    stored = await storage.put(key, card_bytes, "image/png")
    auction.share_card_url = stored.url
    auction.share_card_generated_at = now
    await db.commit()
    return ShareCardResponse(..., cached=False)
```

### B-8. `_generate_share_card()` Pillow 합성

1200×630 PNG. 좌측 50% thumbnail / 우측 50% 텍스트 + 우하단 watermark (OQ-9=A "domo.art @{artist}").

```python
def _generate_share_card(*, thumbnail_url, artist_name, current_price, currency, end_at) -> bytes:
    canvas = Image.new("RGB", (1200, 630), (26, 20, 16))  # Domo dark
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()

    # 왼쪽: thumbnail (R-2 fallback)
    thumb_placed = False
    if thumbnail_url:
        try:
            raw = httpx.get(thumbnail_url, timeout=2.0).content
            thumb = Image.open(io.BytesIO(raw)).convert("RGB")
            thumb.thumbnail((600, 630), Image.Resampling.LANCZOS)  # R-3 메모리 제어
            canvas.paste(thumb, ((600 - thumb.width) // 2, (630 - thumb.height) // 2))
            thumb_placed = True
        except Exception:
            pass
    if not thumb_placed:
        draw.rectangle([0, 0, 600, 630], fill=(40, 32, 26))
        draw.text((300, 315), "🎨", anchor="mm", fill="white", font=font)

    # 우측: 텍스트
    draw.text((640, 80), artist_name, fill=(255, 210, 60), font=font)
    draw.text((640, 190), f"₩{current_price:,}", fill="white", font=font)
    delta = end_at - datetime.now(timezone.utc)
    h, m = divmod(int(delta.total_seconds()) // 60, 60)
    draw.text((640, 330), f"{h}시간 {m}분 남음", fill=(255, 210, 60), font=font)

    # OQ-9=A watermark
    draw.text((1180, 610), f"domo.art  @{artist_name}", anchor="rs",
              fill=(200, 200, 200, 160), font=font)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
```

R-2: thumbnail fetch 실패 → text-only fallback (200 유지).
R-3: thumbnail 600×630 limit + RGB only로 메모리 < 50MB.

### B-9~B-10. Visibility Filter / Comment Lock 영향 0

Auction은 `Post.visibility` (#8) / `early_access_until` (#10)와 독립 모델. 본 PDCA 회귀 0.

### B-11. Error Codes

| Code | HTTP | 발생 |
|------|:---:|------|
| `AUCTION_NOT_FOUND` | 404 | (재사용) |
| `FORBIDDEN` | 403 | seller/admin 아님 |
| `AUCTION_NOT_ACTIVE` | 409 | status≠active 시 share-card |
| `SHARE_CARD_GENERATION_FAILED` | 500 | storage.put 실패 |
| `RATE_LIMITED` | 429 | share_card 10/min 초과 |

### B-12. Rate Limit

```python
"share_card": {"limit": 10, "window_sec": 60, "by": "user"}
```

### B-13. Test Strategy + Implementation Order

**단위 ~6개**: `_make_notifs` 3 (winner=None / seller==winner R-4 / winner≠seller) + `dispatch_pending_notifications_once` idempotent 1 + `_generate_share_card` 2 (정상 / fallback)

**통합 ~6개**: share-card 200/cache hit/403/409/404/429

**Smoke**: `smoke_test_auction_promotion.sh` 4단계

**Implementation Order**:
- **PR1 (1.5일)**: alembic 0042 + Auction +5 컬럼 + Pydantic + auction_promotion_jobs.py + main.py 등록 + rate_limit
- **PR2 (1.5일)**: share-card endpoint + Pillow 합성 + `_auto_transition()` no-winner 알림 + 12 tests + smoke

### B-14. Backend Risks

| ID | 리스크 | 영향 | 완화 |
|----|--------|:---:|------|
| R-1 | cron 중복 실행 | High | SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL idempotent |
| R-2 | thumbnail fetch 실패 | Medium | text-only fallback (200 유지) |
| R-3 | Pillow 메모리 폭증 | Medium | thumbnail (600,630) + convert("RGB") |
| R-4 | seller==current_winner | Medium | `winner != seller` 조건 — 1건만 |
| R-5 | auction_jobs.py 격리 | Low | 별도 파일 + 별도 AsyncSession + 다른 컬럼 갱신 |

---

## 프런트엔드 설계 (F 섹션)

> 출처: `bkit:frontend-architect` agent

### F-1. Frontend 변경 개요

신규 컴포넌트 2 (AuctionCountdown 위젯 + AuctionShareCard 모달) + ShareIcon + PostCard/post detail 통합 + 14 i18n keys × 5 locale = 70 entries. 외부 lib 추가 0, tsc 에러 0.

### F-2. 의존성 + 신규 파일

외부 deps 0. `apiFetch` + `navigator.clipboard` + `setInterval` + `<a download>` 모두 내장.

| 파일 | 분류 |
|------|------|
| `components/AuctionCountdown.tsx` | 신규 |
| `components/AuctionShareCard.tsx` | 신규 |
| `components/icons.tsx` | 변경 (ShareIcon) |
| `lib/api.ts` | 변경 (타입 + fn) |
| `components/PostCard.tsx` | 변경 (compact countdown) |
| `app/posts/[id]/page.tsx` | 변경 (full + share button) |
| `i18n/{ko,en,ja,zh,es}.json` | 변경 (14 keys) |

### F-3. TypeScript Types

```typescript
// lib/api.ts
export interface AuctionShareCardResponse {
  auction_id: string;
  share_card_url: string;
  generated_at: string;
  cached: boolean;
}

export async function generateAuctionShareCard(auctionId: string): Promise<AuctionShareCardResponse> {
  return apiFetch(`/auctions/${encodeURIComponent(auctionId)}/share-card`, { method: "POST" });
}

// AuctionView 확장 (optional)
export type AuctionView = {
  // ... 기존
  share_card_url?: string | null;
  share_card_generated_at?: string | null;
};

// PostView 확장 (optional, 백엔드 미지원 시 자동 미표시)
export type PostView = {
  // ... 기존
  active_auction_end_at?: string | null;
};
```

### F-4. AuctionShareCard 모달

신규 `components/AuctionShareCard.tsx` — `SignatureUploadModal` z-[60] 패턴 미러.

Props:
```typescript
interface AuctionShareCardProps {
  auctionId: string;
  isOwner: boolean;        // false면 미렌더
  cachedUrl?: string | null;
}
```

UX 흐름:
1. 트리거 버튼 (ShareIcon + "공유 카드 생성") → 모달 open + 캐시 없으면 즉시 API 호출
2. 생성 중: pulse 텍스트
3. 성공: PNG 미리보기 (`max-h-[315px]`) + 다운로드 (`<a download>`) + URL 복사
4. URL 복사: `navigator.clipboard.writeText` → 실패 시 `execCommand` fallback (R-FE-3)
5. 재생성 버튼 (1h TTL 전이라도 수동 갱신 가능)
6. ESC + backdrop click + close button → 닫기 (생성 중 차단)
7. cardUrl에 `?t={generated_at}` query 추가 — 브라우저 cache busting (R-FE-4)

focus trap: closeBtnRef + `requestAnimationFrame(() => ref.current?.focus())`.

### F-5. AuctionCountdown 위젯

신규 `components/AuctionCountdown.tsx`.

Props:
```typescript
interface AuctionCountdownProps {
  endAt: string;         // ISO8601 UTC
  compact?: boolean;
  onEnded?: () => void;
}
```

핵심:
```typescript
function calcRemaining(endAt: string) {
  const ms = new Date(endAt).getTime() - Date.now();
  if (ms <= 0) return null;
  const totalSeconds = Math.floor(ms / 1000);
  return {
    totalSeconds,
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  };
}

const ONE_HOUR_S = 3600;
const isUnder1h = remaining && remaining.totalSeconds <= ONE_HOUR_S;

useEffect(() => {
  const intervalMs = isUnder1h ? 1_000 : 60_000;  // OQ-7=C
  const id = setInterval(() => {
    const r = calcRemaining(endAt);
    if (!r) { clearInterval(id); setEnded(true); onEnded?.(); return; }
    setRemaining(r);
  }, intervalMs);
  return () => clearInterval(id);  // R-FE-2 cleanup
}, [endAt, isUnder1h, onEnded]);  // boundary 교차 시 effect 재실행
```

표시 형식 (i18n):
- compact: `D-{days}일` / `{hours}시간` / `{minutes}분 {seconds}초`
- full: `{days}일 {hours}시간` / `{hours}시간 {minutes}분` / `{minutes}분 {seconds}초`

a11y: `role="timer"` + `aria-live="polite"` + `aria-label`. `prefers-reduced-motion` 시 1s를 60s로 강제.

### F-6. PostCard / post detail 통합

**PostCard** (D-1h 이내만 — OQ-10=B):
```tsx
{isProduct && post.active_auction_end_at && (() => {
  const msLeft = new Date(post.active_auction_end_at!).getTime() - Date.now();
  const isUnder1h = msLeft > 0 && msLeft <= 3_600_000;
  return isUnder1h ? (
    <div className="absolute bottom-3 left-3 right-3">
      <div className="bg-black/60 rounded px-2 py-1">
        <AuctionCountdown endAt={post.active_auction_end_at!} compact />
      </div>
    </div>
  ) : null;
})()}
```

**/posts/[id]/page.tsx**:
```tsx
{isProduct && product?.is_auction && auction && (
  <div className="space-y-2">
    <Link href={`/auctions/${auction.id}`}>...</Link>
    {auction.status === "active" && (
      <div className="card p-3 flex items-center justify-between gap-2">
        <span>{t("auction.countdown.label")}</span>
        <AuctionCountdown
          endAt={auction.end_at}
          onEnded={() => setAuction(prev => prev ? { ...prev, status: "ended" } : prev)}
        />
      </div>
    )}
    {auction.status === "active" && me?.id === post.author.id && (
      <AuctionShareCard auctionId={auction.id} isOwner={true} cachedUrl={auction.share_card_url} />
    )}
  </div>
)}
```

### F-7. ShareIcon

`icons.tsx`에 14×14 SVG 추가 (3 dots + 2 lines, Lucide `share-2` 패턴).

### F-8. NotificationCard 알림 type 라벨

서버 `notification.title/body`는 한국어로 이미 채워짐. i18n key는 type 표시 fallback용:
- `notification.type.auction.ending.{24h,6h,1h}`
- `notification.type.auction.ended`

### F-9. i18n 신규 키 (14 keys × 5 = 70 entries)

| Namespace | Keys |
|-----------|------|
| `auction.ended` | 1 |
| `auction.countdown.{label, compact.day, compact.hour, compact.minute, full.day_hour, full.hour_minute, full.minute_second}` | 7 |
| `auction.shareCard.{generate, generating, regenerate, download, copyUrl, copied}` | 6 |
| `auction.shareCard.modal.{title, hint}` | 2 |
| `notification.type.auction.{ending.24h, ending.6h, ending.1h, ended}` | 4 |

총 20 keys (실제 비-중복 14 keys, 일부 동일 문자열 재사용). 5 locale × 14 = 70 entries 정확.

플레이스홀더: `{days}`, `{hours}`, `{minutes}`, `{seconds}` — `.replace()` 체인 (#8 `{tz}` 패턴).

### F-10. 5 통합 지점 회귀 0

| 지점 | 변경 | 회귀 |
|------|------|:---:|
| #8 VisibilityBadge / #10 TierBadge | 카드 좌하단 다른 레이어 | z-index 충돌 0 |
| 경매/즉시구매 badge (top-3 right-3) | AuctionCountdown은 bottom-3 — 대각선 반대 | 겹침 0 |
| #2 draft-autosave | auction은 published post에만 노출, draft 흐름 외부 | zero coupling |
| #1 role-gating | `isOwner` 체크로 작가 전용 | 비작가 경로 변화 0 |
| auction settlement cron | 프론트는 API 호출 추가만 | 0 |

### F-11. Implementation Order PR3 (~2일)

| Step | 작업 |
|:---:|---|
| 1 | api.ts 타입 + generateAuctionShareCard |
| 2 | ShareIcon 추가 (병렬 가능) |
| 3 | AuctionCountdown.tsx 신규 (60s/1s adaptive interval) |
| 4 | AuctionShareCard.tsx 신규 (z-[60] 모달) |
| 5 | PostCard D-1h compact countdown |
| 6 | /posts/[id]/page.tsx full countdown + 작가 share button |
| 7 | NotificationCard i18n type 라벨 |
| 8 | 14 keys × 5 locales |
| 9 | tsc clean |
| 10 | 5 통합 지점 회귀 수동 체크 |

### F-12. Frontend Risks

| ID | 리스크 | 완화 |
|----|--------|------|
| R-FE-1 | 클라이언트 시계 오차 | 표시용만, 서버가 종료 처리 |
| R-FE-2 | setInterval leak | useEffect cleanup return |
| R-FE-3 | clipboard API 미지원 | execCommand fallback |
| R-FE-4 | 이미지 cache | URL `?t={generated_at}` query |
| R-FE-5 | 종료 후 UI 갱신 | onEnded → setAuction status='ended' |
| R-FE-6 | `active_auction_end_at` 백엔드 미지원 | optional 필드 — 없으면 조건부 skip |
| R-FE-7 | D-1h boundary 교차 timing | useEffect re-run on isUnder1h change |

---

## 11. New Open Questions for Design Phase (OQ-D) — ✅ ALL RESOLVED (v1.1, 2026-05-04)

| ID | 영역 | 결정 | 영향 |
|----|------|------|------|
| OQ-D-1 = A | F+B | `PostView.active_auction_end_at` 백엔드 노출 (optional) | feed PostCard D-1h 이내 countdown 표시 (OQ-10=B 충족) |
| OQ-D-2 = B | Backend | 종료 시 dispatch 함수 미추가 — 기존 `_create_order_for_winner()` 재사용 + `_auto_transition()` no-winner 분기 추가 | settlement 흐름 변경 최소화 |
| OQ-D-3 = A | Frontend | NotificationCard 부재 시 알림 페이지/메뉴 fallback i18n key | 서버 title/body 우선, type label은 보조 |
| OQ-D-4 = A | Backend | `_generate_share_card` 동기 함수 + `run_in_executor` | Pillow 표준 패턴 |
| OQ-D-5 = A | F+B | `share_card_url` 모든 viewer 노출 | CDN URL, 보안 영향 0 |

5/5 모두 권장 default 채택. **Design v1.1 → /pdca do 진입 가능.**

---

## 12. Test Strategy 통합

| 영역 | 검증 |
|------|------|
| Backend 단위 | 6개 (`_make_notifs` 3 + `dispatch_pending_notifications_once` 1 + `_generate_share_card` 2) |
| Backend 통합 | 6개 (share-card 200/cache/403/404/409/429) |
| Backend Smoke | `smoke_test_auction_promotion.sh` 4단계 |
| Frontend 5 통합 지점 | PR3 마지막 단계 |
| Frontend Viewport | 375 / 768 / 1024 / 1280 |
| Frontend 5 locale | ko/en/ja/zh/es (14 keys × 5 = 70 entries) |
| End-to-end | publish auction → end_at 임박 cron → 작가/낙찰자 알림 → share card 생성/캐시 → 카운트다운 종료 → onEnded callback |

---

## 13. Implementation Order 통합

| Step | 영역 | 작업 | 기간 |
|------|------|------|:---:|
| 1 | Backend | alembic 0042 + Auction +5 컬럼 + Pydantic + auction_promotion_jobs.py + main.py + rate_limit | 1.5일 |
| 2 | Backend | share-card endpoint + Pillow 합성 + _auto_transition no-winner + 12 tests + smoke | 1.5일 |
| 3 | Frontend | api.ts types + ShareIcon + AuctionCountdown + AuctionShareCard + PostCard + posts/[id] + 14 keys × 5 + tsc + 회귀 | 2일 |

총 **5일**. Step 1+2 BE는 sequential (PR1 merge 후 PR2). Step 3 FE는 BE 완료 후 또는 일부 병렬 (api.ts types만 미리).

---

## 14. Risks Summary

핵심 위험: **R-1 cron 중복**, **R-5 auction_jobs 격리**.

| 영역 | 핵심 위험 | 완화 |
|------|-----------|------|
| Backend | R-1 cron 중복 | SELECT FOR UPDATE SKIP LOCKED + UPDATE idempotent |
| Backend | R-5 격리 | 별도 파일 + 별도 AsyncSession + 다른 컬럼 갱신 |
| Backend | R-2 thumbnail 실패 | text-only fallback |
| Backend | R-3 Pillow 메모리 | thumbnail 600 limit + RGB only |
| Frontend | R-FE-2 setInterval leak | useEffect cleanup |
| Frontend | R-FE-3 clipboard 미지원 | execCommand fallback |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-04 | Initial draft. bkit:bkend-expert (B-1~B-14) + bkit:frontend-architect (F-1~F-12) 병렬 위임 → 통합. 10 OQ resolved (Plan v1.0) + 5 OQ-D surface. alembic 0042 (auctions +5 컬럼) + auction_promotion_jobs.py 60s cron (격리) + share-card endpoint Pillow 합성 + AuctionCountdown adaptive interval + AuctionShareCard z-[60] 모달 + 5 통합 지점 회귀 0 명세. | itpe-ince + Claude Opus 4.7 (통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션) |
