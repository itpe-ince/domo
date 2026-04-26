"""Admin API package.

Assembles all admin sub-routers into a single FastAPI router with prefix /admin.
main.py imports this package as ``from app.api import admin as admin_router``
and registers ``admin_router.router`` — behaviour is unchanged.

Sub-modules:
  users.py        — artist applications + user CRUD
  schools.py      — school management
  content.py      — post moderation, digital-art verdicts, reports/warnings
  transactions.py — auctions, orders, refunds
"""
from fastapi import APIRouter

from app.api.admin import content, schools, transactions, users

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(users.router)
router.include_router(schools.router)
router.include_router(content.router)
router.include_router(transactions.router)
