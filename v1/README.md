# Domo Prototype (v1)

> 글로벌 신진 미술 작가를 위한 SNS · 후원 · 경매 플랫폼 — Phase 0 스캐폴딩

## 개요

Domo는 동남아·남미·동유럽의 신진 미술 작가들이 작품을 공유하고 후원받으며 경매를 통해 거래할 수 있는 글로벌 SNS 플랫폼입니다. 본 v1 디렉토리는 고객 커뮤니케이션용 **프로토타입**입니다.

자세한 설계 문서는 다음을 참조하세요.

- [Plan](docs/01-plan/plan.md)
- [Design Direction (두쫀쿠 테마)](docs/01-plan/design-direction.md)
- [Design (데이터 모델 / API / 화면)](docs/02-design/design.md)

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.12) + SQLAlchemy 2.0 (async) + Alembic |
| DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Auth | Google OAuth + JWT (Access 1h / Refresh 30d) |
| Push | Firebase Cloud Messaging (Phase 2~3) |
| Payment | Stripe (Phase 2) |
| Infra | Docker Compose on `100.75.139.86` |
| Domain | `*.tuzigroup.com` |

## 디렉토리 구조

```
v1/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── api/          # 라우터 (auth, posts, ...)
│   │   ├── core/         # 설정, 보안, 의존성, 에러
│   │   ├── db/           # SQLAlchemy 세션/베이스
│   │   ├── models/       # ORM 모델
│   │   ├── schemas/      # Pydantic 스키마
│   │   └── services/     # 비즈니스 로직 (Google OAuth 등)
│   ├── alembic/          # 마이그레이션
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/             # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/          # App Router 페이지
│   │   ├── components/
│   │   ├── lib/          # API 클라이언트
│   │   └── styles/       # Tailwind 글로벌 CSS
│   ├── tailwind.config.ts
│   └── Dockerfile
├── infra/                # 배포 관련 (추후 확장)
├── scripts/              # 시드/유틸 스크립트 (추후)
├── docs/                 # PDCA 문서
│   ├── 01-plan/
│   └── 02-design/
├── .github/workflows/    # CI/CD
├── docker-compose.yml
├── .env.example
└── README.md
```

## 서브도메인 전략

| 서브도메인 | 용도 |
|------------|------|
| `domo.tuzigroup.com` | 메인 웹 (프론트엔드) |
| `api.domo.tuzigroup.com` | 백엔드 API |
| `admin.domo.tuzigroup.com` | 관리자 페이지 |
| `cdn.domo.tuzigroup.com` | 미디어 CDN (추후) |

## 로컬 개발 환경 (권장 — Host 실행)

Backend(Python) / Frontend(Node)를 **호스트에서 직접 실행**하고, Postgres/Redis만 Docker 인프라로 사용하는 하이브리드 방식입니다. 코드 수정 → 핫 리로드 반응이 Docker full-stack보다 빠르고, 디버거 연결도 쉽습니다.

### 사전 요구 사항

| 도구 | 버전 | 설치 |
|------|------|------|
| Python | 3.12+ | `brew install python@3.12` |
| Node | 20+ | `brew install node@20` |
| Docker Desktop / OrbStack | 최신 | Postgres + Redis만 실행 |

### 빠른 시작

```bash
cd v1

# 1. 인프라 (postgres + redis)만 기동
./scripts/dev-infra.sh

# 2. 백엔드 실행 (venv 자동 생성 + 마이그레이션 + uvicorn)
./scripts/dev-backend.sh

# 3. 새 터미널에서 프론트엔드 실행 (npm install + next dev)
./scripts/dev-frontend.sh
```

### 접속

| URL | 용도 |
|-----|------|
| http://localhost:3700 | 프론트엔드 |
| http://localhost:3710/v1/health | 백엔드 헬스체크 |
| http://localhost:3710/docs | FastAPI Swagger |
| localhost:55432 | Postgres (user: `domo`, db: `domo`) |
| localhost:56379 | Redis |

### 유틸 스크립트

```bash
./scripts/dev-migrate.sh          # alembic upgrade head
./scripts/dev-migrate.sh current  # 현재 리비전
./scripts/dev-migrate.sh history  # 전체 이력

./scripts/dev-seed.sh             # base + demo 시드 (기본값)
./scripts/dev-seed.sh base        # base 시드만
./scripts/dev-seed.sh demo        # demo 시드만 (활성 경매/신고 케이스)

./scripts/dev-stop.sh             # postgres + redis 정지 (데이터 볼륨 유지)
```

