"""PATCH /v1/me/preferences/currency — B'-1 multi-currency-foundation.

Allows authenticated users to set their preferred display currency.
Supported currencies: USD, KRW, EUR, JPY.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me/preferences", tags=["me"])

SUPPORTED_CURRENCIES = {"USD", "KRW", "EUR", "JPY"}


class CurrencyPreferenceRequest(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        normalized = v.upper().strip()
        if normalized not in {"USD", "KRW", "EUR", "JPY"}:
            raise ValueError(
                f"Unsupported currency: {v}. Supported: USD, KRW, EUR, JPY"
            )
        return normalized


@router.patch("/currency")
async def update_preferred_currency(
    body: CurrencyPreferenceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("me_currency_preference"),
):
    """Update the user's preferred display currency.

    This sets user.preferred_currency which is used to convert prices
    on PostCard / FeedItem / posts/[id] pages.

    DB stores in native currency; display is converted to preferred_currency.
    """
    old = user.preferred_currency
    user.preferred_currency = body.currency
    await db.commit()
    await db.refresh(user)
    log.info("user %s preferred_currency: %s → %s", user.id, old, body.currency)

    return {
        "data": {
            "preferred_currency": user.preferred_currency,
        }
    }


@router.get("/currency")
async def get_preferred_currency(
    user: User = Depends(get_current_user),
    _rl=rate_limit("me_currency_preference"),
):
    """Get the user's current preferred display currency."""
    return {
        "data": {
            "preferred_currency": getattr(user, "preferred_currency", "USD"),
        }
    }
