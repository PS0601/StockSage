# SPDX-License-Identifier: MIT
"""Tests for year-over-year change, including negative prior values."""

import pytest

from src.crew.facts import _yoy_change


def test_positive_growth_unchanged_from_usual_formula() -> None:
    assert _yoy_change(110.0, 100.0) == pytest.approx(0.10)


def test_negative_value_getting_worse_is_negative() -> None:
    # JPM-style: FCF fell from -42.01B to -147.78B
    assert _yoy_change(-147.78, -42.01) == pytest.approx(-2.5178, rel=1e-3)


def test_negative_value_improving_is_positive() -> None:
    # RIVN-style: FCF improved from -2.857B to -2.489B
    assert _yoy_change(-2.489, -2.857) == pytest.approx(0.1288, rel=1e-3)
