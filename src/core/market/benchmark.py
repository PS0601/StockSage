# SPDX-License-Identifier: MIT
"""Benchmark index fetching — market index and sector ETF via yfinance."""

import logging
from typing import Tuple

import pandas as pd
import yfinance as yf

from src.core.config.config import DEFAULT_PERIOD
from src.core.config.markets import is_indian_symbol

logger = logging.getLogger(__name__)

MARKET_INDICES = {
    "us": ("^GSPC", "S&P 500"),
    "india": ("^NSEI", "NIFTY 50"),
}

US_SECTOR_ETFS = {
    "Technology": ("XLK", "Technology Select Sector"),
    "Financial Services": ("XLF", "Financial Select Sector"),
    "Healthcare": ("XLV", "Health Care Select Sector"),
    "Consumer Cyclical": ("XLY", "Consumer Discretionary"),
    "Consumer Defensive": ("XLP", "Consumer Staples"),
    "Energy": ("XLE", "Energy Select Sector"),
    "Industrials": ("XLI", "Industrial Select Sector"),
    "Basic Materials": ("XLB", "Materials Select Sector"),
    "Utilities": ("XLU", "Utilities Select Sector"),
    "Real Estate": ("XLRE", "Real Estate Select Sector"),
    "Communication Services": ("XLC", "Communication Services"),
}


class BenchmarkFetcher:
    """Fetches market index and sector benchmark price data."""

    def __init__(self, symbol: str, company_info: dict, period: str = DEFAULT_PERIOD):
        self._period = period
        self._market = "india" if is_indian_symbol(symbol) else "us"
        self._sector = company_info.get("sector", "")

    def fetch_market_index(self) -> Tuple[pd.DataFrame, str]:
        """Fetch the main market index (S&P 500 or NIFTY 50)."""
        ticker, name = MARKET_INDICES.get(self._market, MARKET_INDICES["us"])
        return self._fetch_history(ticker, name), name

    def fetch_sector_index(self) -> Tuple[pd.DataFrame, str]:
        """Fetch the sector ETF. US only — returns empty for Indian stocks or unknown sectors."""
        if self._market != "us" or self._sector not in US_SECTOR_ETFS:
            return pd.DataFrame(), ""
        ticker, name = US_SECTOR_ETFS[self._sector]
        return self._fetch_history(ticker, name), name

    def _fetch_history(self, ticker: str, name: str) -> pd.DataFrame:
        try:
            df = yf.Ticker(ticker).history(period=self._period)
            if df is not None and not df.empty:
                # Drop today's still-trading row (Yahoo returns it with NaN prices).
                if "Close" in df.columns:
                    df = df.dropna(subset=["Close"])
                return df
        except Exception as e:
            logger.warning("Failed to fetch %s (%s): %s", name, ticker, e)
        return pd.DataFrame()
