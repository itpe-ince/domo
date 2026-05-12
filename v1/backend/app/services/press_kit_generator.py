"""Press kit PDF generator — C-2 press-kit-auto-export.

Generates a multi-page press kit PDF for an artist using reportlab + Pillow.
Stores result via the configured storage provider and writes a PressKit DB row.

Page structure (5-8 pages):
  Page 1 — Cover: avatar + name + country + tier + ranking
  Page 2 — Bio: artist profile + activity stats
  Page 3 — Featured Works: top-4 posts (2x2 grid + captions)
  Page 4 — Interview: published ArtistInterview body_markdown (optional)
  Page 5 — Achievements: index score + rank + milestones
  Page 6 — Sponsor Stats: patron count + lifetime amount (optional)
  Page 7 — Contact: profile URL + Domo branding

Design constraints:
  - Domo brand colours: amber (#F59E0B) + dark (#1C1917)
  - CJK font support (H'-2): locale-driven font selection via font_registry.
    ko → NotoSansKR, ja → NotoSansJP, zh → NotoSansSC, en/es → Helvetica.
    Graceful fallback to Helvetica when font files are unavailable.
  - No external network calls during PDF generation (offline-safe)
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.artist_interview import ArtistInterview
from app.models.post import MediaAsset, Post
from app.models.press_kit import PressKit
from app.models.sponsorship import Sponsorship
from app.models.user import ArtistProfile, User
from app.schemas.press_kit import PressKitOut
from app.services.font_registry import get_font_pair, is_cjk_locale
from app.services.otel_setup import get_tracer
from app.services.storage.factory import get_storage_provider

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

# Brand colours (RGB 0-1 float for reportlab)
_AMBER = (0.961, 0.620, 0.043)   # #F59E0B
_DARK = (0.110, 0.098, 0.090)    # #1C1917
_WHITE = (1.0, 1.0, 1.0)
_GRAY = (0.6, 0.6, 0.6)
_LIGHT_GRAY = (0.92, 0.92, 0.92)

_CACHE_DAYS = 30


# ─── Public entry point ───────────────────────────────────────────────────────


async def generate_press_kit(
    *,
    db: AsyncSession,
    artist_id: uuid.UUID,
    locale: str,
    admin_id: uuid.UUID,
    force: bool = False,
) -> PressKit:
    """Generate (or return cached) press kit for an artist.

    Returns a PressKit ORM row. If a valid non-expired record exists for
    (artist_id, locale) and force=False, it is returned directly.
    """
    with tracer.start_as_current_span("press_kit.generate") as span:
        span.set_attribute("artist_id", str(artist_id))
        span.set_attribute("locale", locale)
        span.set_attribute("force_regenerate", force)
        return await _generate_press_kit_inner(
            db=db, artist_id=artist_id, locale=locale, admin_id=admin_id, force=force
        )


async def _generate_press_kit_inner(
    *,
    db: AsyncSession,
    artist_id: uuid.UUID,
    locale: str,
    admin_id: uuid.UUID,
    force: bool = False,
) -> PressKit:
    """Inner implementation — called from generate_press_kit with OTel span."""
    now = datetime.now(timezone.utc)

    # ── Cache check ─────────────────────────────────────────────────────────
    if not force:
        cached = await _find_cached(db, artist_id, locale, now)
        if cached:
            log.info(
                "press_kit_cache_hit artist=%s locale=%s pk=%s",
                artist_id, locale, cached.id,
            )
            return cached

    # ── Collect artist data ──────────────────────────────────────────────────
    artist = await _load_artist(db, artist_id)
    profile = await _load_profile(db, artist_id)
    posts = await _load_top_posts(db, artist_id)
    sponsor_stats = await _load_sponsor_stats(db, artist_id)
    interview = await _load_published_interview(db, artist_id, locale)

    # ── Build PDF ────────────────────────────────────────────────────────────
    pdf_bytes, page_count = _build_pdf(
        artist=artist,
        profile=profile,
        posts=posts,
        sponsor_stats=sponsor_stats,
        interview=interview,
        locale=locale,
    )

    # ── Store PDF ────────────────────────────────────────────────────────────
    storage = get_storage_provider()
    storage_key = f"press_kits/{artist_id}/{locale}/{now.strftime('%Y%m%d%H%M%S')}.pdf"
    stored = await storage.put(
        key=storage_key,
        data=pdf_bytes,
        content_type="application/pdf",
    )

    # ── Metadata snapshot ────────────────────────────────────────────────────
    gen_meta: dict[str, Any] = {
        "admin_id": str(admin_id),
        "generated_at": now.isoformat(),
        "artist_index_rank": getattr(artist, "artist_index_rank", None),
        "artist_index_score": getattr(artist, "artist_index_score", None),
        "sponsor_count": sponsor_stats["count"],
        "lifetime_amount": str(sponsor_stats["lifetime_amount"]),
        "post_count": len(posts),
        "has_interview": interview is not None,
    }

    # ── PressKit DB row ──────────────────────────────────────────────────────
    press_kit = PressKit(
        artist_id=artist_id,
        locale=locale,
        storage_key=stored.key,
        file_size_bytes=stored.size_bytes,
        page_count=page_count,
        interview_id=interview.id if interview else None,
        generation_metadata=gen_meta,
        is_public=False,  # artist must explicitly enable public download
        expires_at=now + timedelta(days=_CACHE_DAYS),
    )
    db.add(press_kit)
    await db.commit()
    await db.refresh(press_kit)

    log.info(
        "press_kit_generated artist=%s locale=%s pk=%s pages=%d bytes=%d",
        artist_id, locale, press_kit.id, page_count, stored.size_bytes,
    )
    return press_kit


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def _find_cached(
    db: AsyncSession, artist_id: uuid.UUID, locale: str, now: datetime
) -> PressKit | None:
    result = await db.execute(
        select(PressKit)
        .where(
            PressKit.artist_id == artist_id,
            PressKit.locale == locale,
            PressKit.expires_at > now,
        )
        .order_by(PressKit.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _load_artist(db: AsyncSession, artist_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == artist_id))
    artist = result.scalar_one_or_none()
    if artist is None:
        raise ApiError("NOT_FOUND", "Artist not found", http_status=404)
    return artist


async def _load_profile(
    db: AsyncSession, artist_id: uuid.UUID
) -> ArtistProfile | None:
    result = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == artist_id)
    )
    return result.scalar_one_or_none()


async def _load_top_posts(db: AsyncSession, artist_id: uuid.UUID) -> list[Post]:
    result = await db.execute(
        select(Post)
        .where(
            Post.author_id == artist_id,
            Post.status == "published",
        )
        .order_by(Post.like_count.desc(), Post.created_at.desc())
        .limit(4)
    )
    return list(result.scalars().all())


async def _load_sponsor_stats(
    db: AsyncSession, artist_id: uuid.UUID
) -> dict[str, Any]:
    from sqlalchemy import func as sqlfunc

    result = await db.execute(
        select(
            sqlfunc.count(Sponsorship.id).label("count"),
            sqlfunc.coalesce(sqlfunc.sum(Sponsorship.amount), 0).label(
                "lifetime_amount"
            ),
        ).where(
            Sponsorship.artist_id == artist_id,
            Sponsorship.status == "completed",
        )
    )
    row = result.one()
    return {"count": row.count or 0, "lifetime_amount": row.lifetime_amount or 0}


async def _load_published_interview(
    db: AsyncSession, artist_id: uuid.UUID, locale: str
) -> ArtistInterview | None:
    result = await db.execute(
        select(ArtistInterview)
        .where(
            ArtistInterview.artist_id == artist_id,
            ArtistInterview.locale == locale,
            ArtistInterview.status == "published",
        )
        .order_by(ArtistInterview.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ─── PDF generation ───────────────────────────────────────────────────────────


def _build_pdf(
    *,
    artist: User,
    profile: ArtistProfile | None,
    posts: list[Post],
    sponsor_stats: dict[str, Any],
    interview: ArtistInterview | None,
    locale: str,
) -> tuple[bytes, int]:
    """Build PDF bytes and return (bytes, page_count).

    Uses reportlab Platypus for layout. Font selection is locale-driven:
      - CJK locales (ko/ja/zh): Noto Sans CJK TTF via font_registry.
      - en/es and unrecognised locales: built-in Helvetica.
    When a CJK font file is unavailable, font_registry falls back to
    Helvetica automatically, so PDF generation never fails.
    Text is passed as-is to reportlab (UTF-8 safe with TTF embedding).
    For Helvetica-only fallback, non-Latin-1 chars are replaced with '?'.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("reportlab is required for press kit generation") from exc

    # ── Font selection (H'-2) ─────────────────────────────────────────────────
    font_regular, font_bold = get_font_pair(locale)
    # Determine whether we have a real CJK font or are using Helvetica fallback
    _cjk_active = font_regular not in ("Helvetica", "Helvetica-Bold")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=f"Press Kit — {_render_str(artist.display_name, font_regular)}",
        author="Domo",
    )

    styles = getSampleStyleSheet()

    # Custom styles — use locale-resolved fonts
    h1 = ParagraphStyle(
        "DH1",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=28,
        textColor=colors.Color(*_AMBER),
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "DH2",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=16,
        textColor=colors.Color(*_AMBER),
        spaceBefore=12,
        spaceAfter=6,
    )
    normal = ParagraphStyle(
        "DN",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=10,
        textColor=colors.Color(*_DARK),
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "DS",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=8,
        textColor=colors.Color(*_GRAY),
    )
    cover_name = ParagraphStyle(
        "DCover",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=36,
        textColor=colors.Color(*_WHITE),
        spaceAfter=8,
    )

    story: list = []

    # Partial helper to encode text for the selected font
    def _t(text: str | None) -> str:
        return _render_str(text, font_regular)

    # ── Page 1: Cover ────────────────────────────────────────────────────────
    story += _cover_page(artist, cover_name, h2, small, _t)
    story.append(PageBreak())

    # ── Page 2: Bio ─────────────────────────────────────────────────────────
    story += _bio_page(artist, profile, h2, normal, small, _t)
    story.append(PageBreak())

    # ── Page 3: Featured Works ───────────────────────────────────────────────
    story += _works_page(posts, h2, normal, small, _t)
    story.append(PageBreak())

    # ── Page 4: Interview (optional) ─────────────────────────────────────────
    if interview:
        story += _interview_page(interview, h2, normal, small, _t)
        story.append(PageBreak())

    # ── Page 5: Achievements ─────────────────────────────────────────────────
    story += _achievements_page(artist, profile, h2, normal, small, _t)
    story.append(PageBreak())

    # ── Page 6: Sponsor Stats (if any sponsors) ───────────────────────────────
    if sponsor_stats["count"] > 0:
        story += _sponsor_stats_page(sponsor_stats, h2, normal, small, _t)
        story.append(PageBreak())

    # ── Page 7: Contact ───────────────────────────────────────────────────────
    story += _contact_page(artist, h2, normal, small, locale, _t)

    # Pass font_regular for footer rendering in _page_frame
    _frame = _make_page_frame(font_regular)
    doc.build(story, onFirstPage=_frame, onLaterPages=_frame)

    pdf_bytes = buf.getvalue()
    # Rough page count from PDF structure: count "Page" occurrences
    page_count = max(1, pdf_bytes.count(b"/Type /Page\n") + pdf_bytes.count(b"/Type/Page\n"))
    return pdf_bytes, page_count


