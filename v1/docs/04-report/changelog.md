# Changelog

모든 주요 변경 사항은 이 파일에 기록됩니다.

---

## [2026-05-11] - Settings Unification 완료

### Added
- `/me/settings` Hub page (6 카테고리 카드 그리드)
- `/me/settings/profile` sub-page (← `/me/bio` 이동)
- `/me/settings/display` sub-page (← `/me/settings/preferences` 이름 변경)
- `/me/settings/notifications` sub-page (← `/me/notifications/preferences` + `/me/newsletter` 통합)
- `/me/settings/account` sub-page (← `/me/account` + `/me/settings/sponsor-validity` 통합)
- `settings.hub.*` i18n keys (14 keys × 5 locales = 70 entries) for ko/en/ja/zh/es

### Removed
- `/me/account/` directory (→ `/me/settings/account`)
- `/me/bio/` directory (→ `/me/settings/profile`)
- `/me/newsletter/` directory (→ `/me/settings/notifications` section)
- `/me/notifications/preferences/` directory (→ `/me/settings/notifications`)
- `/me/settings/preferences/` directory (→ `/me/settings/display`)
- `/me/settings/sponsor-validity/` directory (→ `/me/settings/account` section)

### Changed
- `Sidebar.tsx`: 설정 항목 링크 통합 (`/me/settings`)
- `MobileTabBar.tsx`: 설정 탭 링크 통합
- `patronage/page.tsx`: "계정 설정" 링크 → `/me/settings/account`
- `legal/privacy/page.tsx`: "계정 설정" 링크 → `/me/settings/account`
- `accessibility/page.tsx` breadcrumb: → `/me/settings`
- `privacy/page.tsx` breadcrumb: → `/me/settings`

### Fixed
- PreferencesCard.tsx JSDoc 경로 (스테일 참조 제거)

### Performance
- No backend impact (frontend-only refactor)
- Regression: 0 (tsc 0 error, backend 780 passed)

### Metrics
- **Match Rate**: 99% (≥ 90% ✅)
- **PDCA Cycle**: Complete (Plan → Design → Do → Check → Act)
- **Completion**: 2026-05-11

---

## Document References

- **Plan**: [settings-unification.plan.md](features/settings-unification.plan.md)
- **Design**: [settings-unification.design.md](../02-design/features/settings-unification.design.md)
- **Analysis**: [settings-unification.analysis.md](../03-analysis/settings-unification.analysis.md)
- **Report**: [settings-unification.report.md](features/settings-unification.report.md)
