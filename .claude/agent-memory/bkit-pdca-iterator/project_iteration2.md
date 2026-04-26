---
name: Iteration 2 Major Wave (M1-M11)
description: 11 major gaps fixed in domo backend; migrations 0028+0029 added; reportlab dependency added
type: project
---

Completed PDCA Act Phase — Iteration 2 on 2026-04-24.

**Why:** Gap analysis showed 11 Major items blocking production readiness (92% match rate).

**How to apply:** Next iteration (if needed) should focus on remaining Minor gaps (N1-N9) and wiring artwork_title/artist_name properly in email templates (currently passing IDs as placeholders).

Changes made:
- M1: POST /media/presign + POST /media/finalize; presign_post() on StorageProvider ABC, S3, LocalStorage
- M2: 4 email templates (payment_receipt, auction_won, account_deleted, warning_issued); wired to webhooks/auctions/me/moderation
- M3/M11: gdpr_export rate limit → 1/24h via @rate_limit("gdpr_export") in DEFAULT_LIMITS
- M4: guardian.withdraw_consent cascade: hides posts, cancels auctions, cancels subscriptions
- M5: CommunityComment model + migration 0028; 3 endpoints in communities.py
- M6: community_jobs.py seed_default_communities(); registered in main.py lifespan
- M7: GET /orders/{id}/tracking endpoint in orders.py (uses existing services/shipping.py)
- M8: GET /admin/reports/school/{school_name}/pdf via reportlab; added reportlab>=4.2 to pyproject.toml
- M9: Order status inspection_complete intermediate state; settlement_jobs queries inspection_complete, sets settled; orders.py sets inspection_complete not settled
- M10: users.stripe_customer_id column; stripe_price_cache table; migration 0029; create_subscription uses cache when db passed
- M11: same as M3 (confirmed @rate_limit applied)