### VSCode Task 사용

`v1/` 을 VSCode 워크스페이스로 열면 `Cmd+Shift+P → Tasks: Run Task`로 다음 태스크 사용 가능:

- **Domo: Dev All** — 인프라 + 백엔드 + 프론트엔드 동시 실행
- **Domo: Start Infra** — Postgres + Redis만 기동
- **Domo: Backend Dev Server** — 백엔드 단독
- **Domo: Frontend Dev Server** — 프론트엔드 단독
- **Domo: Migrate DB** — alembic upgrade head
- **Domo: Seed DB** — base + demo 시드
- **Domo: Stop Infra** — postgres/redis 정지
- **Domo: Reinstall Backend Deps** — venv 강제 재설치
- **Domo: Reinstall Frontend Deps** — node_modules 재설치

### VSCode 디버거

`F5`로 `Domo: Full Stack (backend + frontend)` compound 실행 시 백엔드 + 프론트엔드가 동시에 디버거에 붙습니다 (`v1/.vscode/launch.json`). 중단점 걸기 가능.

### 환경변수 (스크립트가 자동 설정)

| 변수 | 기본값 |
|------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://domo:domo_dev_pw@localhost:55432/domo` |
| `REDIS_URL` | `redis://localhost:56379/0` |
| `JWT_SECRET` | `local_dev_secret_change_me_in_production` |
| `FRONTEND_URL` | `http://localhost:3700` |
| `UPLOAD_DIR` | `<backend>/uploads` (호스트 로컬) |
| `PAYMENT_PROVIDER` | `mock_stripe` |
| `STORAGE_PROVIDER` | `local` |
| `EMAIL_PROVIDER` | `mock` |
| `RATE_LIMIT_MODE` | `enforce` |

환경변수를 덮어쓰려면 스크립트 실행 전에 export:

```bash
JWT_SECRET=$(openssl rand -hex 32) ./scripts/dev-backend.sh
```

---

## 대체: Docker Full-Stack 실행

Python/Node를 로컬에 설치하기 싫다면 전체 스택을 Docker로 실행할 수도 있습니다.

```bash
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
```

- 프론트엔드: http://localhost:3700
- 백엔드: http://localhost:3710/v1/health
- Postgres: localhost:55432
- Redis: localhost:56379

단, 파일 수정 시 핫 리로드 속도가 host 실행보다 느리고, 디버거 연결이 번거롭습니다. 따라서 **host 실행 방식을 권장**합니다.

## API 사용 예시

### Google 로그인 (개발 모드 — 모의 토큰)

```bash
curl -X POST http://localhost:8000/v1/auth/sns/google \
  -H "Content-Type: application/json" \
  -d '{"id_token": "mock:test@example.com"}'
```

응답:
```json
{
  "data": {
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    },
    "user": {
      "id": "uuid",
      "email": "test@example.com",
      "role": "user",
      ...
    }
  }
}
```

### 내 정보 조회

```bash
curl http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Phase 진행 상황

| Phase | 상태 | 내용 |
|-------|------|------|
| **Phase 0** (Week 1~2) | ✅ 진행 중 | Docker, FastAPI/Next.js 스캐폴딩, JWT, Google 로그인 |
| Phase 1 (Week 3~6) | ⏳ 예정 | 작가 심사, 피드, 사진 업로드, 프로필 |
| Phase 2 (Week 7~10) | ⏳ 예정 | 블루버드 후원, 경매, Stripe 결제 |
| Phase 3 (Week 11~12) | ⏳ 예정 | 영상, 정기 후원, 신고 처리, 시연 시나리오 |

## 디자인 시스템 (두쫀쿠 테마)

핵심 컬러:
- **Background**: `#1A1410` (다크 초콜릿)
- **Primary**: `#A8D76E` (피스타치오 그린)
- **Text**: `#F5EFE4` (크림 오프화이트)

자세한 토큰은 [docs/02-design/design.md §11](docs/02-design/design.md) 참조.

## 다음 작업

1. Phase 0 구동 확인 (docker compose up + alembic upgrade head)
2. Google OAuth 클라이언트 발급 후 `.env`에 등록
3. Phase 1 착수: posts, media, follows 모델 + 피드 API
