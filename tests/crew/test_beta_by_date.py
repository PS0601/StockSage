# SPDX-License-Identifier: MIT
"""Beta must pair stock and market returns by date, not by row position."""

import numpy as np
import pandas as pd

from src.crew.facts import _beta_by_date


def _frame(dates: list[str], closes: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"Date": dates, "Close": closes})


def test_beta_survives_mismatched_trading_calendars() -> None:
    rng = np.random.default_rng(0)
    dates = [str(d.date()) for d in pd.bdate_range("2025-01-01", periods=200)]
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.01, 200))

    # Stock and index move identically (true beta = 1), but the index skips a few
    # days (its holidays), so the two files have different lengths.
    stock = _frame(dates, closes)
    keep = [i for i in range(200) if i not in (20, 80, 140)]
    market = _frame([dates[i] for i in keep], closes[keep])

    beta = _beta_by_date(stock, market)

    assert beta is not None
    assert 0.9 < beta < 1.1


def test_beta_none_without_market_data() -> None:
    dates = [str(d.date()) for d in pd.bdate_range("2025-01-01", periods=10)]
    stock = _frame(dates, np.linspace(100, 110, 10))
    assert _beta_by_date(stock, None) is None
