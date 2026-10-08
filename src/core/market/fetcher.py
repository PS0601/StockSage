# SPDX-License-Identifier: MIT
"""Stock data fetching module using yfinance."""

import logging
from typing import Any, Dict

import pandas as pd
import yfinance as yf

from src.core.config.config import DEFAULT_PERIOD
from src.core.market.stock_data import Financials, MarketIntel, PriceHistory

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """Fetches comprehensive stock data from yfinance."""

    def __init__(self, symbol: str, period: str = DEFAULT_PERIOD):
        self._symbol = symbol
        self._period = period
        self._ticker = yf.Ticker(symbol)

    def fetch_company_profile(self) -> Dict[str, Any]:
        """Fetch company info — name, sector, industry, market cap, valuation metrics."""
        try:
            info = self._ticker.info
            return info if isinstance(info, dict) else {}
        except Exception as e:
            logger.warning("Failed to fetch company profile for %s: %s", self._symbol, e)
            return {}

    def fetch_price_history(self) -> PriceHistory:
        """Fetch OHLCV, dividends, and splits."""
        daily = self._safe_fetch(lambda: self._ticker.history(period=self._period), "price history")
        if isinstance(daily, pd.DataFrame) and "Close" in daily.columns:
            # Drop today's still-trading row (Yahoo returns it with NaN prices).
            daily = daily.dropna(subset=["Close"])
        dividends = self._safe_fetch(lambda: self._ticker.dividends, "dividends")
        splits = self._safe_fetch(lambda: self._ticker.splits, "splits")

        if isinstance(dividends, pd.Series):
            dividends = dividends.to_frame(name="Dividends")
        if isinstance(splits, pd.Series):
            splits = splits.to_frame(name="Stock Splits")

        return PriceHistory(
            daily=daily if self._is_valid(daily) else pd.DataFrame(),
            dividends=dividends if self._is_valid(dividends) else pd.DataFrame(),
            splits=splits if self._is_valid(splits) else pd.DataFrame(),
        )

    def fetch_financials(self) -> Financials:
        """Fetch income statement, balance sheet, cash flow (annual + quarterly)."""
        fetches = {
            "income_statement": lambda: self._ticker.income_stmt,
            "quarterly_income_statement": lambda: self._ticker.quarterly_income_stmt,
            "balance_sheet": lambda: self._ticker.balance_sheet,
            "quarterly_balance_sheet": lambda: self._ticker.quarterly_balance_sheet,
            "cash_flow": lambda: self._ticker.cashflow,
            "quarterly_cash_flow": lambda: self._ticker.quarterly_cashflow,
        }
        results = {name: self._safe_fetch(fn, name) for name, fn in fetches.items()}
        return Financials(
            **{k: v if self._is_valid(v) else pd.DataFrame() for k, v in results.items()}
        )

    def fetch_market_intel(self) -> MarketIntel:
        """Fetch earnings, holders, insider trades, and recommendations.

        News is fetched separately by NewsFetcher in the download pipeline.
        """
        earnings_dates = self._safe_fetch(lambda: self._ticker.earnings_dates, "earnings dates")
        institutional = self._safe_fetch(
            lambda: self._ticker.institutional_holders, "institutional holders"
        )
        insider = self._safe_fetch(
            lambda: self._ticker.insider_transactions, "insider transactions"
        )
        major = self._safe_fetch(lambda: self._ticker.major_holders, "major holders")
        recs = self._safe_fetch(lambda: self._ticker.recommendations, "recommendations")

        return MarketIntel(
            earnings_dates=earnings_dates if self._is_valid(earnings_dates) else pd.DataFrame(),
            institutional_holders=institutional
            if self._is_valid(institutional)
            else pd.DataFrame(),
            insider_transactions=insider if self._is_valid(insider) else pd.DataFrame(),
            major_holders=major if self._is_valid(major) else pd.DataFrame(),
            recommendations=recs if self._is_valid(recs) else pd.DataFrame(),
        )

    def _safe_fetch(self, fn, name: str) -> pd.DataFrame:
        """Fetch with error handling, returns empty DataFrame on failure."""
        try:
            result = fn()
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            logger.warning("Failed to fetch %s for %s: %s", name, self._symbol, e)
            return pd.DataFrame()

    @staticmethod
    def _is_valid(df) -> bool:
        return df is not None and isinstance(df, pd.DataFrame) and not df.empty
