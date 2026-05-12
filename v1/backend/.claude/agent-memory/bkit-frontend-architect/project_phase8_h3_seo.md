---
name: Phase 8 H'-3 Multi-language SEO Meta
description: H'-3 완료: og:locale + og:locale:alternate + hreflang (5 locale) + canonical + sitemap; tsc 0
type: project
---

H'-3 multi-language-seo-meta 완료 (2026-05-04).

**Why:** SEO를 위해 G'-6 4개 OG 라우트 + stories hub에 locale별 메타 태그 통합 필요.

**How to apply:** 신규 SEO 메타 작업 시 `/lib/seo/locales.ts` 헬퍼 재사용.

## 신규/수정 파일

| 파일 | 상태 | 내용 |
|------|------|------|
| `src/lib/seo/locales.ts` | 신규 | 공유 SEO 상수 + buildAlternateLanguages / buildCanonical / buildOgLocaleAlternates 헬퍼 |
| `src/app/users/[id]/layout.tsx` | 수정 | og:locale + alternateLocale + alternates.languages + canonical 추가 |
| `src/app/users/[id]/timeline/layout.tsx` | 수정 | 동일 |
| `src/app/posts/[id]/layout.tsx` | 수정 | 동일 |
| `src/app/me/sponsorships/[id]/layout.tsx` | 신규 | G'-6 4번째 OG 라우트 layout 없었음 — 신규 생성 + H'-3 적용 |
| `src/app/stories/layout.tsx` | 신규 | A-7 storytelling hub에 metadata 추가 (static export) |
| `src/app/sitemap.ts` | 신규 | 5 locale hreflang alternates 포함 sitemap (9 static routes, 24h ISR) |

## 5 Locale OG Meta 검증 (expected HTML output)

`/users/abc123` 기준:
```html
<meta property="og:locale" content="ko_KR" />
<meta property="og:locale:alternate" content="en_US" />
<meta property="og:locale:alternate" content="ja_JP" />
<meta property="og:locale:alternate" content="zh_CN" />
<meta property="og:locale:alternate" content="es_ES" />
```

## Hreflang Tags 검증

```html
<link rel="alternate" hreflang="ko" href="https://domo.lounge/ko/users/abc123" />
<link rel="alternate" hreflang="en" href="https://domo.lounge/en/users/abc123" />
<link rel="alternate" hreflang="ja" href="https://domo.lounge/ja/users/abc123" />
<link rel="alternate" hreflang="zh" href="https://domo.lounge/zh/users/abc123" />
<link rel="alternate" hreflang="es" href="https://domo.lounge/es/users/abc123" />
```

## 설계 결정

- OG image 자체는 locale 분기 없음 (Edge runtime에서 localStorage 불가, 언어 무관한 시각 콘텐츠)
- twitter:card="summary_large_image" 유지 (G'-6 회귀 없음)
- SITE_URL: `NEXT_PUBLIC_SITE_URL` env var 또는 `https://domo.lounge` fallback
- sitemap: 동적 artist/post URL 제외 (crawl budget), static 9개 라우트만
