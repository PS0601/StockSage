# SPDX-License-Identifier: MIT
"""Mini Screener and index naming must reflect the stock's own data."""

import numpy as np
import pandas as pd

from src.crew.facts import _analyst_mix, _index_name, _mini_screener


def test_index_name_by_market() -> None:
    assert _index_name("RELIANCE.NS") == "NIFTY 50"
    assert _index_name("AAPL") == "S&P 500"


def test_analyst_mix_handles_blank_counts() -> None:
    recs = pd.DataFrame([{"strongBuy": 2, "buy": None, "hold": 2, "sell": 0, "strongSell": 0}])
    buy_pct, sell_pct, total = _analyst_mix(recs)
    assert total == 4
    assert buy_pct == 50.0


def test_screener_for_expensive_outperformer() -> None:
    row = pd.Series({"trailingPE": 40.0, "priceToBook": 10.0})
    stock = np.linspace(100, 150, 50)  # +50%, smooth
    market = np.linspace(100, 110, 50)  # +10%
    recs = pd.DataFrame([{"strongBuy": 8, "buy": 2, "hold": 0, "sell": 0, "strongSell": 0}])
    assert _mini_screener(row, stock, market, recs) == (
        "Valuation=Rich | Momentum=Strong | Risk=Low | Sentiment=Bullish"
    )


def test_screener_without_data() -> None:
    empty = np.array([])
    assert _mini_screener(pd.Series(dtype=object), empty, empty, None) == (
        "Valuation=N/A | Momentum=N/A | Risk=N/A | Sentiment=N/A"
    )
