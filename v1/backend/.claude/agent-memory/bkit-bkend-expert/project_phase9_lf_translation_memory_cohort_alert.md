---
name: Phase 9 L-F Translation Memory + Cohort Alert
description: L-F 완료: alembic 0071+0072, 번역 메모리 DB+Redis, cohort_alert 14번째 cron, 17 tests
type: project
---

Phase 9 L-F 완료: 번역 메모리 + Cohort Retention 자동 Slack 알림

**Why:** LLM Gateway 번역 중복 호출 비용 절감(목표 60%↓) + D7/D30 retention 임계치 미달 시 팀 자동 알림

**How to apply:** 다음 Phase에서 번역 캐시 hit rate 모니터링 필요 (translation_cache.hit_count 합산)

## alembic
- 0071_translation_cache: source_hash+source_lang+target_lang UNIQUE INDEX, last_used_at index (90일 cleanup용)
- 0072_cohort_alerts: cohort_date+metric_name UNIQUE INDEX, metric_name+created_at index (cooldown 조회)
- down_revision 체인: 0071→0070, 0072→0071

## 신규 파일
- app/models/translation_cache.py (TranslationCache)
- app/models/cohort_alert.py (CohortAlert)
- app/services/translation_cache.py (get_cached_translation, save_translation, cleanup_old_cache_entries)
- app/services/cohort_alert_jobs.py (check_and_alert_once, cohort_alert_cron_loop)
- tests/unit/test_translation_cache.py (9 tests)
- tests/unit/test_cohort_alert_jobs.py (8 tests)

## 수정 파일
- app/services/story_translator.py: translate_bio_to_all_locales에 DB+Redis 2-tier 캐시 통합
  - get_cached_translation(db, text, src, tgt) + save_translation(...) 호출
  - translate_milestone_text: in-memory 캐시 유지 (OQ-L-F-2 결정)
- app/models/__init__.py: TranslationCache, CohortAlert 추가
- app/core/config.py: slack_webhook_url, cohort_alert_*_threshold, cohort_alert_min_cohort_size 추가
- app/main.py: 14번째 cron worker cohort_alert_task 등록 (COHORT_ALERT_WORKER_ENABLED env guard)

## 설계 결정
- OQ-L-F-2: translate_milestone_text DB session 없음 → in-memory 캐시 유지
- OQ-L-F-3: cleanup_old_cache_entries는 별도 cron 아닌 gdpr_cron_loop 통합 권장 (함수 제공)
- OQ-L-F-4: Mock 번역 결과(model_version='mock-gateway') DB 저장함 → 프로덕션 전환 시 DELETE
- SLACK_WEBHOOK_URL 미설정 시 Mock 모드: cohort_alerts에 status='sent'로 INSERT해 cooldown 동작
- cleanup_old_cache_entries: gdpr_cron_loop 내 통합 호출 예정 (본 Phase에서 연결 미포함)
