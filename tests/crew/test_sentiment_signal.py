# SPDX-License-Identifier: MIT
"""Sentiment signal: analyst view, downgraded after heavy underperformance."""

import pandas as pd

from src.crew.facts import _sentiment_facts

BULLISH = pd.DataFrame([{"strongBuy": 4, "buy": 15, "hold": 14, "sell": 1, "strongSell": 0}])


def test_positive_kept_when_roughly_in_line_with_market() -> None:
    text = _sentiment_facts(BULLISH, None, None, relative_return=-0.05)
    assert "Sentiment Signal: Positive" in text
    assert "downgraded" not in text


def test_positive_downgraded_after_heavy_underperformance() -> None:
    text = _sentiment_facts(BULLISH, None, None, relative_return=-0.35)
    assert "Sentiment Signal: Neutral" in text
    assert "trailed the market by 35.0 points" in text


def test_no_return_data_keeps_analyst_signal() -> None:
    assert "Sentiment Signal: Positive" in _sentiment_facts(BULLISH, None, None)
