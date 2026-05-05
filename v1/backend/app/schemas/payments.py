"""Pydantic schemas for the payments API (B-1 Blue Bird sponsor flow)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SetupIntentRequest(BaseModel):
    """Request body for POST /v1/payments/setup-intent.

    No required fields — the backend derives the Stripe customer from the
    authenticated user. ``metadata`` is forwarded verbatim to Stripe.
    """

    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional key/value metadata forwarded to Stripe SetupIntent.",
    )


class SetupIntentResponse(BaseModel):
    """Response envelope for POST /v1/payments/setup-intent."""

    client_secret: str
    customer_id: str
    setup_intent_id: str
