# SPDX-License-Identifier: MIT
"""Insights must be generated from each stock's data, not canned text."""

import pandas as pd

from src.crew.facts import (
    _health_insight,
    _performance_insight,
    _sentiment_insight,
    _valuation_insight,
)


def test_valuation_without_earnings_says_so() -> None:
    assert "No meaningful P/E" in _valuation_insight(pd.Series({"trailingPE": None}))


def test_valuation_rich_but_growth_justified() -> None:
    row = pd.Series({"trailingPE": 30.0, "pegRatio": 0.3, "earningsGrowth": 1.2})
    assert "may justify" in _valuation_insight(row)


def test_valuation_ignores_peg_when_growth_negative() -> None:
    row = pd.Series({"trailingPE": 30.0, "pegRatio": 0.8, "earningsGrowth": -0.2})
    assert "must stay strong" in _valuation_insight(row)


def test_performance_underperformance_with_large_swings() -> None:
    text = _performance_insight(-0.20, 0.15, 0.19, -0.31, -1.3)
    assert text.startswith("Underperformed the market by 35.0")
    assert "large swings" in text


def test_health_negative_cash_flow_is_flagged() -> None:
    assert "consuming cash" in _health_insight(-1.8e9, 104.0)
    assert "leverage is high" in _health_insight(-1.8e9, 104.0)


def test_sentiment_thresholds() -> None:
    assert "strongly bullish" in _sentiment_insight(95.1, 1.6, 61)
    assert "No analyst ratings" in _sentiment_insight(0.0, 0.0, 0)
