"""Payments API — SetupIntent endpoint (B-1 Blue Bird sponsor flow).

POST /v1/payments/setup-intent
    Creates a Stripe SetupIntent so the frontend can collect and save a
    payment method with Stripe Elements (PCI-DSS Level 1 compliant).
    Returns a client_secret the frontend passes to stripe.confirmCardSetup().

Flow:
    1. Look up User.stripe_customer_id from DB.
    2. If missing, call provider.get_or_create_customer() and persist.
    3. Call provider.create_setup_intent(customer_id) → SetupIntent.
    4. Return {client_secret, customer_id, setup_intent_id}.

The BluebirdModal frontend uses this client_secret to call
stripe.confirmCardSetup() — no card data ever passes through our server
(PCI-DSS Level 1 delegation to Stripe).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.payments import SetupIntentRequest, SetupIntentResponse
from app.services.payments import get_payment_provider
from app.services.analytics import capture_event

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/setup-intent", response_model=None)
async def create_setup_intent(
    body: SetupIntentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("payments_setup_intent"),
):
    """Create a Stripe SetupIntent for off-session payment method collection.

    Used by BluebirdModal for both one-time and subscription flows.

    Returns:
        200: {data: {client_secret, customer_id, setup_intent_id}}
        401: Unauthenticated
        429: Rate limit exceeded (10/min/user)
    """
    provider = get_payment_provider()

    # ── 1. Get or create Stripe Customer ─────────────────────────────────
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer_id = await provider.get_or_create_customer(
            user_id=str(user.id),
            email=user.email,
        )
        user.stripe_customer_id = customer_id
        await db.commit()
        await db.refresh(user)

    # ── 2. Create SetupIntent ────────────────────────────────────────────
    metadata = dict(body.metadata or {})
    metadata.setdefault("user_id", str(user.id))

    si = await provider.create_setup_intent(
        customer_id=customer_id,
        metadata=metadata,
    )

    # G'-4: server-side SetupIntent success event (payment method collection initiated)
    capture_event(
        str(user.id),
        "setup_intent_succeeded",
        {"setup_intent_id": si.id, "customer_id": si.customer_id},
    )

    return {
        "data": SetupIntentResponse(
            client_secret=si.client_secret,
            customer_id=si.customer_id,
            setup_intent_id=si.id,
        ).model_dump()
    }
