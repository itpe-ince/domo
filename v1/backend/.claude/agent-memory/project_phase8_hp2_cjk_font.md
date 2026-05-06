---
name: Phase 8 H'-2 CJK Font PDF Embedding
description: H'-2 완료: Noto Sans CJK TTF 임베딩, font_registry.py, press_kit_generator 수정, 8 unit tests, cjk-font-embedding.md
type: project
---

H'-2 CJK font PDF embedding 완료 (2026-05-04).

**Why:** C-2 PressKit PDF가 reportlab Helvetica(Latin-1 only) 사용으로 한국어/일본어/중국어 문자 모두 `?` 렌더링. Noto Sans CJK TTF 임베딩으로 해결.

**How to apply:** 배포 환경마다 `bash scripts/download_cjk_fonts.sh` 1회 실행 필요. 폰트 없으면 자동 Helvetica fallback.

신규 파일:
- `scripts/download_cjk_fonts.sh` — GitHub noto-cjk에서 KR/JP/SC/TC TTF 다운로드, fallback 포함
- `app/services/font_registry.py` — locale→font 매핑, lazy idempotent 등록, `reset_for_testing()` 제공
- `app/fonts/.gitkeep` — 폰트 디렉토리 placeholder (fonts/ gitignored)
- `tests/unit/test_cjk_font.py` — 8 unit tests
- `docs/operations/cjk-font-embedding.md` — setup + Docker + S3 + 트러블슈팅

수정 파일:
- `app/services/press_kit_generator.py`:
  - `get_font_pair(locale)` import → ParagraphStyle에 locale font 주입
  - `_render_str(text, font_name)` 신규 — CJK TTF면 통과, Helvetica면 latin-1 replace
  - `_make_page_frame(font_regular)` — closure로 footer 폰트 전달
  - page builder 함수 시그니처: `_t` callable 파라미터 추가
  - `_safe_str()` legacy로 유지 (하위호환)
- `.gitignore` — `backend/app/fonts/` 추가

Locale 매핑: ko→NotoSansKR, ja→NotoSansJP, zh→NotoSansSC, zh-TW/zh-HK→NotoSansTC, en/es→Helvetica

No alembic, no frontend changes.
