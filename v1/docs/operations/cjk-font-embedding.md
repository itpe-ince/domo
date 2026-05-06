# CJK Font Embedding — Operations Guide

Phase H'-2. Press kit PDF 한국어/일본어/중국어 글자 깨짐 수정.

## 문제 배경

C-2 PressKit + C-5 Newsletter PDF는 reportlab 기본 폰트 Helvetica를 사용했다.
Helvetica는 Latin-1(서유럽 문자) 범위만 커버하므로 CJK 문자(한글, 한자, 가나)는
모두 `?`로 렌더링되었다. H'-2에서 Noto Sans CJK TTF를 임베딩해 이 문제를 해결한다.

## 구현 개요

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| 폰트 다운로드 | `scripts/download_cjk_fonts.sh` | 배포 환경별 1회 실행 |
| 폰트 레지스트리 | `app/services/font_registry.py` | locale → font 매핑, 등록 관리 |
| PDF 생성기 | `app/services/press_kit_generator.py` | locale 파라미터 → 폰트 선택 |
| 폰트 디렉토리 | `app/fonts/` | 런타임 폰트 파일 위치 (gitignored) |

## Locale → Font 매핑

| locale | 폰트 | 파일 |
|--------|------|------|
| `ko` | NotoSansKR | NotoSansKR-Regular.ttf |
| `ja` | NotoSansJP | NotoSansJP-Regular.ttf |
| `zh` | NotoSansSC | NotoSansSC-Regular.ttf |
| `zh-TW`, `zh-HK` | NotoSansTC | NotoSansTC-Regular.ttf |
| `en`, `es`, 기타 | Helvetica | built-in (파일 불필요) |

## Setup

### 1. 폰트 다운로드 (배포 환경별 1회)

```bash
bash scripts/download_cjk_fonts.sh
```

커스텀 경로 지정:

```bash
FONTS_DIR=/var/app/fonts bash scripts/download_cjk_fonts.sh
```

성공 시 출력:

```
=== Domo CJK Font Download (H'-2) ===
Target directory: app/fonts
  [GET]  NotoSansKR-Regular.ttf
         -> OK (3142560 bytes)
  [GET]  NotoSansJP-Regular.ttf
         -> OK (3987204 bytes)
  ...
=== Font status ===
  OK  NotoSansKR-Regular.ttf
  OK  NotoSansJP-Regular.ttf
  OK  NotoSansSC-Regular.ttf
  OK  NotoSansTC-Regular.ttf
```

### 2. 폰트 경로 오버라이드 (선택)

환경변수로 폰트 디렉토리 경로 재지정:

```bash
export DOMO_FONTS_DIR=/var/app/fonts
```

기본값: `app/fonts/` (font_registry.py 파일 기준 상대경로)

### 3. 서버 시작

폰트 등록은 lazy — 첫 번째 `get_font_name()` 호출 시 자동 수행된다.
서버 시작 전 추가 설정 불필요.

## 동작 검증

### 로그 확인

정상 등록 시:

```
INFO cjk_font_registered font=NotoSansKR path=/app/fonts/NotoSansKR-Regular.ttf
INFO cjk_font_registered font=NotoSansJP path=/app/fonts/NotoSansJP-Regular.ttf
INFO cjk_font_registered font=NotoSansSC path=/app/fonts/NotoSansSC-Regular.ttf
INFO cjk_font_registered font=NotoSansTC path=/app/fonts/NotoSansTC-Regular.ttf
INFO cjk_font_init registered=4/4 dir=/app/fonts
```

폰트 파일 없음 (fallback 활성):

```
DEBUG cjk_font_missing font=NotoSansKR path=/app/fonts/NotoSansKR-Regular.ttf
INFO  cjk_font_init registered=0/4 dir=/app/fonts
```

### Press Kit API 테스트

```bash
# 한국어 Press Kit 생성
curl -X POST /admin/press-kits \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"artist_id": "...", "locale": "ko", "force": true}'

# PDF 다운로드 후 CJK 렌더링 확인
open <download_url>
```

## Production Deployment

### Docker (권장)

폰트를 Docker 이미지에 pre-bake하면 런타임 네트워크 의존성을 제거할 수 있다.

```dockerfile
# Dockerfile — multi-stage: font download stage
FROM python:3.12-slim AS font-builder
RUN apt-get update && apt-get install -y curl
WORKDIR /fonts
RUN curl -fsSL -o NotoSansKR-Regular.ttf \
  "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf" && \
  curl -fsSL -o NotoSansJP-Regular.ttf \
  "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf" && \
  curl -fsSL -o NotoSansSC-Regular.ttf \
  "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf" && \
  curl -fsSL -o NotoSansTC-Regular.ttf \
  "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/TC/NotoSansTC-Regular.otf"

# Main stage
FROM python:3.12-slim
COPY --from=font-builder /fonts/ /app/app/fonts/
...
```

### CI/CD (GitHub Actions)

```yaml
- name: Download CJK fonts
  run: bash scripts/download_cjk_fonts.sh
  env:
    FONTS_DIR: backend/app/fonts
```

### S3 Mount (대안)

폰트 파일을 S3에 저장하고 ECS task startup에서 다운로드:

```bash
aws s3 sync s3://domo-assets/fonts/ /app/fonts/
```

## Fallback 동작

폰트 파일이 없어도 PDF 생성은 실패하지 않는다. `font_registry.py`가 자동으로
Helvetica로 fallback하므로 CJK 텍스트는 `?`로 표시되지만 PDF는 정상 생성된다.

| 상황 | 결과 |
|------|------|
| 폰트 파일 있음 | CJK 문자 정상 렌더링 |
| 폰트 파일 없음 | CJK → `?` 대체, PDF 생성 성공 |
| reportlab 미설치 | RuntimeError (reportlab은 필수 의존성) |

## 테스트

```bash
# Unit tests (5개 — font_registry + _render_str)
python -m pytest tests/unit/test_cjk_font.py -v

# 전체 baseline 확인
python -m pytest tests/unit/ -q
```

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| CJK 여전히 `?` | 폰트 파일 미다운로드 | `bash scripts/download_cjk_fonts.sh` 재실행 |
| `cjk_font_missing` 로그 | 경로 불일치 | `DOMO_FONTS_DIR` 환경변수 확인 |
| `TTFont` 파싱 오류 | 손상된 폰트 파일 | 폰트 삭제 후 재다운로드 |
| `reportlab not installed` | 의존성 누락 | `pip install reportlab` |
| 폰트 파일 너무 작음 | 다운로드 중단 | 파일 삭제 후 재실행 (>10KB 체크) |

## 파일 크기 참고

| 폰트 | 예상 크기 |
|------|---------|
| NotoSansKR-Regular.ttf (OTF SubsetOTF) | ~3 MB |
| NotoSansJP-Regular.ttf | ~4 MB |
| NotoSansSC-Regular.ttf | ~6 MB |
| NotoSansTC-Regular.ttf | ~5 MB |
| 합계 | ~18 MB |

OTF SubsetOTF 버전은 전체 Noto CJK (~8 MB per file)보다 작다.
reportlab은 .otf 파일도 `TTFont`로 로드 가능하다 (OpenType/CFF 포함).

---

Phase H'-2 구현자: bkend-expert agent (2026-05-04)
