# SPDX-License-Identifier: MIT
# Cap size uses dollar bands for US stocks and rupee bands for Indian stocks.

from src.crew.facts import _cap_size


def test_us_bands_unchanged() -> None:
    assert _cap_size(4.9e12, "AAPL") == "Very Large Cap"
    assert _cap_size(20.8e9, "RIVN") == "Large Cap"


def test_indian_stock_uses_rupee_bands() -> None:
    assert _cap_size(4.04e12, "INFY.NS") == "Large Cap"
    assert _cap_size(16.9e12, "RELIANCE.NS") == "Very Large Cap"
    assert _cap_size(500e9, "XYZ.NS") == "Mid Cap"


def test_missing_market_cap() -> None:
    assert _cap_size(None, "INFY.NS") == "N/A"
