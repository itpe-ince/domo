# Phase 13 C-2: K-6 v2 ML 회귀 모델 설계 (알고리즘 설계 단계)

---

## 문서 상태

| 항목 | 내용 |
|------|------|
| **단계** | 알고리즘 설계만 (코드 구현 없음) |
| **진입 조건** | 거래 ≥ 500건 — 현재 미충족 (보수적 가정 < 500건) |
| **구현 이월** | Phase 14 (거래 ≥ 500건 도달 시 진입) |
| **alembic** | 0090 미생성 (Phase 14 진입 시 생성) |
| **작성일** | 2026-05-09 |
| **carry-over** | Phase 12 §10 → Phase 13 C-2 (#7, Could) |

---

## 1. 진입 조건 및 의사결정

### 1.1 거래 카운트 기반 분기

```sql
-- C-2 진입 전 실행 (Phase 14 시작 시 재확인)
SELECT COUNT(*) AS sold_count
FROM auctions
WHERE status = 'sold';
```

| 결과 | 행동 |
|------|------|
| `sold_count >= 500` | C-2 구현 진입 (ML 회귀 모델 학습 + API 구현) |
| `sold_count < 500` | 설계 단계만 수행 + Phase 14 이월 (현재 상태) |

### 1.2 현재 상태 (Phase 13 Wave C)

- Phase 12 기준 거래 약 50~70건 수준 (보수적 가정)
- 500건 기준에 크게 미달 → **알고리즘 설계 단계만 수행**
- 코드 구현, alembic 마이그레이션, sklearn 의존성 추가 일체 없음

### 1.3 Graceful Fallback 전략 (현재 운영 중)

거래 < 500건이거나 ML 모델 미배포 상태에서는 기존 K-6 v1 단순 평균가를 유지한다.

```
현재 K-6 v1 (단순 평균가):
  recommended_price = (comparable_avg * 0.6) + (artist_avg * 0.4)
  comparable: 동일 장르 + 유사 사이즈 최근 90일 낙찰가 평균
  artist: 해당 작가 최근 1년 낙찰가 평균
```

K-6 v1은 Phase 13 B-1k (또는 B-2)에서 구현된 `POST /artworks/{id}/recommend-price` 엔드포인트를 그대로 유지한다.

---

## 2. 알고리즘 설계

### 2.1 모델 선택 근거

| 단계 | 모델 | 이유 |
|------|------|------|
| 1단계 (Phase 14) | scikit-learn LinearRegression | 해석 가능성 높음, 소규모 데이터(500~2000건)에서 충분한 정확도, 의존성 경량 |
| 2단계 (Phase 14+ 조건부) | RandomForestRegressor | Linear 모델 R² < 0.6 지속 시 비선형 관계 포착 목적으로 전환 |

LinearRegression을 먼저 시도하는 이유:

1. 작품 가격 결정 요인(작가 등급, 사이즈, 팔로워 등)은 대체로 단조적 관계 → 선형 모델로 주요 분산 설명 가능
2. 거래 500~2000건 수준에서는 과적합 위험이 낮음
3. 예측 결과의 feature_importance가 직관적 → 운영자 신뢰도 확보
4. 학습/예측 속도가 빠름 → 주 1회 cron 학습 부담 없음

### 2.2 Feature Engineering

#### 입력 피처 (X) — 8개

| # | 피처 이름 | 원천 필드 | 전처리 방법 |
|:-:|----------|---------|-----------|
| 1 | `artist_tier` | `users.tier` (bronze/silver/gold/platinum) | one-hot encoding (4열) |
| 2 | `media_type` | `posts.media_type` (photo/video) | one-hot encoding (2열) |
| 3 | `artwork_size_log` | `posts.width * posts.height` (pixels) 또는 video `posts.duration` (seconds) | `log1p(width * height)` 또는 `log1p(duration)` |
| 4 | `follower_count_log` | `users.follower_count` | `log1p(follower_count)` |
| 5 | `avg_likes_90d_log` | `likes` 집계 (최근 90일 작품 평균 좋아요) | `log1p(avg_likes)` |
| 6 | `sold_count_log` | `users.sold_count` | `log1p(sold_count)` |
| 7 | `artwork_category` | `posts.category` (회화/조각/디지털/사진/기타) | one-hot encoding (5열) |
| 8 | `artist_activity_days` | `users.created_at` → 가입 후 일수 | StandardScaler 정규화 |

#### 로그 변환 적용 이유

작품 가격, 팔로워 수, 좋아요 수는 right-skewed 분포(소수의 고가/인기 작품이 평균을 왜곡)이므로 `log1p` 변환으로 분포를 정규화한다. 이 과정에서 0값도 안전하게 처리된다(`log1p(0) = 0`).

#### 타깃 변수 (y)

```
y = log1p(sold_price_usd)
예측 후 역변환: predicted_price = expm1(y_hat)
```

### 2.3 Feature 벡터 예시

```python
# 입력 예시 (silver 등급 작가, photo 미디어, 1024×768 사이즈)
X = {
    "artist_tier_bronze":    0,
    "artist_tier_silver":    1,   # one-hot
    "artist_tier_gold":      0,
    "artist_tier_platinum":  0,
    "media_type_photo":      1,   # one-hot
    "media_type_video":      0,
    "artwork_size_log":      13.56,  # log1p(1024*768) ≈ 13.56
    "follower_count_log":    6.91,   # log1p(1000)
    "avg_likes_90d_log":     3.91,   # log1p(49)
    "sold_count_log":        2.40,   # log1p(10)
    "category_painting":     0,
    "category_sculpture":    0,
    "category_digital":      1,   # one-hot
    "category_photo":        0,
    "category_other":        0,
    "artist_activity_days":  0.87,   # StandardScaler 정규화 후
}
# y = log1p(45000) ≈ 10.71  → 역변환: expm1(10.71) ≈ 44991 USD
```

---

## 3. 학습 파이프라인

### 3.1 학습 데이터 조건

```sql
-- 학습에 사용할 데이터 쿼리 (Phase 14 구현 시 참고)
SELECT
    a.sold_price,
    u.tier,
    p.media_type,
    p.width,
    p.height,
    p.duration,
    u.follower_count,
    u.sold_count,
    p.category,
    EXTRACT(EPOCH FROM (NOW() - u.created_at)) / 86400 AS activity_days,
    (
        SELECT COALESCE(AVG(like_count), 0)
        FROM (
            SELECT COUNT(*) AS like_count
            FROM likes l
            JOIN posts p2 ON l.post_id = p2.id
            WHERE p2.user_id = u.id
              AND l.created_at >= NOW() - INTERVAL '90 days'
            GROUP BY l.post_id
        ) subq
    ) AS avg_likes_90d
FROM auctions a
JOIN posts p ON a.post_id = p.id
JOIN users u ON p.user_id = u.id
WHERE a.status = 'ended'
  AND a.sold_price IS NOT NULL
  AND a.ended_at >= NOW() - INTERVAL '12 months'
ORDER BY a.ended_at DESC;
```

- **기간**: 최근 12개월 낙찰 거래
- **조건**: `status = 'ended'`, `sold_price IS NOT NULL`
- **최소 샘플**: 500건 (미달 시 모델 학습 skip)

### 3.2 학습 빈도 및 스케줄

| 항목 | 설정 |
|------|------|
| 주기 | 주 1회 |
| 실행 시각 | 월요일 03:00 UTC |
| cron 번호 | 26번째 (Phase 14 추가 시) |
| worker 이름 | `train_price_recommendation_model` |

### 3.3 모델 Artifact 저장

```
저장 위치 (우선순위):
  1순위: AWS S3 (운영 환경)
     s3://{BUCKET}/ml-models/k6/v{version}/model.pkl
  2순위: 로컬 디스크 (개발/스테이징 환경)
     /app/ml_artifacts/k6/v{version}/model.pkl

직렬화: joblib.dump(model, artifact_path)
로드:   model = joblib.load(artifact_path)
```

### 3.4 학습 파이프라인 흐름 (Phase 14 구현 참고)

```
[월요일 03:00 UTC]
    │
    ▼
1. DB 쿼리 → 최근 12개월 sold 거래 fetch
    │
    ▼
2. 샘플 카운트 확인
   ├── < 500건 → skip + Slack alert("학습 데이터 부족: {n}건") → 종료
   └── ≥ 500건 → 계속
    │
    ▼
3. Feature Engineering
   - one-hot encoding (tier, media_type, category)
   - log1p 변환 (size, follower, likes, sold_count)
   - StandardScaler 정규화 (activity_days)
   - y = log1p(sold_price)
    │
    ▼
4. Train/Val Split (80/20)
    │
    ▼
5. LinearRegression 학습
    │
    ▼
6. 평가 (Val set)
   - R² 계산
   - MAE 계산
   ├── R² < 0.5 → alert("모델 품질 미달: R²={r2:.3f}") → 배포 skip
   └── R² ≥ 0.5 → 계속
    │
    ▼
7. Artifact 저장 (S3 / 로컬)
    │
    ▼
8. ml_model_metadata INSERT
   (model_version, trained_at, r2_score, n_samples, feature_importance, artifact_path)
    │
    ▼
9. cron_status 업데이트 (Redis hash)
```

---

## 4. 예측 API

### 4.1 Endpoint

```
POST /artworks/{id}/recommend-price
```

기존 K-6 v1 위치를 유지한다. 분기 로직만 내부에 추가된다.

### 4.2 분기 로직

```
[POST /artworks/{id}/recommend-price 호출]
    │
    ▼
1. ml_model_metadata에서 최신 모델 버전 조회
   - model_version, r2_score, artifact_path
    │
    ▼
2. 분기 조건 확인
   ├── 모델 없음                      → fallback (method="simple_avg")
   ├── r2_score < 0.6                 → fallback (method="simple_avg")
   ├── n_samples < 500                → fallback (method="simple_avg")
   └── 모델 정상 (r2 ≥ 0.6)          → ML 예측 (method="ml")
    │
    ▼
3a. [ML 예측]
    - 작품/작가 피처 조회
    - Feature vector 구성 + log1p 변환
    - model.predict([X]) → y_hat
    - predicted_price = clip(expm1(y_hat), 10, 100000)
    │
3b. [Fallback: 단순 평균가]
    - comparable_avg (동일 장르 최근 90일)
    - artist_avg (작가 최근 1년)
    - recommended = comparable_avg * 0.6 + artist_avg * 0.4
    │
    ▼
4. 응답 반환
```

### 4.3 응답 스키마

```json
{
  "recommended_price": 42500.00,
  "confidence": 0.73,
  "method": "ml",
  "metadata": {
    "model_version": "v3",
    "r2_score": 0.73,
    "feature_values": {
      "artist_tier": "silver",
      "media_type": "photo",
      "follower_count": 1200,
      "sold_count": 8
    }
  }
}
```

```json
{
  "recommended_price": 38000.00,
  "confidence": null,
  "method": "simple_avg",
  "metadata": {
    "comparable_avg": 42000.00,
    "artist_avg": 32000.00,
    "fallback_reason": "insufficient_training_data"
  }
}
```

| `method` 값 | 조건 |
|------------|------|
| `"ml"` | ML 모델 R² ≥ 0.6 + 거래 ≥ 500건 |
| `"simple_avg"` | 그 외 모든 경우 (모델 없음 / R² 미달 / 데이터 부족) |

### 4.4 Prediction Outlier 처리

```python
# 예측값 범위 클리핑 (음수/극단값 방지)
predicted_price = float(np.clip(np.expm1(y_hat), 10.0, 100_000.0))
```

| 경계 | 값 | 근거 |
|------|:--:|------|
| min | 10 USD | 최소 의미있는 작품 가격 |
| max | 100,000 USD | 신진 작가 최고가 상한선 |

---

## 5. 평가 지표 (KPI)

| 지표 | 목표 | 측정 시점 |
|------|:----:|---------|
| R² (Validation set) | ≥ 0.6 | 매주 학습 후 |
| MAE | ≤ 평균가의 10% | 매주 학습 후 |
| 학습 샘플 수 | ≥ 500건 | 학습 전 체크 |
| 모델 배포 성공률 | 100% (학습 성공 시) | cron 실행 후 |
| Fallback 발생률 | 모니터링 (목표 < 30%) | Phase 14 운영 후 |

### KPI 미달 시 대응

| 조건 | 대응 |
|------|------|
| R² < 0.5 | 모델 미배포 + Slack alert + 단순 평균가 유지 |
| R² 0.5~0.6 | 배포는 하되 fallback 우선 (threshold=0.6) |
| MAE > 평균가의 10% | Phase 14 RandomForest 전환 검토 |
| 학습 샘플 < 500 | 학습 skip + alert, 다음 주 재시도 |

---

## 6. alembic 0090 DDL (Phase 14 진입 시 사용)

Phase 14 구현 시 아래 DDL을 그대로 사용한다.

```sql
-- alembic 0090: ml_model_metadata 테이블
CREATE TABLE ml_model_metadata (
    id                  SERIAL PRIMARY KEY,
    model_version       VARCHAR(20) NOT NULL,        -- 'v1', 'v2', ...
    model_type          VARCHAR(50) NOT NULL,         -- 'linear_regression' | 'random_forest'
    trained_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    train_samples_count INTEGER NOT NULL,
    val_samples_count   INTEGER NOT NULL,
    r2_score            DECIMAL(5, 4) NOT NULL,       -- 0.0000 ~ 1.0000
    mae_usd             DECIMAL(10, 2) NOT NULL,
    feature_names       JSONB NOT NULL,               -- ["artist_tier_silver", ...]
    feature_importance  JSONB NULLABLE,               -- {"artist_tier_silver": 0.23, ...}
    artifact_path       TEXT NOT NULL,                -- s3://... 또는 /app/ml_artifacts/...
    is_deployed         BOOLEAN NOT NULL DEFAULT FALSE,
    deployed_at         TIMESTAMPTZ NULLABLE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_ml_model_metadata_trained_at   ON ml_model_metadata (trained_at DESC);
CREATE INDEX idx_ml_model_metadata_is_deployed  ON ml_model_metadata (is_deployed) WHERE is_deployed = TRUE;
```

### DDL 설계 의도

| 컬럼 | 의도 |
|------|------|
| `model_version` | v1/v2/... 수동 버전 관리, 롤백 시 이전 버전 참조 |
| `feature_names` | JSONB로 피처 목록 저장 → 피처 변경 이력 추적 |
| `feature_importance` | LinearRegression의 `coef_` 저장 (RandomForest는 `.feature_importances_`) |
| `is_deployed` | 현재 서빙 중인 모델 단일 구분 |
| `artifact_path` | S3 또는 로컬 경로 통합 (환경별 prefix로 구분) |

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 대응 방안 |
|--------|:----:|---------|
| sklearn 미설치 | 예측 API 오류 | `try/except ImportError` → graceful fallback (단순 평균가 자동 전환) |
| 학습 데이터 < 500건 | 모델 품질 부족 | 학습 skip + Slack alert, 단순 평균가 유지 |
| Prediction outlier (음수/극단값) | 신뢰도 손상 | `clip(min=10 USD, max=100,000 USD)` 강제 적용 |
| 모델 drift (R² 점진 하락) | 추천 정확도 저하 | 매주 학습 후 R² 모니터링, R² < 0.5이면 Slack alert + 배포 skip |
| S3 artifact 업로드 실패 | 모델 갱신 불가 | 로컬 디스크 fallback 저장 + 다음 주 재시도 |
| 피처 누락 (작가 신규 등록) | 예측 불가 | 누락 피처 → 해당 필드 평균값으로 대체 (mean imputation) |
| right-skewed 가격 분포 | LinearRegression 편향 | log1p 타깃 변환으로 완화 (설계에 반영 완료) |

---

## 8. Phase 14 이월 항목 체크리스트

다음 항목들은 거래 ≥ 500건 도달 시 Phase 14에서 구현한다.

- [ ] alembic 0090 `ml_model_metadata` 테이블 생성 (위 DDL 참고)
- [ ] sklearn 의존성 추가
  ```
  scikit-learn>=1.4
  joblib>=1.3
  ```
  `v1/backend/requirements.txt` 또는 `pyproject.toml`에 추가
- [ ] 학습 cron worker 구현
  `v1/backend/app/services/k6_train_cron.py`
  - 데이터 쿼리 → Feature Engineering → LinearRegression 학습 → 평가 → S3 저장 → metadata INSERT
  - cron 스케줄: 월요일 03:00 UTC (26번째 cron)
- [ ] 예측 서비스 구현
  `v1/backend/app/services/k6_predict.py`
  - artifact 로드 (S3/로컬 분기)
  - Feature vector 구성 함수
  - predict() → clip → expm1 역변환
- [ ] 예측 API 업데이트
  `v1/backend/app/api/k6_predict.py` (또는 기존 recommend_price 라우터)
  - ML 분기 로직 주입 (§4.2 분기 기준)
- [ ] 모델 artifact 저장/로드 유틸리티
  `v1/backend/app/utils/ml_artifact.py`
  - S3 presigned PUT / GET 또는 boto3 직접 업로드
  - 로컬 디스크 fallback (개발 환경)
- [ ] Admin 모델 관리 페이지 (선택)
  `/admin/ml/models` — 모델 버전 목록, R² 히스토리, 수동 학습 트리거 버튼
- [ ] 회귀 테스트 (예측 정확도 baseline)
  - `tests/test_k6_ml.py`
  - 샘플 500건 fixtures 기반 R² ≥ 0.6 검증
  - graceful fallback 동작 테스트 (`SKLEARN_ENABLED=0` env)
  - outlier clip 테스트 (음수 예측값 → 10 USD)
  - predict API 응답 스키마 검증

---

## 9. Phase 14 이월 공지

본 설계는 Phase 13 C-2에서 알고리즘 설계 단계만 수행한다.

현재 거래 건수가 진입 조건(≥ 500건)에 미달하므로 코드 구현, alembic 마이그레이션, sklearn 의존성 추가는 일체 수행하지 않는다.

거래 ≥ 500건 도달이 확인되는 시점에 Phase 14에서 §8 체크리스트를 순서대로 구현한다. 그 전까지는 기존 K-6 v1 단순 평균가(`method="simple_avg"`)를 운영 유지한다.
