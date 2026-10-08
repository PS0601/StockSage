# SPDX-License-Identifier: MIT
"""Mock SSE stream for fast frontend/UI iteration in dev mode."""

import asyncio

from src.app.utils.formatters import format_log_entry
from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.markets import is_indian_symbol
from src.core.config.models import LogEntry

SSE_RETRY_MS = 3000

_MOCK_RAW_PAYLOADS_TEMPLATE: dict[SubStage, str] = {
    SubStage.VALIDATING_DATA_SANITY: """
Structured Summary: All critical data files present and consistent; soft blocks on 3 optional files.
Gate Status: PASS
Market Context: Developed market large-cap equity
Company Type: Public
Validated File: company_info.csv
Validated File: historical_prices.csv
Validated File: income_statement.csv
Validated File: cash_flow.csv
Validated File: recommendations.csv
Missing/Invalid File: balance_sheet.csv
Missing/Invalid File: insider_transactions.csv
Missing/Invalid File: institutional_holders.csv
Warning: Forward P/E not present in company_info.csv
Ratio Applicability: PE Ratio -> VALID
Ratio Applicability: P/S Ratio -> VALID
Ratio Applicability: EV/EBITDA -> VALID
Valuation Model Applicability: Relative Valuation -> VALID
""",
    SubStage.ANALYZING_VALUATION_RATIOS: """
Valuation Verdict: Fair | Near long-term average
Insight: Valuation is not cheap, but earnings quality remains solid.
P/E Ratio: 22.6x
Forward P/E: 21.2x
P/B Ratio: 2.16x
P/S Ratio: 1.85x
PEG Ratio: 1.20x
EV/EBITDA: 14.1x
Implication: Upside likely depends on sustained growth execution.
Structured Summary: The stock appears reasonably priced relative to peers.
""",
    SubStage.ANALYZING_PRICE_PERFORMANCE: """
Total Return (%): 16.62%
Annualized Return (%): 16.91%
Volatility (%): 24%
Volatility Label: Moderate
Max Drawdown (%): -18%
Beta (vs market): 1.01
Sharpe Ratio: 0.80
Market Total Return (%): 11.5%
Performance Badge: IN LINE
Insight: Performance remains healthy but volatility requires position sizing discipline.
CHART_DATA: {"labels":["Q1","Q2","Q3","Q4"],"stock":[3.2,4.8,2.4,6.2],"benchmark":[2.5,3.4,2.1,3.5]}
""",
    SubStage.ANALYZING_MARKET_SENTIMENT: """
Sentiment Signal: Positive
Analyst Consensus: Buy 3 | Hold 1 | Sell 0 (4 analysts)
Insight: News flow is mildly constructive with cautious optimism.
Structured Summary: Analysts remain constructive but await stronger catalysts.
News: Company beats quarterly estimates with stable guidance | MarketWire | https://example.com/news1
News: Sector tailwinds improve medium-term demand outlook | FinanceToday | https://example.com/news2
News: Valuation concerns limit near-term upside | DailyMarkets | https://example.com/news3
""",
}

_REVIEW_TEMPLATE = """
Structured Summary: Review of {ticker} analysis quality and consistency.
Data Accuracy: Key valuation and performance figures are internally consistent.
Watchout: Sentiment inputs can change quickly with macro headlines.
Confirmed: Financial health trend aligns with profitability and cashflow signals.
"""

_MOCK_COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "META": "Meta Platforms Inc.",
    "NVDA": "NVIDIA Corporation",
    "RELIANCE.NS": "Reliance Industries Limited",
    "TCS.NS": "Tata Consultancy Services Limited",
    "INFY.NS": "Infosys Limited",
}

_REPORT_TEMPLATE = """
VERDICT: BUY | Confidence: High
Company Name: {company_name}
Ticker: {ticker}
Sector: Technology
Segment: Large Cap
Price: {cur}{price}
Market Cap: {cur}{mcap}
Cap Size: Very Large Cap
Structured Summary: The business is fundamentally healthy, but valuation leaves limited margin of safety at current levels.
Strength: Strong free-cash-flow generation supports buybacks and dividends
Strength: Revenue acceleration across key segments
Risk: Premium valuation leaves little margin of safety in a downturn
Risk: Geopolitical supply-chain exposure could pressure margins
Best Suited For: Long-term growth investors comfortable with moderate volatility
Best Suited For: Dividend-growth portfolio allocations
Not Ideal For: Short-term traders expecting quick gains
Not Ideal For: Risk-averse investors seeking guaranteed returns
Guidance For Existing Holders: Keep core holdings; avoid aggressive averaging at current levels.
Guidance For New Buyers: Wait for improved risk-reward or stronger earnings acceleration before adding.
"""

_HEALTH_TEMPLATE = """
Health Status: Healthy
Revenue Growth Desc: Revenue growth remains resilient | 10.4%
Profit Growth Desc: Margins are stable with mild expansion | 6.0%
Debt Desc: Debt ratio remains manageable | 36%
Cash Desc: Free cash flow supports flexibility | {cur}387.4B
P/E Ratio: 22.6x
P/B Ratio: 2.16x
Forward P/E: 21.2x
Revenue Growth Rate: 10.40%
Earnings Growth Rate: 6.00%
Growth Signal: Revenue momentum remains constructive.
Caution Signal: Margin expansion may slow if input costs rise.
Insight: Fundamentals support a HOLD with selective accumulation on dips.
Structured Summary: Financial profile is healthy with balanced growth and risk.
"""


