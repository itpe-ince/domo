"""CJK font registry — H'-2 cjk-font-pdf-embedding.

Manages registration of Noto Sans CJK fonts with reportlab's pdfmetrics.
Provides locale-to-font mapping with graceful fallback to Helvetica when
a CJK font file is unavailable (e.g. first deployment before download_cjk_fonts.sh
has been run).

Font files are expected at: app/fonts/{name}.ttf (or .otf)
Download via: bash scripts/download_cjk_fonts.sh

Locale → Font mapping:
  ko  → NotoSansKR  (Korean)
  ja  → NotoSansJP  (Japanese)
  zh  → NotoSansSC  (Chinese Simplified)
  zh-TW, zh-HK → NotoSansTC  (Chinese Traditional)
  en, es, (other) → Helvetica (built-in, no embedding needed)

Registration is lazy and idempotent: calling get_font_name() on first use
registers all available fonts. Subsequent calls are instant lookups.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

# ─── Font definitions ─────────────────────────────────────────────────────────

# reportlab font name → TTF/OTF filename (relative to FONTS_DIR)
_FONT_FILES: Final[dict[str, str]] = {
    "NotoSansKR": "NotoSansKR-Regular.ttf",
    "NotoSansJP": "NotoSansJP-Regular.ttf",
    "NotoSansSC": "NotoSansSC-Regular.ttf",
    "NotoSansTC": "NotoSansTC-Regular.ttf",
}

# Bold variants — if a bold TTF is present, use it; otherwise use regular
_FONT_FILES_BOLD: Final[dict[str, str]] = {
    "NotoSansKR-Bold": "NotoSansKR-Bold.ttf",
    "NotoSansJP-Bold": "NotoSansJP-Bold.ttf",
    "NotoSansSC-Bold": "NotoSansSC-Bold.ttf",
    "NotoSansTC-Bold": "NotoSansTC-Bold.ttf",
}

# Locale → (regular_font, bold_font, fallback_regular, fallback_bold)
_LOCALE_MAP: Final[dict[str, tuple[str, str, str, str]]] = {
    "ko":    ("NotoSansKR",  "NotoSansKR",  "Helvetica", "Helvetica-Bold"),
    "ja":    ("NotoSansJP",  "NotoSansJP",  "Helvetica", "Helvetica-Bold"),
    "zh":    ("NotoSansSC",  "NotoSansSC",  "Helvetica", "Helvetica-Bold"),
    "zh-tw": ("NotoSansTC",  "NotoSansTC",  "Helvetica", "Helvetica-Bold"),
    "zh-hk": ("NotoSansTC",  "NotoSansTC",  "Helvetica", "Helvetica-Bold"),
    "en":    ("Helvetica",   "Helvetica-Bold", "Helvetica", "Helvetica-Bold"),
    "es":    ("Helvetica",   "Helvetica-Bold", "Helvetica", "Helvetica-Bold"),
}
_DEFAULT_LOCALE: Final = "en"

# ─── State ────────────────────────────────────────────────────────────────────

# Tracks which reportlab font names have been successfully registered
_registered: set[str] = set()
_registration_attempted: bool = False

# Resolved fonts directory — set once on first access
_fonts_dir: Path | None = None


def _get_fonts_dir() -> Path:
    """Return the fonts directory path.

    Resolution order:
    1. DOMO_FONTS_DIR environment variable
    2. app/fonts/ relative to this file's location
    """
    global _fonts_dir
    if _fonts_dir is None:
        env_dir = os.environ.get("DOMO_FONTS_DIR")
        if env_dir:
            _fonts_dir = Path(env_dir)
        else:
            # __file__ = app/services/font_registry.py → go up two levels → app/
            _fonts_dir = Path(__file__).parent.parent / "fonts"
    return _fonts_dir


# ─── Registration ─────────────────────────────────────────────────────────────


def _register_font(font_name: str, filename: str, fonts_dir: Path) -> bool:
    """Attempt to register a single TTF/OTF font with reportlab.

    Returns True if registration succeeded (or was already registered).
    Returns False if the file does not exist or reportlab raises an error.
    """
    if font_name in _registered:
        return True

    font_path = fonts_dir / filename
    if not font_path.exists():
        log.debug("cjk_font_missing font=%s path=%s", font_name, font_path)
        return False

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        log.warning("reportlab not installed — cannot register CJK fonts")
        return False

    try:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        _registered.add(font_name)
        log.info("cjk_font_registered font=%s path=%s", font_name, font_path)
        return True
    except Exception as exc:
        log.warning(
            "cjk_font_registration_failed font=%s path=%s error=%s",
            font_name, font_path, exc,
        )
        return False


def _ensure_registered() -> None:
    """Register all available CJK fonts (idempotent — runs at most once)."""
    global _registration_attempted
    if _registration_attempted:
        return
    _registration_attempted = True

    fonts_dir = _get_fonts_dir()
    log.debug("cjk_font_dir=%s", fonts_dir)

    # Register regular weights
    for font_name, filename in _FONT_FILES.items():
        _register_font(font_name, filename, fonts_dir)

    # Register bold weights if available (optional; fall back silently)
    for font_name, filename in _FONT_FILES_BOLD.items():
        _register_font(font_name, filename, fonts_dir)

    registered_count = len([n for n in _FONT_FILES if n in _registered])
    log.info(
        "cjk_font_init registered=%d/%d dir=%s",
        registered_count, len(_FONT_FILES), fonts_dir,
    )


# ─── Public API ───────────────────────────────────────────────────────────────


def get_font_name(locale: str, bold: bool = False) -> str:
    """Return the reportlab font name for the given locale.

    If the CJK font for the locale is not registered (file missing), falls
    back to Helvetica so PDF generation always succeeds.

    Args:
        locale: BCP-47 locale string, e.g. "ko", "ja", "zh", "en", "es".
                Normalised to lowercase; "zh-tw" and "zh-hk" → Traditional.
        bold:   If True, return the bold variant name.

    Returns:
        reportlab font name string (e.g. "NotoSansKR", "Helvetica-Bold").
    """
    _ensure_registered()

    normalized = locale.lower().strip()
    mapping = _LOCALE_MAP.get(normalized) or _LOCALE_MAP.get(_DEFAULT_LOCALE)

    # mapping = (regular, bold_cjk, fallback_regular, fallback_bold)
    regular_name, bold_name, fallback_regular, fallback_bold = mapping

    if bold:
        # Prefer bold variant if registered; fall back to regular CJK (reportlab
        # simulates bold for TTF fonts via synthetic bold), then Helvetica-Bold.
        bold_variant = bold_name + "-Bold" if not bold_name.startswith("Helvetica") else bold_name
        if bold_variant in _registered:
            return bold_variant
        if regular_name in _registered:
            return regular_name  # synthetic bold via reportlab
        return fallback_bold
    else:
        if regular_name in _registered:
            return regular_name
        return fallback_regular


def get_font_pair(locale: str) -> tuple[str, str]:
    """Return (regular_font, bold_font) for the locale.

    Convenience wrapper around get_font_name().

    Returns:
        Tuple of (regular_font_name, bold_font_name).
    """
    return get_font_name(locale, bold=False), get_font_name(locale, bold=True)


def is_cjk_locale(locale: str) -> bool:
    """Return True if the locale requires a CJK font (ko, ja, zh variants)."""
    normalized = locale.lower().strip()
    return normalized in {"ko", "ja", "zh", "zh-tw", "zh-hk"}


def is_font_available(locale: str) -> bool:
    """Return True if the CJK font for this locale has been registered.

    Useful for health checks and monitoring.
    """
    _ensure_registered()
    normalized = locale.lower().strip()
    mapping = _LOCALE_MAP.get(normalized) or _LOCALE_MAP.get(_DEFAULT_LOCALE)
    regular_name = mapping[0]
    if regular_name.startswith("Helvetica"):
        return True  # built-in, always available
    return regular_name in _registered


def registered_fonts() -> list[str]:
    """Return list of currently registered CJK font names (for diagnostics)."""
    _ensure_registered()
    return sorted(_registered)


def reset_for_testing(*, fonts_dir: Path | None = None) -> None:
    """Reset registry state — for unit tests only.

    Args:
        fonts_dir: Override fonts directory path. If None, resets to default.
    """
    global _registered, _registration_attempted, _fonts_dir
    _registered = set()
    _registration_attempted = False
    _fonts_dir = fonts_dir
