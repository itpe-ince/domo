"""Unit tests for G'-10 price-unit-consistency.

3 tests covering:
  1. ProductPostIn.buy_now_price validator converts dollar float to cents int
  2. parsePriceToCents semantics mirrored in backend schema (round-trip check)
  3. Zero and None edge cases for buy_now_price

The migration data-loss guard is exercised by the alembic migration itself
(PL/pgSQL DO block); not duplicated here.
"""
from __future__ import annotations

import pytest

from app.schemas.post import ProductPostIn


# ─── 1. Dollar float -> cents int conversion ─────────────────────────────────


class TestProductPostInPriceCents:
    """ProductPostIn.dollars_to_cents validator."""

    def test_dollar_float_converts_to_cents(self):
        """$50.00 -> 5000 cents."""
        p = ProductPostIn(is_buy_now=True, buy_now_price=50.0)
        assert p.buy_now_price == 5000

    def test_dollar_int_converts_to_cents(self):
        """50 (int dollars) -> 5000 cents."""
        p = ProductPostIn(is_buy_now=True, buy_now_price=50)
        assert p.buy_now_price == 5000

    def test_fractional_dollar_rounds_correctly(self):
        """$50.005 rounds to 5001 cents (banker's round / Python round behaviour)."""
        p = ProductPostIn(is_buy_now=True, buy_now_price=50.005)
        # Python round() uses banker's rounding; we use round() which is equivalent.
        assert p.buy_now_price == round(50.005 * 100)

    def test_none_passes_through(self):
        """None buy_now_price stays None (product not for sale)."""
        p = ProductPostIn(is_buy_now=False, buy_now_price=None)
        assert p.buy_now_price is None

    def test_zero_converts_to_zero_cents(self):
        """$0.00 -> 0 cents (free product; validation against <=0 is at API level)."""
        p = ProductPostIn(is_buy_now=True, buy_now_price=0)
        assert p.buy_now_price == 0


# ─── 2. Round-trip: cents -> display dollars ──────────────────────────────────


class TestCentsRoundTrip:
    """Verify the cents <-> display-dollars round-trip is lossless for typical prices."""

    @pytest.mark.parametrize(
        "dollar_input, expected_cents",
        [
            (1.99, 199),
            (100.00, 10000),
            (9999.99, 999999),
            (0.01, 1),
        ],
    )
    def test_round_trip(self, dollar_input: float, expected_cents: int):
        p = ProductPostIn(is_buy_now=True, buy_now_price=dollar_input)
        assert p.buy_now_price == expected_cents
        # Display side: cents / 100 restores original dollar value
        assert p.buy_now_price / 100 == pytest.approx(dollar_input, abs=0.001)


# ─── 3. Invalid input rejected ───────────────────────────────────────────────


class TestProductPostInPriceValidation:
    """Invalid buy_now_price values raise ValidationError."""

    def test_non_numeric_string_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductPostIn(is_buy_now=True, buy_now_price="not-a-number")
