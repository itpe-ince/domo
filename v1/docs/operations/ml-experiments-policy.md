# ML 실험 운영 정책 및 KPI 측정 가이드

> CO-1 PR-6: ml_experiments 보존 정책 + K-1/K-3/K-5 운영 14일 후 KPI 측정 명령어.
> 작성일: 2026-05-05. 대상: 운영팀, 백엔드 개발자.

---

## 1. ml_experiments 테이블 보존 정책

### 보존 원칙

| 단계 | 기간 | 내용 |
|------|------|------|
| 실험 진행 중 | 실험 기간 전체 | 전체 레코드 보존 (assignment + event) |
| 실험 종료 후 | 90일 | 원본 레코드 보존 (통계 분석 충분 기간) |
| 90일 초과 | 즉시 | 집계 통계 요약 후 원본 삭제 또는 cold storage 이동 |

- **90일 보존 이유**: A/B 테스트 통계 유의성 검증, 사후 분석, 감사(audit) 요건 충족
- **삭제 전 집계**: `ml_experiment_assignments` 집계 통계를 `ml_experiments.result_summary` (JSONB)에 저장
- **Phase 11 예정**: scheduled cleanup cron job 구현 (자동 archive → 삭제)

### 수동 삭제 명령 (90일 경과 완료 실험)

```sql
-- 1단계: 삭제 대상 확인
SELECT e.experiment_id, e.name, e.ended_at,
       COUNT(a.id) as assignment_count
FROM ml_experiments e
JOIN ml_experiment_assignments a ON a.experiment_id = e.experiment_id
WHERE e.status = 'completed'
  AND e.ended_at < NOW() - INTERVAL '90 days'
GROUP BY e.experiment_id, e.name, e.ended_at
ORDER BY e.ended_at;

-- 2단계: assignment 삭제 (실험 종료 후 90일 경과)
DELETE FROM ml_experiment_assignments
WHERE experiment_id IN (
  SELECT experiment_id FROM ml_experiments
  WHERE status = 'completed'
    AND ended_at < NOW() - INTERVAL '90 days'
);

-- 3단계: 실험 레코드 자체는 영구 보존 (요약 데이터만 남김)
-- ml_experiments 레코드는 삭제하지 않음 (감사 추적 목적)
```

### K-8 A/B 테스트 종료 절차

1. 통계적 유의성 p < 0.05 달성 또는 14일 경과 후 결정
2. PostHog Experiment 종료 → feature flag 고정
3. `ml_experiments.status = 'completed'`, `ended_at = NOW()` 업데이트
4. 결과 요약을 `result_summary` JSONB 컬럼에 기록

```sql
-- 실험 종료 처리
UPDATE ml_experiments
SET status = 'completed',
    ended_at = NOW(),
    result_summary = '{
      "winning_variant": "v2",
      "p_value": 0.031,
      "primary_metric": "feed_ctr",
      "lift": 0.12
    }'::jsonb
WHERE experiment_id = '<experiment_id>';
```

---

## 2. ml_experiments 테이블 상태 확인

```bash
# 전체 실험 목록 + assignment 수 확인
psql $DATABASE_URL -c "
  SELECT e.experiment_id, e.name, e.status,
         e.started_at::date, e.ended_at::date,
         (SELECT COUNT(*) FROM ml_experiment_assignments a
          WHERE a.experiment_id = e.experiment_id) as assignments
  FROM ml_experiments e
  ORDER BY e.started_at DESC;"
```

---

## 3. K-1/K-3/K-5 운영 14일 후 KPI 측정 명령

### K-1: ML 피드 interaction 누적 확인

```bash
# 14일간 누적 interaction 수 / 유니크 사용자 수 / 유니크 포스트 수
psql $DATABASE_URL -c "
  SELECT COUNT(*) AS total_interactions,
         COUNT(DISTINCT user_id) AS unique_users,
         COUNT(DISTINCT post_id) AS unique_posts,
         AVG(CASE WHEN interaction_type = 'like' THEN 1.0 ELSE 0.0 END) AS like_rate,
         AVG(CASE WHEN interaction_type = 'view' THEN 1.0 ELSE 0.0 END) AS view_rate
  FROM user_post_interactions
  WHERE created_at > NOW() - INTERVAL '14 days';"
```

**목표 KPI**:
- 피드 CTR (클릭/노출) +10% 이상 (A/B test v1 vs v2 비교)
- 1인당 일 평균 interaction 수 전주 대비 증가