def _currency_prefix(symbol: str) -> str:
    s = symbol.upper()
    if is_indian_symbol(s):
        return "\u20b9"
    return "$"


def _mock_raw_payloads(symbol: str) -> dict[SubStage, str]:
    ticker = symbol.upper() or "AAPL"
    company_name = _MOCK_COMPANY_NAMES.get(ticker, f"{ticker} Corp.")
    cur = _currency_prefix(ticker)
    is_indian = cur == "\u20b9"
    price = "2,485.60" if is_indian else "198.50"
    mcap = "16.8L Cr" if is_indian else "4.0T"
    payloads = dict(_MOCK_RAW_PAYLOADS_TEMPLATE)
    payloads[SubStage.REVIEWING_ANALYSIS] = _REVIEW_TEMPLATE.format(ticker=ticker)
    payloads[SubStage.GENERATING_INVESTMENT_REPORT] = _REPORT_TEMPLATE.format(
        ticker=ticker, company_name=company_name, cur=cur, price=price, mcap=mcap
    )
    payloads[SubStage.ANALYZING_FINANCIAL_HEALTH] = _HEALTH_TEMPLATE.format(cur=cur)
    return payloads


def _build_mock_log_entries(symbol: str) -> list[LogEntry]:
    entries: list[LogEntry] = [
        LogEntry(
            stage=ProcessingStage.STARTING,
            status_type=StatusType.IN_PROGRESS,
            message=f"Processing symbol: {symbol}",
            symbol=symbol,
        ),
        LogEntry(
            stage=ProcessingStage.VALIDATING,
            substage=SubStage.VALIDATING_SYMBOL,
            status_type=StatusType.SUCCESS,
            message="validating symbol (success)",
            symbol=symbol,
        ),
    ]

    entries.append(
        LogEntry(
            stage=ProcessingStage.DOWNLOADING_DATA,
            status_type=StatusType.IN_PROGRESS,
            message="Downloading data...",
            symbol=symbol,
        )
    )

    download_substages = [
        (SubStage.DOWNLOADING_COMPANY_PROFILE, "downloading company profile"),
        (SubStage.DOWNLOADING_PRICE_HISTORY, "downloading price history"),
        (SubStage.DOWNLOADING_FINANCIALS, "downloading financials"),
        (SubStage.DOWNLOADING_MARKET_INTEL, "downloading market intel"),
        (SubStage.DOWNLOADING_BENCHMARKS, "downloading benchmarks"),
        (SubStage.DOWNLOADING_NEWS, "downloading news"),
        (SubStage.DOWNLOADING_TRENDS, "downloading trends"),
        (SubStage.SAVING_DATA, "saving data"),
    ]
    for substage, msg in download_substages:
        entries.append(
            LogEntry(
                stage=ProcessingStage.DOWNLOADING_DATA,
                substage=substage,
                status_type=StatusType.SUCCESS,
                message=msg,
                symbol=symbol,
            )
        )

    entries.append(
        LogEntry(
            stage=ProcessingStage.ANALYZING,
            status_type=StatusType.IN_PROGRESS,
            message="Processing...",
            symbol=symbol,
        )
    )

    raw_map = _mock_raw_payloads(symbol)
    analysis_substages = [
        SubStage.VALIDATING_DATA_SANITY,
        SubStage.ANALYZING_VALUATION_RATIOS,
        SubStage.ANALYZING_PRICE_PERFORMANCE,
        SubStage.ANALYZING_FINANCIAL_HEALTH,
        SubStage.ANALYZING_MARKET_SENTIMENT,
        SubStage.REVIEWING_ANALYSIS,
        SubStage.GENERATING_INVESTMENT_REPORT,
    ]
    for substage in analysis_substages:
        entries.append(
            LogEntry(
                stage=ProcessingStage.ANALYZING,
                substage=substage,
                status_type=StatusType.IN_PROGRESS,
                message=None,
                symbol=symbol,
            )
        )
        entries.append(
            LogEntry(
                stage=ProcessingStage.ANALYZING,
                substage=substage,
                status_type=StatusType.SUCCESS,
                message=raw_map[substage],
                symbol=symbol,
            )
        )
    return entries


async def stream_mock_logs(
    symbol: str,
    cached_messages: list[str] | None = None,
    delay_ms: int = 1000,
):
    """Fast deterministic SSE stream for UI iteration."""
    safe_symbol = (symbol.upper() or "AAPL").strip()
    yield f"retry: {SSE_RETRY_MS}\n\n"

    if cached_messages:
        for message in cached_messages:
            flat = message.replace("\n", "").replace("\r", "")
            yield f"data: {flat}\n\n"
            await asyncio.sleep(max(delay_ms, 20) / 1000)
    else:
        for entry in _build_mock_log_entries(safe_symbol):
            flat = format_log_entry(entry).replace("\n", "").replace("\r", "")
            yield f"data: {flat}\n\n"
            pause = 1.0 if entry.message == "Processing..." else max(delay_ms, 20) / 1000
            await asyncio.sleep(pause)
    yield "event: complete\ndata: \n\n"
