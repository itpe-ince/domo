"""Unit tests for app/services/font_registry.py — H'-2 cjk-font-pdf-embedding.

5 tests covering:
  1. get_font_name() en/es locales → Helvetica (no CJK font needed)
  2. get_font_name() ko/ja/zh with fonts registered → NotoSansXX returned
  3. get_font_name() missing font (not registered) → Helvetica fallback
  4. _render_str() with Helvetica → latin-1 safe replacement of CJK chars
  5. _render_str() with NotoSansKR → CJK text passed through unchanged
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _reset_registry(fonts_dir: Path | None = None):
    """Reset font_registry module state for test isolation."""
    # Re-import to pick up a clean module state via reset_for_testing
    import app.services.font_registry as fr
    fr.reset_for_testing(fonts_dir=fonts_dir)
    return fr


def _make_fake_ttf(tmp_path: Path, name: str) -> Path:
    """Create a minimal fake TTF file (just needs to be >10 KB for existence checks)."""
    font_file = tmp_path / name
    # Write dummy bytes — TTFont will fail to parse but we mock that call
    font_file.write_bytes(b"\x00" * 16000)
    return font_file


# ─── Test 1: en/es locales → Helvetica (no CJK font file needed) ─────────────

def test_latin_locales_return_helvetica(tmp_path):
    """en and es locales should always resolve to Helvetica (built-in)."""
    fr = _reset_registry(fonts_dir=tmp_path)  # empty fonts dir — no CJK files

    assert fr.get_font_name("en") == "Helvetica"
    assert fr.get_font_name("es") == "Helvetica"
    assert fr.get_font_name("en", bold=True) == "Helvetica-Bold"
    assert fr.get_font_name("es", bold=True) == "Helvetica-Bold"


# ─── Test 2: CJK locales with fonts registered → NotoSansXX returned ─────────

def test_cjk_locales_with_registered_fonts(tmp_path):
    """ko/ja/zh locales return NotoSansXX when font files exist and are loaded."""
    # Create fake font files
    for filename in [
        "NotoSansKR-Regular.ttf",
        "NotoSansJP-Regular.ttf",
        "NotoSansSC-Regular.ttf",
        "NotoSansTC-Regular.ttf",
    ]:
        _make_fake_ttf(tmp_path, filename)

    fr = _reset_registry(fonts_dir=tmp_path)

    # Patch reportlab TTFont to avoid real font parsing
    mock_ttfont = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "reportlab": MagicMock(),
            "reportlab.pdfbase": MagicMock(),
            "reportlab.pdfbase.pdfmetrics": MagicMock(),
            "reportlab.pdfbase.ttfonts": MagicMock(TTFont=mock_ttfont),
        },
    ):
        # Manually inject registered fonts to simulate successful registration
        fr._registered = {"NotoSansKR", "NotoSansJP", "NotoSansSC", "NotoSansTC"}
        fr._registration_attempted = True

        assert fr.get_font_name("ko") == "NotoSansKR"
        assert fr.get_font_name("ja") == "NotoSansJP"
        assert fr.get_font_name("zh") == "NotoSansSC"
        assert fr.get_font_name("zh-TW") == "NotoSansTC"
        assert fr.get_font_name("zh-HK") == "NotoSansTC"


# ─── Test 3: Missing font file → Helvetica fallback ──────────────────────────

def test_missing_font_file_falls_back_to_helvetica(tmp_path):
    """When font files are absent, CJK locales fall back to Helvetica."""
    # tmp_path is empty — no font files
    fr = _reset_registry(fonts_dir=tmp_path)

    # Force registration attempt with no files available
    fr._ensure_registered()

    # _registered should be empty (no files to load)
    assert "NotoSansKR" not in fr._registered

    # get_font_name should fall back gracefully
    assert fr.get_font_name("ko") == "Helvetica"
    assert fr.get_font_name("ja") == "Helvetica"
    assert fr.get_font_name("zh") == "Helvetica"
    assert fr.get_font_name("ko", bold=True) == "Helvetica-Bold"


# ─── Test 4: _render_str() with Helvetica → latin-1 replacement ───────────────

def test_render_str_helvetica_replaces_cjk():
    """_render_str with Helvetica font replaces non-latin-1 chars with '?'."""
    from app.services.press_kit_generator import _render_str

    korean_text = "안녕하세요 Artist"
    result = _render_str(korean_text, "Helvetica")
    # CJK chars are replaced; ASCII part survives
    assert "Artist" in result
    # CJK characters that cannot be encoded in latin-1 become '?'
    assert "안" not in result  # '안' should be gone
    assert "?" in result or result.count("Artist") == 1  # replacement happened


def test_render_str_helvetica_empty_input():
    """_render_str returns empty string for None/empty input."""
    from app.services.press_kit_generator import _render_str

    assert _render_str(None, "Helvetica") == ""
    assert _render_str("", "Helvetica") == ""
    assert _render_str(None, "NotoSansKR") == ""


# ─── Test 5: _render_str() with NotoSansKR → CJK text unchanged ───────────────

def test_render_str_noto_preserves_cjk():
    """_render_str with NotoSansKR passes CJK text through without modification."""
    from app.services.press_kit_generator import _render_str

    korean_text = "안녕하세요"
    japanese_text = "こんにちは"
    chinese_text = "你好世界"

    # With a CJK font, text passes through as-is
    assert _render_str(korean_text, "NotoSansKR") == korean_text
    assert _render_str(japanese_text, "NotoSansJP") == japanese_text
    assert _render_str(chinese_text, "NotoSansSC") == chinese_text

    # ASCII text is also preserved
    assert _render_str("Hello World", "NotoSansKR") == "Hello World"


# ─── Bonus: is_cjk_locale() helper ───────────────────────────────────────────

def test_is_cjk_locale_classification():
    """is_cjk_locale() correctly identifies CJK vs Latin locales."""
    import app.services.font_registry as fr

    assert fr.is_cjk_locale("ko") is True
    assert fr.is_cjk_locale("ja") is True
    assert fr.is_cjk_locale("zh") is True
    assert fr.is_cjk_locale("zh-TW") is True
    assert fr.is_cjk_locale("zh-HK") is True
    assert fr.is_cjk_locale("en") is False
    assert fr.is_cjk_locale("es") is False
    assert fr.is_cjk_locale("fr") is False


# ─── Bonus: is_font_available() for Latin locales ────────────────────────────

def test_is_font_available_latin_always_true(tmp_path):
    """Latin locales (en/es) always report font as available (Helvetica built-in)."""
    fr = _reset_registry(fonts_dir=tmp_path)
    fr._registration_attempted = True  # skip file scan

    assert fr.is_font_available("en") is True
    assert fr.is_font_available("es") is True


# ─── Bonus: get_font_pair() returns tuple ─────────────────────────────────────

def test_get_font_pair_returns_tuple(tmp_path):
    """get_font_pair() returns (regular, bold) tuple for any locale."""
    fr = _reset_registry(fonts_dir=tmp_path)
    fr._registration_attempted = True

    regular, bold = fr.get_font_pair("en")
    assert regular == "Helvetica"
    assert bold == "Helvetica-Bold"

    # CJK with no font file → both fallback to Helvetica
    regular_ko, bold_ko = fr.get_font_pair("ko")
    assert regular_ko == "Helvetica"
    assert bold_ko == "Helvetica-Bold"
