# SPDX-License-Identifier: MIT
"""Tests for shared market detection."""

import pytest

from src.core.config.markets import is_indian_symbol


@pytest.mark.parametrize("symbol", ["RELIANCE.NS", "TCS.BO", "reliance.ns", " infy.bo "])
def test_indian_symbols(symbol: str) -> None:
    assert is_indian_symbol(symbol)


@pytest.mark.parametrize("symbol", ["AAPL", "aapl", "BRK.B", "NSE"])
def test_non_indian_symbols(symbol: str) -> None:
    assert not is_indian_symbol(symbol)
