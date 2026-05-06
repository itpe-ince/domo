# Memory Index

## Project
- [Phase 5 D-6 Observability Baseline](project_phase5_d6_observability.md) — D-6 완료: prometheus metrics, health/ready, /metrics endpoint, cron 4개 통합, 114 tests passing
- [Phase 6 D'-5 Prometheus Deployment](project_phase6_dp5_prometheus_deployment.md) — D'-5 완료: Grafana dashboard JSON 7패널, alerts.yml 5개, metrics-security.md, observability.md v0.2 Production Checklist
- [Phase 6 D'-2 Subscription Cancellation Tracking](project_phase6_dp2_cancel_tracking.md) — D'-2 완료: alembic 0044, cancel body+HTML sanitize+audit log, GET /churn endpoint, ChurnList color-coded badge, 6 tests
- [Phase 6 D'-3 Stripe Coupon Foundation](project_phase6_dp3_stripe_coupon.md) — D'-3 완료: alembic 0046, CouponProvider ABC+Mock+Stripe, 5 endpoints, SubscriptionCard badge, 13 tests. B-5 winback carry-over.
- [Phase 6 A-8 Retention Loop Enhancement](project_phase6_a8_retention_loop.md) — A-8 완료: alembic 0048, subscription_expiry_jobs cron, ExpiryBanner, WinbackBanner B-5 booster, 5 PostHog events, 30 i18n entries, 7 new tests
- [Phase 6 A-5 Search Enhancement](project_phase6_a5_search_enhancement.md) — A-5 완료: alembic 0049_search_history, SearchHistory 모델, /search v2 + popular + history CRUD, 8 unit tests, search.v2.* i18n 95키, PostHog 3 events
- [Phase 8 G''-2 Redis Cache Layer](project_phase8_gpp2_redis_cache.md) — G''-2 완료: CacheClient+Mock fallback, 4 cache 영역, cron invalidation, 4 metrics, 9+5 tests, redis-cache.md ops guide
- [Phase 8 G''-3 N+1 Audit](project_phase8_gpp3_n_plus_one_audit.md) — G''-3 완료: 18쿼리 CI gate, N+1 0건(이미 최적화), 0059 3 indexes, 4 tests, db-performance.md
- [Phase 8 G''-1 OpenTelemetry Tracing](project_phase8_gpp1_otel_tracing.md) — G''-1 완료: OTel SDK+6패키지, 8 cron span, 5 critical op span, G'-4 trace_id booster, 6 tests, opentelemetry.md
- [Phase 8 H'-4 Click Tracking RSS Thumbnail](project_phase8_hp4_click_tracking.md) — H'-4 완료: MediaCoverageClickEvent url+source, UserMediaCoverage onClick, POST /click 60/min/IP, 8→11 tests. RSS+thumbnail carry-over.
- [Phase 8 H'-5 SES Bounce Handling](project_phase8_hp5_ses_bounce.md) — H'-5 완료: 0060 alembic, SNS webhook+sig verify, hard/soft/complaint handlers, 6 tests, newsletter-bounce.md
- [Phase 8 H'-2 CJK Font PDF Embedding](project_phase8_hp2_cjk_font.md) — H'-2 완료: font_registry.py, download_cjk_fonts.sh, press_kit_generator locale→font 주입, 8 tests, cjk-font-embedding.md
- [Phase 8 B'-2 DM Messaging](project_phase8_bp2_dm_messaging.md) — B'-2 완료: alembic 0063, 9 endpoints(8+1 admin), 11 tests, 75 i18n, Notification.type=dm_received, polling model
- [Phase 8 B'-3 Push Email Digest Foundation](project_phase8_bp3_push_email_digest.md) — B'-3 완료: alembic 0064, FCM+APNs Mock, push_notifier, email_digest 10th cron, 4 endpoints, 15 tests, 75 i18n
- [Phase 9 L-B External Content Booster](project_phase9_lb_external_content.md) — L-B 완료: alembic 0067, rss_fetch 13번째 cron, og_scraper LRU, newsletter tracking 2 API, inject_tracking, 16 tests
- [Phase 9 L-F Translation Memory + Cohort Alert](project_phase9_lf_translation_memory_cohort_alert.md) — L-F 완료: alembic 0071+0072, 번역 메모리 DB+Redis 2-tier, cohort_alert 14번째 cron, 17 tests
- [Phase 9 L-C DM Expansion](project_phase9_lc_dm_expansion.md) — L-C 완료: alembic 0068+0069, Group DM 3테이블, ConnectionManager+RedisConnectionManager, WS /ws/dm, 9 endpoints, 23+13 tests
