"""Legal endpoints — policy versions (Phase 4 M3)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.settings import get_setting

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/versions")
async def current_versions(db: AsyncSession = Depends(get_db)):
    """Return current policy version identifiers — used by frontend consent flow."""
    privacy = await get_setting(db, "privacy_policy_version")
    terms = await get_setting(db, "terms_version")
    return {
        "data": {
            "privacy_policy": privacy,
            "terms": terms,
        }
    }