```bash
# A/B test 그룹별 CTR 비교 (K-8 연계)
psql $DATABASE_URL -c "
  SELECT a.variant,
         COUNT(DISTINCT i.user_id) AS users,
         COUNT(i.id) AS interactions,
         ROUND(COUNT(i.id)::numeric / NULLIF(COUNT(DISTINCT i.user_id), 0), 2) AS avg_per_user
  FROM ml_experiment_assignments a
  LEFT JOIN user_post_interactions i ON i.user_id = a.user_id
    AND i.created_at > a.assigned_at
    AND i.created_at > NOW() - INTERVAL '14 days'
  JOIN ml_experiments e ON e.experiment_id = a.experiment_id
  WHERE e.name = 'feed-algorithm-v2'
    AND e.status IN ('active', 'completed')
  GROUP BY a.variant;"
```

### K-3: AI 캡션 생성률 확인

```bash
# 이미지 포스트 중 AI 캡션 보유 비율
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE ai_caption IS NOT NULL) AS captioned,
    COUNT(*) FILTER (WHERE ai_caption IS NULL) AS pending,
    COUNT(*) AS total,
    ROUND(
      100.0 * COUNT(*) FILTER (WHERE ai_caption IS NOT NULL) / NULLIF(COUNT(*), 0), 1
    ) AS coverage_pct
  FROM posts
  WHERE media_type = 'image'
    AND status != 'deleted';"

# caption_override 사용률 (K-3 수동 오버라이드 기능 사용 현황)
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE caption_override IS NOT NULL) AS manual_override_count,
    COUNT(*) FILTER (WHERE caption_override IS NULL AND ai_caption IS NOT NULL) AS ai_only_count,
    COUNT(*) AS total_with_caption
  FROM posts
  WHERE (ai_caption IS NOT NULL OR caption_override IS NOT NULL)
    AND status != 'deleted';"
```

**목표 KPI**:
- 이미지 포스트 AI 캡션 커버리지 80% 이상
- caption_override 사용률 추이 (작가 참여도 지표)

### K-5: 도슨트 생성률 + opt-out 비율 확인

```bash
# 전체 포스트 도슨트 현황
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE ai_docent_text IS NOT NULL) AS with_ai_docent,
    COUNT(*) FILTER (WHERE artist_docent_text IS NOT NULL) AS with_artist_docent,
    COUNT(*) FILTER (WHERE ai_docent_opted_out = true) AS opted_out,
    COUNT(*) AS total,
    ROUND(
      100.0 * COUNT(*) FILTER (WHERE ai_docent_text IS NOT NULL) / NULLIF(COUNT(*), 0), 1
    ) AS ai_docent_pct,
    ROUND(
      100.0 * COUNT(*) FILTER (WHERE ai_docent_opted_out = true) / NULLIF(COUNT(*), 0), 1
    ) AS opt_out_pct
  FROM posts
  WHERE status != 'deleted';"

# 도슨트 생성 14일 트렌드
psql $DATABASE_URL -c "
  SELECT DATE(ai_docent_generated_at) AS date,
         COUNT(*) AS generated
  FROM posts
  WHERE ai_docent_generated_at > NOW() - INTERVAL '14 days'
    AND status != 'deleted'
  GROUP BY DATE(ai_docent_generated_at)
  ORDER BY date;"
```

**목표 KPI**:
- AI 도슨트 생성 포스트 비율 50% 이상 (14일 내 신규 포스트 기준)
- opt-out 비율 10% 이하 (작가 신뢰도 지표)
- 작가 직접 해설 작성 포스트 수 전주 대비 증가

---

## 4. Prometheus / PostHog 연계 측정 (선택)

```bash
# PostHog: K-8 A/B 실험 결과 조회 (PostHog CLI 또는 API)
# https://posthog.com/docs/experiments/api

# 실험 결과 확인 (PostHog Web UI)
# App → Experiments → "feed-algorithm-v2" → Results 탭
# 지표: Conversion rate, Confidence interval, p-value

# Prometheus: 피드 레이턴시 p99 (K-1 성능 회귀 없음 확인)
# prometheus_url/api/v1/query?query=histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{endpoint="/posts/feed"}[14d]))
```

---

## 5. 운영 체크리스트 (배포 14일 후)

- [ ] K-1 interaction 누적 SQL 실행 → 목표 대비 달성률 확인
- [ ] K-3 AI 캡션 커버리지 80% 이상 확인
- [ ] K-5 도슨트 생성률 50% 이상 확인 + opt-out < 10%
- [ ] K-8 A/B 테스트 p-value 확인 → 유의미한 경우 feature flag 고정
- [ ] ml_experiments 상태 확인 → completed 실험 ended_at 기록
- [ ] 90일 경과 실험 있으면 manual cleanup 실행

---

## Version History

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| 0.1 | 2026-05-05 | CO-1 PR-6 초안. ml_experiments 90일 보존 정책 + K-1/K-3/K-5 KPI 측정 명령어 |
