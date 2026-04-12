"""Phase 3 Week 14 demo seed enhancement.

Adds on top of `scripts/seed.py`:
- 5 active auctions in mid-progress (multiple bids each)
- 2 pending reports
- 1 completed sponsorship history per artist

Run inside backend container (after `python -m scripts.seed`):
    docker compose exec -T backend python -m scripts.seed_demo

Idempotent: removes previously demo-tagged objects before re-creating.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.auction import Auction, Bid
from app.models.moderation import Report
from app.models.post import MediaAsset, Post, ProductPost
from app.models.sponsorship import Sponsorship
from app.models.user import User

DEMO_TAG = "DEMO_WEEK14"


async def reset_demo(db) -> None:
    posts_result = await db.execute(
        select(Post).where(Post.content == DEMO_TAG)
    )
    posts = list(posts_result.scalars().all())
    for p in posts:
        # Delete bids → auctions → product → media → post
        auctions_result = await db.execute(
            select(Auction).where(Auction.product_post_id == p.id)
        )
        for a in auctions_result.scalars().all():
            await db.execute(delete(Bid).where(Bid.auction_id == a.id))
            await db.delete(a)
        await db.execute(
            delete(ProductPost).where(ProductPost.post_id == p.id)
        )
        await db.execute(delete(MediaAsset).where(MediaAsset.post_id == p.id))
        await db.delete(p)

    await db.execute(delete(Report).where(Report.description == DEMO_TAG))
    await db.commit()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await reset_demo(db)

        artist_emails = [
            "maria@example.com",
            "linh@example.com",
            "kenji@example.com",
            "ana@example.com",
            "dmitri@example.com",
        ]
        artists: list[User] = []
        for email in artist_emails:
            r = await db.execute(select(User).where(User.email == email))
            u = r.scalar_one_or_none()
            if u:
                artists.append(u)

        collector_emails = [
            "alex@example.com",
            "chen@example.com",
            "sato@example.com",
            "riley@example.com",
            "emma@example.com",
        ]
        collectors: list[User] = []
        for email in collector_emails:
            r = await db.execute(select(User).where(User.email == email))
            u = r.scalar_one_or_none()
            if u:
                collectors.append(u)

        if len(artists) < 5 or len(collectors) < 3:
            print("⚠ run `scripts.seed` first to create base users")
            return

        admin_result = await db.execute(
            select(User).where(User.email == "admin@domo.example.com")
        )
        admin = admin_result.scalar_one_or_none()

        print(f"→ Creating {5} active auctions...")
        for i, artist in enumerate(artists):
            post = Post(
                id=uuid.uuid4(),
                author_id=artist.id,
                type="product",
                title=f"Demo Auction {i + 1} — {artist.display_name}",
                content=DEMO_TAG,
                genre=random.choice(
                    ["painting", "drawing", "photography", "sculpture"]
                ),
                tags=["demo", "week14"],
                language="en",
                status="published",
                digital_art_check="approved",
                like_count=random.randint(10, 80),
                view_count=random.randint(100, 600),
            )
            db.add(post)
            await db.flush()

            db.add(
                MediaAsset(
                    post_id=post.id,
                    type="image",
                    url=f"https://picsum.photos/seed/demo{i}/1200/1500",
                    thumbnail_url=f"https://picsum.photos/seed/demo{i}/400/500",
                    width=1200,
                    height=1500,
                    order_index=0,
                )
            )

            buy_now = (i % 2 == 0)
            db.add(
                ProductPost(
                    post_id=post.id,
                    is_auction=True,
                    is_buy_now=buy_now,
                    buy_now_price=Decimal("450000") if buy_now else None,
                    currency="KRW",
                    dimensions=random.choice(["50x70cm", "60x80cm"]),
                    medium=random.choice(
                        ["Oil on canvas", "Watercolor on paper", "Mixed media"]
                    ),
                    year=2026,
                )
            )
            await db.flush()  # Ensure ProductPost FK is satisfied before Auction

            start_price = Decimal("100000") + Decimal(str(i * 20000))
            increment = Decimal("10000")
            duration_h = random.choice([12, 24, 48, 72, 168])
            end_at = datetime.now(timezone.utc) + timedelta(hours=duration_h)

            auction = Auction(
                id=uuid.uuid4(),
                product_post_id=post.id,
                seller_id=artist.id,
                start_price=start_price,
                min_increment=increment,
                current_price=start_price,
                currency="KRW",
                start_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                end_at=end_at,
                status="active",
                bid_count=0,
            )
            db.add(auction)
            await db.flush()

            # Place 2~4 bids by different collectors
            num_bids = random.randint(2, 4)
            shuffled = random.sample(
                [c for c in collectors if c.id != artist.id], k=num_bids
            )
            current = start_price
            current_winner = None
            for j, bidder in enumerate(shuffled):
                amount = current + increment
                # Mark previous active as outbid
                if current_winner is not None:
                    await db.execute(
                        Bid.__table__.update()
                        .where(
                            Bid.auction_id == auction.id,
                            Bid.status == "active",
                        )
                        .values(status="outbid")
                    )
                db.add(
                    Bid(
                        id=uuid.uuid4(),
                        auction_id=auction.id,
                        bidder_id=bidder.id,
                        amount=amount,
                        status="active",
                    )
                )
                current = amount
                current_winner = bidder.id
                auction.bid_count += 1

            auction.current_price = current
            auction.current_winner = current_winner
            print(
                f"  {artist.display_name}: ₩{int(current):,} ({auction.bid_count} bids, ends in {duration_h}h)"
            )

        print("→ Creating sponsorship history...")
        for artist in artists:
            for _ in range(random.randint(1, 3)):
                sponsor = random.choice(collectors)
                bb = random.randint(2, 10)
                db.add(
                    Sponsorship(
                        sponsor_id=sponsor.id,
                        artist_id=artist.id,
                        bluebird_count=bb,
                        amount=Decimal(str(bb * 1000)),
                        currency="KRW",
                        is_anonymous=random.random() < 0.3,
                        visibility=random.choice(
                            ["public", "public", "artist_only"]
                        ),
                        message=random.choice(
                            [None, "Great work!", "Loved the texture", None]
                        ),
                        status="completed",
                    )
                )

        print("→ Creating 2 pending reports...")
        # Pick 2 random posts (not demo) to report
        target_result = await db.execute(
            select(Post).where(Post.status == "published").limit(20)
        )
        candidates = [p for p in target_result.scalars().all() if p.content != DEMO_TAG]
        if len(candidates) >= 2:
            picks = random.sample(candidates, k=2)
            for target in picks:
                reporter = random.choice(
                    [c for c in collectors if c.id != target.author_id]
                )
                db.add(
                    Report(
                        reporter_id=reporter.id,
                        target_type="post",
                        target_id=target.id,
                        reason=random.choice(["spam", "inappropriate"]),
                        description=DEMO_TAG,
                        status="pending",
                    )
                )

        await db.commit()

    print()
    print("=" * 50)
    print("Demo seed complete:")
    print("  · 5 active auctions with bids")
    print("  · sponsorship history added")
    print("  · 2 pending reports for moderation demo")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