def _make_page_frame(font_regular: str):
    """Return a page frame callback that uses the given font for footer text."""

    def _page_frame(canvas, doc):
        """Draw header + footer on every page."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.units import cm
        except ImportError:
            return

        w, h = doc.pagesize
        canvas.saveState()

        # Header: thin amber line
        canvas.setStrokeColor(colors.Color(*_AMBER))
        canvas.setLineWidth(2)
        canvas.line(2 * cm, h - 1.5 * cm, w - 2 * cm, h - 1.5 * cm)

        # Footer: page number + URL — use locale font for proper rendering
        canvas.setFont(font_regular, 8)
        canvas.setFillColor(colors.Color(*_GRAY))
        canvas.drawString(2 * cm, 1 * cm, "domo.art")
        canvas.drawRightString(
            w - 2 * cm, 1 * cm, f"Page {canvas.getPageNumber()}"
        )

        canvas.restoreState()

    return _page_frame


# ─── Page builders ────────────────────────────────────────────────────────────


def _cover_page(artist, cover_name, h2, small, _t) -> list:
    try:
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    except ImportError:
        return []

    elements = []

    # Dark background box via a 1-cell table
    name_text = _t(artist.display_name)
    country = _t(artist.country_code or "")
    rank_text = ""
    rank = getattr(artist, "artist_index_rank", None)
    if rank:
        rank_text = f"Global Rank #{rank}"

    cover_data = [[
        Paragraph("PRESS KIT", h2),
    ]]
    cover_table = Table(cover_data, colWidths=["100%"])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*_DARK)),
        ("TOPPADDING", (0, 0), (-1, -1), 60),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
    ]))
    elements.append(cover_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph(name_text, cover_name))
    if country:
        elements.append(Paragraph(f"Country: {country}", small))
    if rank_text:
        elements.append(Paragraph(rank_text, small))

    score = getattr(artist, "artist_index_score", None)
    if score is not None:
        elements.append(Paragraph(f"Artist Index Score: {score:.1f}", small))

    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph("Generated by Domo — domo.art", small))
    return elements


def _bio_page(artist, profile, h2, normal, small, _t) -> list:
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [Paragraph("Artist Bio", h2), Spacer(1, 0.3 * cm)]

    name = _t(artist.display_name)
    elements.append(Paragraph(f"<b>Name:</b> {name}", normal))

    if artist.country_code:
        elements.append(
            Paragraph(f"<b>Country:</b> {_t(artist.country_code)}", normal)
        )

    if artist.bio:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(
            Paragraph(f"<b>About:</b> {_t(artist.bio)}", normal)
        )

    if profile and profile.portfolio_urls:
        url = profile.portfolio_urls[0] if profile.portfolio_urls else None
        if url:
            elements.append(
                Paragraph(
                    f"<b>Portfolio:</b> {_t(url)}", normal
                )
            )

    # Activity stats placeholder (actual counts require separate queries;
    # these come from generation_metadata if available)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("<b>Activity</b>", h2))
    elements.append(
        Paragraph("Emerging artist on Domo — the global art community.", normal)
    )

    if artist.created_at:
        joined = artist.created_at.strftime("%Y-%m-%d") if hasattr(artist.created_at, "strftime") else str(artist.created_at)
        elements.append(Paragraph(f"<b>Member since:</b> {joined}", normal))

    return elements


def _works_page(posts, h2, normal, small, _t) -> list:
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [Paragraph("Featured Works", h2), Spacer(1, 0.3 * cm)]

    if not posts:
        elements.append(Paragraph("No published works available.", normal))
        return elements

    for i, post in enumerate(posts, 1):
        title = _t(post.title or f"Work #{i}")
        elements.append(Paragraph(f"<b>{i}. {title}</b>", normal))
        if post.content:
            excerpt = _t(post.content[:200])
            elements.append(Paragraph(excerpt, small))
        if post.genre:
            elements.append(Paragraph(f"Genre: {_t(post.genre)}", small))
        elements.append(Spacer(1, 0.3 * cm))

    return elements


def _interview_page(interview, h2, normal, small, _t) -> list:
    """Page 4: C-1 ArtistInterview integration.

    Renders the published interview body_markdown as plain text (stripped of
    markdown syntax). Full markdown rendering via reportlab would require
    custom parsing — plain text is sufficient for press kit purposes.
    """
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [
        Paragraph("Artist Interview", h2),
        Spacer(1, 0.3 * cm),
    ]

    title = _t(interview.title)
    elements.append(Paragraph(f"<b>{title}</b>", normal))
    elements.append(Spacer(1, 0.2 * cm))

    # Strip basic markdown for PDF readability; _t handles font encoding
    body = _strip_markdown(_t(interview.body_markdown))
    # Split into paragraphs at double newlines
    for para in body.split("\n\n"):
        para = para.strip()
        if para:
            elements.append(Paragraph(para, normal))
            elements.append(Spacer(1, 0.15 * cm))

    if interview.created_at:
        date_str = interview.created_at.strftime("%Y-%m-%d") if hasattr(interview.created_at, "strftime") else str(interview.created_at)
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(f"Published: {date_str}", small))

    return elements


def _achievements_page(artist, profile, h2, normal, small, _t) -> list:
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [Paragraph("Achievements & Rankings", h2), Spacer(1, 0.3 * cm)]

    rank = getattr(artist, "artist_index_rank", None)
    score = getattr(artist, "artist_index_score", None)
    rank_region = getattr(artist, "artist_index_rank_region", None)
    genre = getattr(artist, "artist_index_primary_genre", None)

    if rank:
        elements.append(Paragraph(f"<b>Global Rank:</b> #{rank}", normal))
    if score is not None:
        elements.append(Paragraph(f"<b>Artist Index Score:</b> {score:.1f}", normal))
    if rank_region:
        elements.append(
            Paragraph(f"<b>Regional Rank:</b> #{rank_region}", normal)
        )
    if genre:
        elements.append(
            Paragraph(f"<b>Primary Genre:</b> {_t(genre)}", normal)
        )

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("<b>Milestones</b>", h2))

    if artist.created_at:
        joined = artist.created_at.strftime("%Y-%m-%d") if hasattr(artist.created_at, "strftime") else str(artist.created_at)
        elements.append(Paragraph(f"Joined Domo: {joined}", normal))

    elements.append(
        Paragraph("Active member of the global emerging artist community.", normal)
    )

    return elements


def _sponsor_stats_page(sponsor_stats, h2, normal, small, _t) -> list:
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [Paragraph("Patronage & Support", h2), Spacer(1, 0.3 * cm)]

    count = sponsor_stats["count"]
    amount = sponsor_stats["lifetime_amount"]

    elements.append(
        Paragraph(f"<b>Total Supporters:</b> {count:,}", normal)
    )
    elements.append(
        Paragraph(
            f"<b>Lifetime Patronage:</b> {float(amount):,.0f} KRW", normal
        )
    )
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Supported by the Domo community via the Blue Bird micro-patronage system.",
            normal,
        )
    )

    return elements


def _contact_page(artist, h2, normal, small, locale, _t) -> list:
    try:
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
    except ImportError:
        return []

    elements = [Paragraph("Contact & Links", h2), Spacer(1, 0.3 * cm)]

    artist_id = str(artist.id)
    profile_url = f"https://domo.art/users/{artist_id}"
    elements.append(Paragraph(f"<b>Profile:</b> {profile_url}", normal))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Domo — Global Emerging Artist Community", normal))
    elements.append(Paragraph("https://domo.art", normal))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            f"Press kit generated automatically. Locale: {locale}.",
            small,
        )
    )
    elements.append(
        Paragraph(
            "For media inquiries, contact the artist via their Domo profile.",
            small,
        )
    )

    return elements


# ─── Utility ──────────────────────────────────────────────────────────────────


def _render_str(text: str | None, font_name: str) -> str:
    """Return text suitable for the given reportlab font.

    - CJK fonts (NotoSansKR/JP/SC/TC): pass text as-is (UTF-8 safe with TTF
      embedding — reportlab handles Unicode correctly when a TTFont is used).
    - Helvetica fallback: encode to latin-1, replacing unmappable chars with '?'
      to prevent UnicodeEncodeError in reportlab's built-in Type 1 fonts.

    Args:
        text: Input string (may contain CJK characters).
        font_name: reportlab font name, e.g. "NotoSansKR" or "Helvetica".
    """
    if not text:
        return ""
    if font_name.startswith("Helvetica"):
        # Built-in Helvetica covers Latin-1 only
        return text.encode("latin-1", errors="replace").decode("latin-1")
    # TTF font — Unicode safe
    return text


def _safe_str(text: str | None) -> str:
    """Legacy helper — latin-1 safe string for Helvetica-only contexts.

    Kept for backward compatibility with any callers outside this module.
    New code should use _render_str() with explicit font_name.
    """
    if not text:
        return ""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_markdown(text: str) -> str:
    """Remove basic markdown syntax for PDF plain-text rendering."""
    import re

    # Headers: ## Title → Title
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Bold/italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Links: [text](url) → text (url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    # Horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    return text


# ─── Schema helper ────────────────────────────────────────────────────────────


def press_kit_to_out(pk: PressKit) -> PressKitOut:
    """Convert PressKit ORM row to PressKitOut schema."""
    storage = get_storage_provider()
    download_url = storage.public_url(pk.storage_key)
    return PressKitOut(
        id=pk.id,
        artist_id=pk.artist_id,
        locale=pk.locale,
        storage_key=pk.storage_key,
        download_url=download_url,
        file_size_bytes=pk.file_size_bytes,
        page_count=pk.page_count,
        interview_id=pk.interview_id,
        is_public=pk.is_public,
        expires_at=pk.expires_at,
        created_at=pk.created_at,
    )
