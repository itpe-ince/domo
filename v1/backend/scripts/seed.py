"""Domo prototype seed data script.

Run inside backend container:
    docker compose exec -T backend python -m scripts.seed

Creates:
- 1 admin (admin@domo.example.com)
- 5 artists (approved + ArtistProfile)
- 5 collectors (regular users)
- 20 posts (mix of general + product, all `published`)
- Random follows, likes, comments

Idempotent: re-running clears Phase-1 content first.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.post import Comment, Follow, Like, MediaAsset, Post, ProductPost
from app.models.user import ArtistApplication, ArtistProfile, User

ARTISTS = [
    ("maria_lima", "maria@example.com", "PE", "Lima Art Academy", "Emerging painter from Peru, oils and landscapes."),
    ("linh_hanoi", "linh@example.com", "VN", "Hanoi Fine Arts University", "Watercolor portraits inspired by Vietnamese street life."),
    ("kenji_osaka", "kenji@example.com", "JP", "Kyoto University of Arts", "Mixed-media collage artist exploring memory."),
    ("ana_bogota", "ana@example.com", "CO", "Universidad de los Andes", "Oil painter, magical realism."),
    ("dmitri_kyiv", "dmitri@example.com", "UA", "NAOMA", "Charcoal sketches and urban landscapes."),
]

COLLECTORS = [
    ("alex_tokyo", "alex@example.com", "JP"),
    ("chen_taipei", "chen@example.com", "TW"),
    ("sato_kobe", "sato@example.com", "JP"),
    ("riley_la", "riley@example.com", "US"),
    ("emma_london", "emma@example.com", "GB"),
]

GENRES = ["painting", "photography", "sculpture", "drawing", "mixed_media"]

POST_TEMPLATES = [
    ("Sunrise in Lima", "Painted at dawn from my balcony.", "painting", ["oil", "landscape"], True, True, 500000, 300000),
    ("Morning Market", "Watercolor sketch from Hanoi old quarter.", "drawing", ["watercolor", "street"], False, True, 250000, None),
    ("Memory #3", "Collage on canvas, 60x80.", "mixed_media", ["collage"], True, False, None, 180000),
    ("Andean Dream", "Magical realism, oil on linen.", "painting", ["oil", "surreal"], True, True, 800000, 400000),
    ("City Pulse", "Charcoal series #2.", "drawing", ["charcoal", "urban"], False, False, None, None),
    ("Untitled Field", "Photo from rural Peru.", "photography", ["photo", "landscape"], False, True, 120000, None),
    ("Saudade", "Portrait in oil pastels.", "drawing", ["pastel", "portrait"], True, False, None, 220000),
    ("Wave Form", "Sculpture sketch series.", "sculpture", ["bronze"], False, False, None, None),
]

GENERAL_POSTS = [
    ("Today's studio", "Working on a new piece. Coffee and oils only."),
    ("Inspiration walk", "Found this color combination on my walk."),
    ("Time-lapse coming soon", "Recording the making of my next painting."),
    ("Studio visit", "Visited a friend's studio in Bogotá last week."),
]


async def clear_phase1_content() -> None:
    """Idempotent reset for re-running."""
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Comment))
        await db.execute(delete(Like))
        await db.execute(delete(Follow))
        await db.execute(delete(ProductPost))
        await db.execute(delete(MediaAsset))
        await db.execute(delete(Post))
        await db.execute(delete(ArtistProfile))
        await db.execute(delete(ArtistApplication))
        await db.execute(delete(Notification))
        # Keep users — but reset roles for known seed accounts
        all_emails = (
            [e for _, e, *_ in ARTISTS]
            + [e for _, e, *_ in COLLECTORS]
            + ["admin@domo.example.com"]
        )
        await db.execute(delete(User).where(User.email.in_(all_emails)))
        await db.commit()


async def upsert_user(
    db,
    email: str,
    display_name: str,
    role: str,
    country: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        id=uuid.uuid4(),
        email=email,
        sns_provider="seed",
        sns_id=f"seed-{email}",
        display_name=display_name,
        role=role,
        status="active",
        country_code=country,
    )
    db.add(user)
    await db.flush()
    return user


async def seed() -> None:
    print("→ Clearing Phase 1 content...")
    await clear_phase1_content()

    async with AsyncSessionLocal() as db:
        print("→ Creating admin...")
        admin = await upsert_user(
            db, "admin@domo.example.com", "domo_admin", role="admin"
        )

        print("→ Creating artists + ArtistProfile...")
        artist_users: list[User] = []
        for handle, email, country, school, statement in ARTISTS:
            user = await upsert_user(db, email, handle, role="artist", country=country)
            # Create approved application + profile
            app = ArtistApplication(
                user_id=user.id,
                school=school,
                statement=statement,
                portfolio_urls=[f"https://picsum.photos/seed/{handle}{i}/800/1000" for i in range(3)],
                status="approved",
                reviewed_by=admin.id,
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(app)
            await db.flush()
            db.add(
                ArtistProfile(
                    user_id=user.id,
                    application_id=app.id,
                    verified_by=admin.id,
                    school=school,
                    statement=statement,
                    portfolio_urls=app.portfolio_urls,
                    badge_level="emerging",
                    payout_country=country,
                )
            )
            artist_users.append(user)

        print("→ Creating collectors...")
        collector_users: list[User] = []
        for handle, email, country in COLLECTORS:
            user = await upsert_user(db, email, handle, role="user", country=country)
            collector_users.append(user)

        await db.commit()

        print("→ Creating posts...")
        all_posts: list[Post] = []
        # 20 product posts spread across artists
        for i in range(20):
            artist = artist_users[i % len(artist_users)]
            tpl = POST_TEMPLATES[i % len(POST_TEMPLATES)]
            (title, content, genre, tags, is_auction, is_buy_now, buy_now_price, start_price) = tpl
            # Force published + approved (skip pending_review for seed visibility)
            post = Post(
                id=uuid.uuid4(),
                author_id=artist.id,
                type="product",
                title=f"{title} #{i + 1}",
                content=content,
                genre=genre,
                tags=tags,
                language="en",
                status="published",
                digital_art_check="approved",
                like_count=random.randint(5, 50),
                view_count=random.randint(50, 500),
                bluebird_count=random.randint(0, 30),
            )
            db.add(post)
            await db.flush()

            db.add(
                MediaAsset(
                    post_id=post.id,
                    type="image",
                    url=f"https://picsum.photos/seed/{post.id}/1200/1500",
                    thumbnail_url=f"https://picsum.photos/seed/{post.id}/400/500",
                    width=1200,
                    height=1500,
                    order_index=0,
                )
            )
            db.add(
                ProductPost(
                    post_id=post.id,
                    is_auction=is_auction,
                    is_buy_now=is_buy_now,
                    buy_now_price=Decimal(str(buy_now_price)) if buy_now_price else None,
                    currency="KRW",
                    dimensions=random.choice(["50x70cm", "60x80cm", "30x40cm"]),
                    medium=random.choice(["Oil on canvas", "Watercolor on paper", "Mixed media"]),
                    year=2026,
                )
            )
            all_posts.append(post)

        # 8 general (SNS) posts
        for i, (title, content) in enumerate(GENERAL_POSTS * 2):
            artist = artist_users[i % len(artist_users)]
            post = Post(
                id=uuid.uuid4(),
                author_id=artist.id,
                type="general",
                title=title,
                content=content,
                language="en",
                status="published",
                digital_art_check="not_required",
                like_count=random.randint(0, 30),
                view_count=random.randint(20, 200),
            )
            db.add(post)
            all_posts.append(post)

        await db.commit()

        print(f"→ Creating follows ({len(collector_users)} × 3)...")
        for collector in collector_users:
            for artist in random.sample(artist_users, k=3):
                db.add(Follow(follower_id=collector.id, followee_id=artist.id))

        # Artists also follow each other
        for a in artist_users:
            for b in random.sample(artist_users, k=2):
                if a.id != b.id:
                    existing = await db.execute(
                        select(Follow).where(
                            Follow.follower_id == a.id, Follow.followee_id == b.id
                        )
                    )
                    if not existing.scalar_one_or_none():
                        db.add(Follow(follower_id=a.id, followee_id=b.id))

        await db.commit()

        print("→ Creating likes & comments...")
        comment_texts = [
            "Beautiful work!",
            "Stunning use of color.",
            "How much for the original?",
            "Wonderful composition.",
            "I love the texture in this.",
        ]
        for post in all_posts:
            likers = random.sample(collector_users, k=random.randint(1, 4))
            for liker in likers:
                db.add(Like(user_id=liker.id, post_id=post.id))
            commenters = random.sample(collector_users, k=random.randint(0, 2))
            for commenter in commenters:
                db.add(
                    Comment(
                        post_id=post.id,
                        author_id=commenter.id,
                        content=random.choice(comment_texts),
                        status="visible",
                    )
                )
            post.like_count = len(likers)
            post.comment_count = len(commenters)

        await db.commit()

    print()
    print("=" * 50)
    print("Seed complete.")
    print(f"  admin:      admin@domo.example.com")
    print(f"  artists:    {len(ARTISTS)} (mock:<email> to login)")
    print(f"  collectors: {len(COLLECTORS)}")
    print(f"  posts:      {20 + len(GENERAL_POSTS) * 2}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
