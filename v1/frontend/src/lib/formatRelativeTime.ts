/**
 * Relative time formatter — "5초 전", "3분 전", "2시간 전", "1일 전".
 *
 * Extracted from app/notifications/page.tsx:15-25 (Q-D2 = A in editor-draft-autosave PDCA).
 * Reused by NotificationsPage and AutosaveIndicator.
 *
 * NOTE: Currently Korean-only. Future i18n: read t("time.secondsAgo", { n: sec })
 * etc. when the time.* namespace is fully populated across all locales.
 */

export function formatRelativeTime(input: string | Date | null): string {
  if (!input) return "";
  const date = typeof input === "string" ? new Date(input) : input;
  const diff = Date.now() - date.getTime();
  if (Number.isNaN(diff)) return "";

  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${Math.max(sec, 0)}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  return `${Math.floor(hr / 24)}일 전`;
}
