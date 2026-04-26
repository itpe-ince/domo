"""Admin: school management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.school import School
from app.models.user import User

router = APIRouter(tags=["admin"])


class SchoolCreateRequest(BaseModel):
    name_ko: str
    name_en: str
    country_code: str
    email_domain: str
    school_type: str = "university"
    logo_url: str | None = None


class SchoolUpdateRequest(BaseModel):
    name_ko: str | None = None
    name_en: str | None = None
    email_domain: str | None = None
    status: str | None = None


@router.get("/schools")
async def list_schools(
    q: str | None = Query(None),
    country: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(School)
    if q:
        query = query.where(School.name_ko.ilike(f"%{q}%") | School.name_en.ilike(f"%{q}%"))
    if country:
        query = query.where(School.country_code == country)
    if status:
        query = query.where(School.status == status)

    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(School.name_en.asc()).offset(offset).limit(limit))
    schools = result.scalars().all()

    return {
        "data": [
            {
                "id": str(s.id), "name_ko": s.name_ko, "name_en": s.name_en,
                "country_code": s.country_code, "email_domain": s.email_domain,
                "school_type": s.school_type, "status": s.status,
            }
            for s in schools
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.post("/schools")
async def create_school(
    body: SchoolCreateRequest,
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(School).where(School.email_domain == body.email_domain))
    if existing.scalar_one_or_none():
        raise ApiError("CONFLICT", "Email domain already registered", http_status=409)
    school = School(**body.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return {"data": {"id": str(school.id), "name_en": school.name_en, "email_domain": school.email_domain}}


@router.patch("/schools/{school_id}")
async def update_school(
    school_id: UUID,
    body: SchoolUpdateRequest,
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise ApiError("NOT_FOUND", "School not found", http_status=404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(school, k, v)
    await db.commit()
    return {"data": {"id": str(school.id), "status": school.status}}
