"""B2B Reports API — school/gallery/sponsor reports for admin."""
import io
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.db.session import get_db
from app.models.auction import Order
from app.models.post import Follow, Post
from app.models.sponsorship import Sponsorship
from app.models.user import ArtistProfile, User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/school/{school_name}")
async def school_report(
    school_name: str,
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Report: artists from a specific school."""
    artists = await db.execute(
        select(User)
        .join(ArtistProfile, ArtistProfile.user_id == User.id)
        .where(ArtistProfile.school.ilike(f"%{school_name}%"), User.role == "artist")
    )
    artist_list = list(artists.scalars().all())
    artist_ids = [a.id for a in artist_list]

    total_posts = 0
    total_sales = 0
    total_sponsorships = 0

    if artist_ids:
        total_posts = await db.scalar(
            select(func.count()).select_from(Post).where(Post.author_id.in_(artist_ids))
        ) or 0
        total_sales = float(await db.scalar(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.seller_id.in_(artist_ids), Order.status.in_(["paid", "inspection_complete", "settled", "paid_out"])
            )
        ) or 0)
        total_sponsorships = float(await db.scalar(
            select(func.coalesce(func.sum(Sponsorship.amount), 0)).where(
                Sponsorship.artist_id.in_(artist_ids), Sponsorship.status == "completed"
            )
        ) or 0)

    return {
        "data": {
            "school": school_name,
            "artist_count": len(artist_list),
            "total_posts": total_posts,
            "total_sales_usd": total_sales,
            "total_sponsorships_usd": total_sponsorships,
            "artists": [
                {"id": str(a.id), "display_name": a.display_name, "role": a.role}
                for a in artist_list[:20]
            ],
        }
    }


@router.get("/overview")
async def platform_overview(
    days: int = Query(30, ge=1, le=365),
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Platform overview report for partners."""
    since = date.today() - timedelta(days=days)

    total_users = await db.scalar(select(func.count()).select_from(User).where(User.status == "active")) or 0
    total_artists = await db.scalar(select(func.count()).select_from(User).where(User.role == "artist")) or 0
    total_posts = await db.scalar(select(func.count()).select_from(Post).where(Post.status == "published")) or 0
    total_gmv = float(await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status.in_(["paid", "inspection_complete", "settled", "paid_out"]),
            func.date(Order.created_at) >= since,
        )
    ) or 0)
    total_sponsorship = float(await db.scalar(
        select(func.coalesce(func.sum(Sponsorship.amount), 0)).where(
            Sponsorship.status == "completed",
            func.date(Sponsorship.created_at) >= since,
        )
    ) or 0)

    return {
        "data": {
            "period_days": days,
            "total_users": total_users,
            "total_artists": total_artists,
            "total_posts": total_posts,
            "gmv_usd": total_gmv,
            "sponsorship_usd": total_sponsorship,
            "total_revenue_usd": total_gmv + total_sponsorship,
        }
    }


def _build_school_pdf(school_name: str, data: dict) -> bytes:
    """Render school report data as a PDF using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Domo — School Report: {school_name}", styles["Title"]))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Generated: {date.today().isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    summary_data = [
        ["Metric", "Value"],
        ["Artists", str(data["artist_count"])],
        ["Total Posts", str(data["total_posts"])],
        ["Total Sales (USD)", f"${data['total_sales_usd']:,.2f}"],
        ["Total Sponsorships (USD)", f"${data['total_sponsorships_usd']:,.2f}"],
    ]
    t = Table(summary_data, colWidths=[10 * cm, 7 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A8D76E")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5 * cm))

    if data.get("artists"):
        elements.append(Paragraph("Top Artists (up to 20)", styles["Heading2"]))
        artist_data = [["ID", "Display Name"]] + [
            [a["id"][:8] + "...", a["display_name"]] for a in data["artists"]
        ]
        at = Table(artist_data, colWidths=[5 * cm, 12 * cm])
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A8D76E")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(at)

    doc.build(elements)
    return buf.getvalue()


@router.get("/school/{school_name}/pdf")
async def school_report_pdf(
    school_name: str,
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """B2B school report as downloadable PDF (reportlab, pure Python)."""
    # Reuse the JSON report logic
    artists = await db.execute(
        select(User)
        .join(ArtistProfile, ArtistProfile.user_id == User.id)
        .where(ArtistProfile.school.ilike(f"%{school_name}%"), User.role == "artist")
    )
    artist_list = list(artists.scalars().all())
    artist_ids = [a.id for a in artist_list]

    total_posts = 0
    total_sales = 0.0
    total_sponsorships = 0.0

    if artist_ids:
        total_posts = await db.scalar(
            select(func.count()).select_from(Post).where(Post.author_id.in_(artist_ids))
        ) or 0
        total_sales = float(await db.scalar(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.seller_id.in_(artist_ids),
                Order.status.in_(["paid", "inspection_complete", "settled", "paid_out"]),
            )
        ) or 0)
        total_sponsorships = float(await db.scalar(
            select(func.coalesce(func.sum(Sponsorship.amount), 0)).where(
                Sponsorship.artist_id.in_(artist_ids), Sponsorship.status == "completed"
            )
        ) or 0)

    data = {
        "school": school_name,
        "artist_count": len(artist_list),
        "total_posts": total_posts,
        "total_sales_usd": total_sales,
        "total_sponsorships_usd": total_sponsorships,
        "artists": [
            {"id": str(a.id), "display_name": a.display_name}
            for a in artist_list[:20]
        ],
    }

    pdf_bytes = _build_school_pdf(school_name, data)
    safe_name = school_name.replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="school_report_{safe_name}.pdf"'
        },
    )
