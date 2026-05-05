"""Admin newsletter management endpoints — C-5 newsletter-digest.

POST   /admin/newsletter/issues/compose      — auto-compose draft from live data
GET    /admin/newsletter/issues              — list issues (filter by status)
PATCH  /admin/newsletter/issues/{id}         — edit body/subject + status change
POST   /admin/newsletter/issues/{id}/send    — transition status draft→sending
"""
from __future__ import annotations

import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.newsletter_issue import NewsletterIssue
from app.models.user import User
from app.schemas.newsletter import (
    AdminPatchIssueRequest,
    NewsletterIssueOut,
)
from app.services.newsletter_composer import compose_issue, md_to_html

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/newsletter", tags=["admin-newsletter"])


def _row_to_out(row: NewsletterIssue) -> dict:
    return NewsletterIssueOut(
        id=row.id,
        issue_date=row.issue_date,
        subject=row.subject,
        body_markdown=row.body_markdown,
        body_html=row.body_html,
        locale=row.locale,
        featured_artist_id=row.featured_artist_id,
        new_top_artists=row.new_top_artists or [],
        new_posts_highlight=row.new_posts_highlight or [],
        media_coverage_ids=row.media_coverage_ids or [],
        status=row.status,
        sent_count=row.sent_count,
        failed_count=row.failed_count,
        sent_at=row.sent_at,
        created_by_admin_id=row.created_by_admin_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


# ─── POST /admin/newsletter/issues/compose ────────────────────────────────────


@router.post("/issues/compose", status_code=201)
async def admin_compose_issue(
    issue_date: date = Query(..., description="Issue date YYYY-MM-DD"),
    locale: str = Query("ko", pattern="^(ko|en|ja|zh|es)$"),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_admin_write"),
):
    """Auto-compose a newsletter draft for the given date and locale.

    Pulls live data from G'-7 (featured artist), A-6 (artist index),
    G'-9 (post engagement), C-4 (media coverage).
    """
    issue = await compose_issue(
        issue_date=issue_date,
        locale=locale,
        db=db,
        admin_id=admin.id,
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    log.info(
        "newsletter: composed issue locale=%s date=%s id=%s",
        locale,
        issue_date,
        issue.id,
    )
    return {"data": _row_to_out(issue)}


# ─── GET /admin/newsletter/issues ────────────────────────────────────────────


@router.get("/issues")
async def admin_list_issues(
    status: str | None = Query(
        None, pattern="^(draft|sending|sent|failed)$"
    ),
    locale: str | None = Query(None, pattern="^(ko|en|ja|zh|es)$"),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_admin_read"),
):
    """List newsletter issues (admin). Optionally filter by status and/or locale."""
    q = select(NewsletterIssue).order_by(NewsletterIssue.issue_date.desc())
    if status:
        q = q.where(NewsletterIssue.status == status)
    if locale:
        q = q.where(NewsletterIssue.locale == locale)
    q = q.limit(limit)
    result = await db.execute(q)
    rows = list(result.scalars().all())
    return {"data": [_row_to_out(r) for r in rows]}


# ─── PATCH /admin/newsletter/issues/{id} ─────────────────────────────────────


@router.patch("/issues/{issue_id}")
async def admin_patch_issue(
    issue_id: uuid.UUID,
    body: AdminPatchIssueRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_admin_write"),
):
    """Edit a newsletter issue (body/subject/status).

    Cannot edit a 'sent' or 'sending' issue's body or subject.
    Status can be changed: draft ↔ draft (body edit), draft → sending (use /send).
    """
    result = await db.execute(
        select(NewsletterIssue).where(NewsletterIssue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise ApiError("NOT_FOUND", "Newsletter issue not found", http_status=404)

    # Block body/subject edits on sent/sending issues
    if issue.status in ("sent", "sending") and (
        body.subject is not None or body.body_markdown is not None
    ):
        raise ApiError(
            "ISSUE_IMMUTABLE",
            "Cannot edit body/subject of a sent or sending issue.",
            http_status=422,
        )

    updates: dict = {}
    if body.subject is not None:
        updates["subject"] = body.subject
    if body.body_markdown is not None:
        updates["body_markdown"] = body.body_markdown
        updates["body_html"] = md_to_html(body.body_markdown)
    if body.status is not None:
        updates["status"] = body.status

    if updates:
        await db.execute(
            update(NewsletterIssue)
            .where(NewsletterIssue.id == issue_id)
            .values(**updates)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        await db.refresh(issue)

    return {"data": _row_to_out(issue)}


# ─── POST /admin/newsletter/issues/{id}/send ─────────────────────────────────


@router.post("/issues/{issue_id}/send", status_code=200)
async def admin_send_issue(
    issue_id: uuid.UUID,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_admin_write"),
):
    """Transition a draft issue to 'sending'.

    The cron worker (newsletter_jobs.py) picks up 'sending' issues and
    dispatches emails to all subscribed users with the matching locale.
    """
    result = await db.execute(
        select(NewsletterIssue).where(NewsletterIssue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise ApiError("NOT_FOUND", "Newsletter issue not found", http_status=404)

    if issue.status != "draft":
        raise ApiError(
            "INVALID_STATUS",
            f"Can only send a draft issue (current status: {issue.status}).",
            http_status=422,
        )

    await db.execute(
        update(NewsletterIssue)
        .where(NewsletterIssue.id == issue_id)
        .values(status="sending")
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    await db.refresh(issue)

    log.info(
        "newsletter: issue %s queued for sending (locale=%s)", issue_id, issue.locale
    )
    return {"data": _row_to_out(issue)}
