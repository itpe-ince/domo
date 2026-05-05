"""Newsletter composer — C-5 newsletter-digest.

compose_issue(): auto-builds a NewsletterIssue draft by pulling data from:
  - G'-7 FeaturedArtist (current month curated featured artist)
  - A-6 ArtistProfile/User (artist_index_rank top 5 improved)
  - G'-9 PostEngagementCache (top 5 posts last 7 days)
  - C-4 MediaCoverage (featured published items)

Markdown → HTML conversion is done inline (no external dependency).
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.featured_artist import FeaturedArtist
from app.models.media_coverage import MediaCoverage
from app.models.newsletter_issue import NewsletterIssue
from app.models.post_engagement_cache import PostEngagementCache
from app.models.user import User

log = logging.getLogger(__name__)

VALID_LOCALES = frozenset({"ko", "en", "ja", "zh", "es"})

# ─── Simple markdown → HTML (subset: headings, bold, paragraphs, links) ───────

_H2 = re.compile(r"^## (.+)$", re.MULTILINE)
_H3 = re.compile(r"^### (.+)$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_LINK = re.compile(r"\[(.+?)\]\((.+?)\)")
_HR = re.compile(r"^---$", re.MULTILINE)


def md_to_html(md: str) -> str:
    """Minimal markdown → HTML for newsletter emails."""
    html = md
    html = _HR.sub("<hr>", html)
    html = _H2.sub(r"<h2>\1</h2>", html)
    html = _H3.sub(r"<h3>\1</h3>", html)
    html = _BOLD.sub(r"<strong>\1</strong>", html)
    html = _LINK.sub(r'<a href="\2">\1</a>', html)

    # Wrap non-tag lines in <p>
    lines = html.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<"):
            result.append(stripped)
        else:
            result.append(f"<p>{stripped}</p>")
    return "\n".join(result)


# ─── Subject line templates per locale ────────────────────────────────────────

_SUBJECTS: dict[str, str] = {
    "ko": "Domo 뉴스레터 — {month} 아티스트 소식",
    "en": "Domo Newsletter — {month} Artist Highlights",
    "ja": "Domo ニュースレター — {month} アーティスト情報",
    "zh": "Domo 通讯 — {month} 艺术家资讯",
    "es": "Domo Boletín — Novedades de artistas {month}",
}


# ─── Compose function ─────────────────────────────────────────────────────────


async def compose_issue(
    issue_date: date,
    locale: str,
    db: AsyncSession,
    admin_id: uuid.UUID,
) -> NewsletterIssue:
    """Auto-compose a newsletter issue draft for the given date and locale.

    Pulls data from G'-7, A-6, G'-9, C-4.
    Returns an unsaved NewsletterIssue — caller is responsible for db.add/commit.
    """
    if locale not in VALID_LOCALES:
        raise ValueError(f"Invalid locale: {locale}")

    month_label = f"{issue_date.year}-{issue_date.month:02d}"
    month_start = date(issue_date.year, issue_date.month, 1)

    # ── G'-7: featured artist ────────────────────────────────────────────────
    featured_artist_id: uuid.UUID | None = None
    featured_artist_name: str = ""
    fa_result = await db.execute(
        select(FeaturedArtist, User).join(
            User, FeaturedArtist.artist_id == User.id
        ).where(
            FeaturedArtist.month == month_start,
            FeaturedArtist.is_active.is_(True),
        ).limit(1)
    )
    fa_row = fa_result.first()
    if fa_row:
        fa, fa_user = fa_row
        featured_artist_id = fa.artist_id
        featured_artist_name = fa_user.display_name or str(fa.artist_id)

    # ── A-6: top 5 ranked artists ────────────────────────────────────────────
    top_artists_result = await db.execute(
        select(User).where(
            User.role == "artist",
            User.status == "active",
            User.deleted_at.is_(None),
            User.artist_index_rank.isnot(None),
        ).order_by(User.artist_index_rank).limit(5)
    )
    top_artists = list(top_artists_result.scalars().all())
    top_artist_ids = [str(a.id) for a in top_artists]
    top_artist_names = [a.display_name or str(a.id) for a in top_artists]

    # ── G'-9: top 5 posts by engagement (last 7 days) ───────────────────────
    pec_result = await db.execute(
        select(PostEngagementCache).order_by(
            PostEngagementCache.engagement_score.desc()
        ).limit(5)
    )
    pec_rows = list(pec_result.scalars().all())
    post_ids = [str(row.post_id) for row in pec_rows]

    # ── C-4: featured media coverage (published + is_featured) ──────────────
    mc_result = await db.execute(
        select(MediaCoverage).where(
            MediaCoverage.is_published.is_(True),
            MediaCoverage.is_featured.is_(True),
        ).order_by(MediaCoverage.published_at.desc()).limit(5)
    )
    mc_rows = list(mc_result.scalars().all())
    mc_ids = [str(row.id) for row in mc_rows]

    # ── Build markdown body ──────────────────────────────────────────────────
    md = _build_markdown(
        locale=locale,
        month_label=month_label,
        featured_artist_name=featured_artist_name,
        top_artist_names=top_artist_names,
        mc_rows=mc_rows,
    )
    html = md_to_html(md)
    subject = _SUBJECTS.get(locale, _SUBJECTS["en"]).format(month=month_label)

    return NewsletterIssue(
        id=uuid.uuid4(),
        issue_date=issue_date,
        subject=subject,
        body_markdown=md,
        body_html=html,
        locale=locale,
        featured_artist_id=featured_artist_id,
        new_top_artists=top_artist_ids,
        new_posts_highlight=post_ids,
        media_coverage_ids=mc_ids,
        status="draft",
        sent_count=0,
        failed_count=0,
        sent_at=None,
        created_by_admin_id=admin_id,
    )


def _build_markdown(
    locale: str,
    month_label: str,
    featured_artist_name: str,
    top_artist_names: list[str],
    mc_rows: list,
) -> str:
    """Build locale-aware markdown body."""
    if locale == "ko":
        return _build_markdown_ko(month_label, featured_artist_name, top_artist_names, mc_rows)
    elif locale == "ja":
        return _build_markdown_ja(month_label, featured_artist_name, top_artist_names, mc_rows)
    elif locale == "zh":
        return _build_markdown_zh(month_label, featured_artist_name, top_artist_names, mc_rows)
    elif locale == "es":
        return _build_markdown_es(month_label, featured_artist_name, top_artist_names, mc_rows)
    else:
        return _build_markdown_en(month_label, featured_artist_name, top_artist_names, mc_rows)


def _build_markdown_ko(
    month: str,
    featured: str,
    tops: list[str],
    mc: list,
) -> str:
    lines = [
        f"## Domo {month} 뉴스레터",
        "",
        "안녕하세요, Domo 구독자 여러분!",
        "이번 달의 아티스트 소식을 전해드립니다.",
        "",
        "---",
        "",
    ]
    if featured:
        lines += [
            "## 이달의 추천 아티스트",
            f"**{featured}** 아티스트를 주목해주세요!",
            "",
            "---",
            "",
        ]
    if tops:
        lines += ["## 인기 아티스트 TOP 5"]
        for i, name in enumerate(tops, 1):
            lines.append(f"**{i}위** {name}")
        lines += ["", "---", ""]
    if mc:
        lines += ["## 미디어 커버리지"]
        for row in mc:
            lines.append(f"- [{row.title}]({row.external_url}) — {row.source_name}")
        lines += ["", "---", ""]
    lines.append("구독 취소를 원하시면 아래 링크를 클릭하세요.")
    return "\n".join(lines)


def _build_markdown_en(
    month: str,
    featured: str,
    tops: list[str],
    mc: list,
) -> str:
    lines = [
        f"## Domo {month} Newsletter",
        "",
        "Hello Domo subscribers!",
        "Here are this month's artist highlights.",
        "",
        "---",
        "",
    ]
    if featured:
        lines += [
            "## Featured Artist of the Month",
            f"Spotlight on **{featured}**!",
            "",
            "---",
            "",
        ]
    if tops:
        lines += ["## Top 5 Artists"]
        for i, name in enumerate(tops, 1):
            lines.append(f"**#{i}** {name}")
        lines += ["", "---", ""]
    if mc:
        lines += ["## Media Coverage"]
        for row in mc:
            lines.append(f"- [{row.title}]({row.external_url}) — {row.source_name}")
        lines += ["", "---", ""]
    lines.append("To unsubscribe, click the link below.")
    return "\n".join(lines)


def _build_markdown_ja(
    month: str,
    featured: str,
    tops: list[str],
    mc: list,
) -> str:
    lines = [
        f"## Domo {month} ニュースレター",
        "",
        "Domoの購読者の皆さん、こんにちは！",
        "今月のアーティスト情報をお届けします。",
        "",
        "---",
        "",
    ]
    if featured:
        lines += [
            "## 今月の注目アーティスト",
            f"**{featured}** さんに注目！",
            "",
            "---",
            "",
        ]
    if tops:
        lines += ["## 人気アーティスト TOP 5"]
        for i, name in enumerate(tops, 1):
            lines.append(f"**{i}位** {name}")
        lines += ["", "---", ""]
    if mc:
        lines += ["## メディア掲載"]
        for row in mc:
            lines.append(f"- [{row.title}]({row.external_url}) — {row.source_name}")
        lines += ["", "---", ""]
    lines.append("配信停止はこちらのリンクからどうぞ。")
    return "\n".join(lines)


def _build_markdown_zh(
    month: str,
    featured: str,
    tops: list[str],
    mc: list,
) -> str:
    lines = [
        f"## Domo {month} 通讯",
        "",
        "亲爱的Domo订阅者，大家好！",
        "以下是本月的艺术家精选内容。",
        "",
        "---",
        "",
    ]
    if featured:
        lines += [
            "## 本月推荐艺术家",
            f"聚焦 **{featured}**！",
            "",
            "---",
            "",
        ]
    if tops:
        lines += ["## 热门艺术家 TOP 5"]
        for i, name in enumerate(tops, 1):
            lines.append(f"**第{i}名** {name}")
        lines += ["", "---", ""]
    if mc:
        lines += ["## 媒体报道"]
        for row in mc:
            lines.append(f"- [{row.title}]({row.external_url}) — {row.source_name}")
        lines += ["", "---", ""]
    lines.append("如需退订，请点击下方链接。")
    return "\n".join(lines)


def _build_markdown_es(
    month: str,
    featured: str,
    tops: list[str],
    mc: list,
) -> str:
    lines = [
        f"## Boletín Domo {month}",
        "",
        "¡Hola suscriptores de Domo!",
        "Aquí están los destacados de artistas de este mes.",
        "",
        "---",
        "",
    ]
    if featured:
        lines += [
            "## Artista destacado del mes",
            f"¡Atención en **{featured}**!",
            "",
            "---",
            "",
        ]
    if tops:
        lines += ["## Top 5 artistas"]
        for i, name in enumerate(tops, 1):
            lines.append(f"**#{i}** {name}")
        lines += ["", "---", ""]
    if mc:
        lines += ["## Cobertura mediática"]
        for row in mc:
            lines.append(f"- [{row.title}]({row.external_url}) — {row.source_name}")
        lines += ["", "---", ""]
    lines.append("Para darse de baja, haga clic en el enlace a continuación.")
    return "\n".join(lines)
