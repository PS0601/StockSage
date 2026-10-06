# SPDX-License-Identifier: MIT
"""Orchestrates the multi-step download sequence for a stock symbol."""

import logging
import time
from collections.abc import Generator
from uuid import uuid4

from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.core.market.benchmark import BenchmarkFetcher
from src.core.market.fetcher import StockDataFetcher
from src.core.market.news import NewsFetcher
from src.core.market.stock_data import BenchmarkData, StockData
from src.core.market.storage import CSVStorage
from src.core.market.trends import TrendsFetcher

logger = logging.getLogger(__name__)


class DownloadPipeline:
    """Orchestrates all download steps and progress logging for a symbol.

    Critical steps (abort flow on failure):
    - Company profile
    - Price history
    - Financial statements

    Non-critical steps (log failure and continue):
    - Supplementary market intel
    - Benchmarks (market index and sector ETF)
    - News
    - Google Trends

    Final step persists all collected data to CSV.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.stage = ProcessingStage.DOWNLOADING_DATA
        self.fetcher = StockDataFetcher(symbol)
        self.stock_data = StockData(symbol=symbol)
        self.critical_ok = False

    def _log(self, substage: SubStage, status: StatusType, message: str | None = None) -> LogEntry:
        return LogEntry(
            stage=self.stage,
            substage=substage,
            status_type=status,
            message=message,
            symbol=self.symbol,
        )

    def _safe_failure_message(self, context: str, error: Exception) -> str:
        ref = uuid4().hex[:8]
        logger.exception("%s failed for %s (ref=%s)", context, self.symbol, ref, exc_info=error)
        return f"{context} failed. See server logs (ref: {ref})."

    def _company_profile_step(self) -> Generator[LogEntry, None, bool]:
        yield self._log(SubStage.DOWNLOADING_COMPANY_PROFILE, StatusType.IN_PROGRESS)
        self.stock_data.company_info = self.fetcher.fetch_company_profile()
        if not self.stock_data.company_info:
            yield self._log(
                SubStage.DOWNLOADING_COMPANY_PROFILE,
                StatusType.FAILED,
                "No company info — aborting",
            )
            return False
        yield self._log(
            SubStage.DOWNLOADING_COMPANY_PROFILE,
            StatusType.SUCCESS,
            self.stock_data.company_summary,
        )
        return True

    def _price_history_step(self) -> Generator[LogEntry, None, bool]:
        yield self._log(SubStage.DOWNLOADING_PRICE_HISTORY, StatusType.IN_PROGRESS)
        self.stock_data.prices = self.fetcher.fetch_price_history()
        if not self.stock_data.prices.is_valid():
            yield self._log(
                SubStage.DOWNLOADING_PRICE_HISTORY, StatusType.FAILED, "No price data — aborting"
            )
            return False
        yield self._log(
            SubStage.DOWNLOADING_PRICE_HISTORY, StatusType.SUCCESS, self.stock_data.prices.summary
        )
        return True

    def _financials_step(self) -> Generator[LogEntry, None, bool]:
        yield self._log(SubStage.DOWNLOADING_FINANCIALS, StatusType.IN_PROGRESS)
        self.stock_data.financials = self.fetcher.fetch_financials()
        if not self.stock_data.financials.has_any():
            yield self._log(
                SubStage.DOWNLOADING_FINANCIALS, StatusType.FAILED, "No financial data — aborting"
            )
            return False
        yield self._log(
            SubStage.DOWNLOADING_FINANCIALS, StatusType.SUCCESS, self.stock_data.financials.summary
        )
        return True

    def _market_intel_step(self) -> Generator[LogEntry, None, None]:
        yield self._log(SubStage.DOWNLOADING_MARKET_INTEL, StatusType.IN_PROGRESS)
        self.stock_data.market_intel = self.fetcher.fetch_market_intel()
        intel_summary = self.stock_data.market_intel.summary
        if intel_summary != "No supplementary data":
            yield self._log(SubStage.DOWNLOADING_MARKET_INTEL, StatusType.SUCCESS, intel_summary)
        else:
            yield self._log(
                SubStage.DOWNLOADING_MARKET_INTEL,
                StatusType.FAILED,
                "Supplementary data unavailable — continuing",
            )

    def _benchmarks_step(self) -> Generator[LogEntry, None, None]:
        yield self._log(SubStage.DOWNLOADING_BENCHMARKS, StatusType.IN_PROGRESS)
        bench = BenchmarkFetcher(self.symbol, self.stock_data.company_info)
        market_df, market_name = bench.fetch_market_index()
        sector_df, sector_name = bench.fetch_sector_index()
        self.stock_data.benchmarks = BenchmarkData(
            market_index=market_df,
            market_index_name=market_name,
            sector_index=sector_df,
            sector_index_name=sector_name,
        )
        bench_summary = self.stock_data.benchmarks.summary
        if bench_summary != "No benchmark data":
            yield self._log(SubStage.DOWNLOADING_BENCHMARKS, StatusType.SUCCESS, bench_summary)
        else:
            yield self._log(
                SubStage.DOWNLOADING_BENCHMARKS,
                StatusType.FAILED,
                "Benchmark data unavailable — continuing",
            )

    def _news_step(self) -> Generator[LogEntry, None, None]:
        yield self._log(SubStage.DOWNLOADING_NEWS, StatusType.IN_PROGRESS)
        company_name = self.stock_data.company_info.get("longName", "")
        articles = NewsFetcher(self.symbol, company_name).fetch()
        if articles:
            self.stock_data.market_intel.news = articles
            yield self._log(
                SubStage.DOWNLOADING_NEWS, StatusType.SUCCESS, f"{len(articles)} articles"
            )
        else:
            yield self._log(
                SubStage.DOWNLOADING_NEWS, StatusType.FAILED, "No news found — continuing"
            )

    def _trends_step(self) -> Generator[LogEntry, None, None]:
        yield self._log(SubStage.DOWNLOADING_TRENDS, StatusType.IN_PROGRESS)
        time.sleep(2)  # Throttle to reduce 429 rate limits from Google Trends
        company_name = self.stock_data.company_info.get("longName", "") or self.symbol
        geo = "IN" if self.symbol.upper().endswith((".NS", ".BO")) else "US"
        trends_df = TrendsFetcher(company_name, geo=geo).fetch()
        if not trends_df.empty:
            self.stock_data.market_intel.google_trends = trends_df
            yield self._log(
                SubStage.DOWNLOADING_TRENDS,
                StatusType.SUCCESS,
                f"{len(trends_df)} weekly data points",
            )
        else:
            yield self._log(
                SubStage.DOWNLOADING_TRENDS, StatusType.FAILED, "No trends data — continuing"
            )

    def _save_step(self) -> Generator[LogEntry, None, bool]:
        yield self._log(SubStage.SAVING_DATA, StatusType.IN_PROGRESS)
        try:
            saved_files = CSVStorage().save(self.stock_data)
            yield self._log(
                SubStage.SAVING_DATA,
                StatusType.SUCCESS,
                f"{len(saved_files)} files saved to .market_data/{self.symbol}/",
            )
            return True
        except (OSError, ValueError, TypeError) as exc:
            yield self._log(
                SubStage.SAVING_DATA, StatusType.FAILED, self._safe_failure_message("Save", exc)
            )
            return False
        except Exception as exc:
            yield self._log(
                SubStage.SAVING_DATA, StatusType.FAILED, self._safe_failure_message("Save", exc)
            )
            return False

    def run(self) -> Generator[LogEntry, None, StockData | None]:
        """Run the full download sequence and stream log entries.

        Returns:
            StockData when all critical steps succeed; otherwise None.
        """
        self.critical_ok = False
        if not (yield from self._company_profile_step()):
            return None

        if not (yield from self._price_history_step()):
            return None

        if not (yield from self._financials_step()):
            return None

        yield from self._market_intel_step()
        yield from self._benchmarks_step()
        yield from self._news_step()
        yield from self._trends_step()
        if not (yield from self._save_step()):
            return None
        self.critical_ok = True
        return self.stock_data
