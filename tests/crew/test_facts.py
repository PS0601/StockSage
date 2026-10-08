"""Unit tests for facts.py helper functions and build_task_facts integration."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd
import pytest

import src.crew.facts as facts_module
from src.crew.facts import (
    _cap_size,
    _cashflow_desc,
    _currency_prefix,
    _debt_desc,
    _earnings_growth_desc,
    _f,
    _fmt_large,
    _fmt_num,
    _health_status,
    _revenue_growth_desc,
    _s,
    _series_close,
)

# ---------------------------------------------------------------------------
# _fmt_num
# ---------------------------------------------------------------------------


def test_fmt_num_none():
    assert _fmt_num(None) == "N/A"


def test_fmt_num_with_suffix():
    assert _fmt_num(15.0, "x") == "15.00x"


def test_fmt_num_with_prefix():
    assert _fmt_num(150.0, "", prefix="$") == "$150.00"


def test_fmt_num_zero_digits():
    assert _fmt_num(1_000_000.0, "", digits=0) == "1,000,000"


# ---------------------------------------------------------------------------
# _fmt_large
# ---------------------------------------------------------------------------


def test_fmt_large_none():
    assert _fmt_large(None) == "N/A"


def test_fmt_large_trillions():
    result = _fmt_large(2_000_000_000_000.0)
    assert result == "$2.00T"


def test_fmt_large_billions():
    result = _fmt_large(5_000_000_000.0)
    assert result == "$5.00B"


def test_fmt_large_millions():
    result = _fmt_large(3_000_000.0)
    assert result == "$3.00M"


def test_fmt_large_small():
    result = _fmt_large(500_000.0)
    assert result == "$500,000"


# ---------------------------------------------------------------------------
# _currency_prefix
# ---------------------------------------------------------------------------


def test_currency_prefix_us():
    assert _currency_prefix("AAPL") == "$"


def test_currency_prefix_nse():
    assert _currency_prefix("RELIANCE.NS") == "\u20b9"


def test_currency_prefix_bse():
    assert _currency_prefix("TCS.BO") == "\u20b9"


# ---------------------------------------------------------------------------
# _cap_size
# ---------------------------------------------------------------------------


def test_cap_size_none():
    assert _cap_size(None) == "N/A"


def test_cap_size_very_large():
    assert _cap_size(300_000_000_000.0) == "Very Large Cap"


def test_cap_size_large():
    assert _cap_size(50_000_000_000.0) == "Large Cap"


def test_cap_size_mid():
    assert _cap_size(5_000_000_000.0) == "Mid Cap"


def test_cap_size_small():
    assert _cap_size(500_000_000.0) == "Small Cap"


def test_cap_size_micro():
    assert _cap_size(50_000_000.0) == "Micro Cap"


# ---------------------------------------------------------------------------
# Growth/debt/cash description helpers
# ---------------------------------------------------------------------------


def test_revenue_growth_rapid():
    assert _revenue_growth_desc(0.20) == "Growing rapidly"


def test_revenue_growth_steady():
    assert _revenue_growth_desc(0.10) == "Grows steadily every year"


def test_revenue_growth_moderate():
    assert _revenue_growth_desc(0.05) == "Moderate revenue growth"


def test_revenue_growth_small():
    assert _revenue_growth_desc(0.01) == "Small revenue gains"


def test_revenue_growth_declining():
    assert _revenue_growth_desc(-0.05) == "Revenue is declining"


def test_revenue_growth_none():
    assert _revenue_growth_desc(None) == "Revenue data not available"


def test_earnings_growth_strong():
    assert _earnings_growth_desc(0.20) == "Strong profit growth"


def test_earnings_growth_healthy():
    assert _earnings_growth_desc(0.08) == "Healthy profit growth"


def test_earnings_growth_small():
    assert _earnings_growth_desc(0.02) == "Small profit gains"


def test_earnings_growth_declining():
    assert _earnings_growth_desc(-0.05) == "Profits are declining"


def test_earnings_growth_none():
    assert _earnings_growth_desc(None) == "Earnings data not available"


def test_debt_desc_very_low():
    assert _debt_desc(20.0) == "Very low debt levels"


def test_debt_desc_manageable():
    assert _debt_desc(50.0) == "Debt is manageable and under control"


def test_debt_desc_moderate():
    assert _debt_desc(80.0) == "Moderate debt levels"


def test_debt_desc_high():
    assert _debt_desc(110.0) == "High debt levels - needs monitoring"


def test_debt_desc_none():
    assert _debt_desc(None) == "Debt data not available"


def test_cashflow_desc_positive():
    assert _cashflow_desc(100_000_000.0) == "Generates strong cash flow"


def test_cashflow_desc_negative():
    assert _cashflow_desc(-50_000_000.0) == "Cash flow needs improvement"


def test_cashflow_desc_none():
    assert _cashflow_desc(None) == "Cash flow data not available"


# ---------------------------------------------------------------------------
# _health_status
# ---------------------------------------------------------------------------


def test_health_status_strong():
    assert _health_status(0.10, 50.0, 1_000_000.0, 0.20) == "STRONG"


def test_health_status_stable():
    assert _health_status(0.10, 50.0, None, 0.20) == "STABLE"


def test_health_status_mixed():
    assert _health_status(0.10, None, None, 0.20) == "MIXED"


def test_health_status_weak():
    assert _health_status(None, None, None) == "WEAK"


# ---------------------------------------------------------------------------
# _series_close
# ---------------------------------------------------------------------------


def test_series_close_normal():
    df = pd.DataFrame({"Close": [100.0, 110.0, 120.0]})
    arr = _series_close(df)
    assert list(arr) == [100.0, 110.0, 120.0]


def test_series_close_none():
    assert len(_series_close(None)) == 0


def test_series_close_missing_column():
    df = pd.DataFrame({"Open": [100.0, 110.0]})
    assert len(_series_close(df)) == 0


def test_series_close_empty():
    df = pd.DataFrame({"Close": []})
    assert len(_series_close(df)) == 0


# ---------------------------------------------------------------------------
# _f and _s row extractors
# ---------------------------------------------------------------------------


def test_f_present():
    row = pd.Series({"trailingPE": 22.5})
    assert _f(row, "trailingPE") == pytest.approx(22.5)


def test_f_missing_key():
    row = pd.Series({"other": 1.0})
    assert _f(row, "trailingPE") is None


def test_f_nan_returns_default():
    row = pd.Series({"trailingPE": float("nan")})
    assert _f(row, "trailingPE") is None


def test_f_explicit_default():
    row = pd.Series(dtype=object)
    assert _f(row, "anything", default=99.0) == 99.0


def test_s_present():
    row = pd.Series({"sector": "Technology"})
    assert _s(row, "sector") == "Technology"


def test_s_missing():
    row = pd.Series(dtype=object)
    assert _s(row, "sector") == ""


def test_s_nan():
    row = pd.Series({"sector": float("nan")})
    assert _s(row, "sector") == ""


# ---------------------------------------------------------------------------
# build_task_facts — integration via monkeypatched DATA_DIR
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_data_dir(tmp_path, monkeypatch):
    """Set DATA_DIR to a tmp directory and create minimal CSVs for FAKE symbol."""
    sym = "FAKE"
    sym_dir = tmp_path / sym
    sym_dir.mkdir()

    # company_info.csv — one row with common scalar fields
    company_csv = textwrap.dedent("""\
        shortName,trailingPE,forwardPE,priceToBook,priceToSalesTrailing12Months,\
pegRatio,enterpriseToEbitda,returnOnEquity,returnOnAssets,grossMargins,\
revenueGrowth,earningsGrowth,debtToEquity,currentRatio,operatingCashflow,\
marketCap,sector,industry
        FakeCo Inc,20.0,18.0,3.0,5.0,1.5,12.0,0.15,0.08,0.60,0.10,0.12,50.0,2.0,\
5000000000,200000000000,Technology,Software
    """)
    (sym_dir / "company_info.csv").write_text(company_csv)

    # historical_prices.csv — 30 days of ascending prices
    dates = pd.date_range("2024-01-01", periods=30)
    prices = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Close": range(100, 130)})
    prices.to_csv(sym_dir / "historical_prices.csv", index=False)

    # market_index.csv — same shape
    market = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Close": range(200, 230)})
    market.to_csv(sym_dir / "market_index.csv", index=False)

    # income_statement.csv — minimal with Total Revenue rows
    income = pd.DataFrame(
        {
            "Breakdown": ["Total Revenue", "Net Income"],
            "2023": [1_000_000_000, 150_000_000],
            "2022": [900_000_000, 130_000_000],
        }
    )
    income.to_csv(sym_dir / "income_statement.csv", index=False)

    # cash_flow.csv — minimal with Free Cash Flow row
    cash = pd.DataFrame(
        {
            "Breakdown": ["Free Cash Flow", "Operating Cash Flow"],
            "2023": [200_000_000, 300_000_000],
            "2022": [180_000_000, 270_000_000],
        }
    )
    cash.to_csv(sym_dir / "cash_flow.csv", index=False)

    # recommendations.csv
    recs = pd.DataFrame(
        {
            "period": ["0m", "-1m"],
            "strongBuy": [5, 4],
            "buy": [10, 8],
            "hold": [3, 3],
            "sell": [1, 1],
            "strongSell": [0, 0],
        }
    )
    recs.to_csv(sym_dir / "recommendations.csv", index=False)

    # institutional_holders.csv
    holders = pd.DataFrame(
        {"Holder": ["Fund A", "Fund B"], "Shares": [1_000_000, 500_000], "% Out": [0.05, 0.025]}
    )
    holders.to_csv(sym_dir / "institutional_holders.csv", index=False)

    # news.csv — minimal
    news = pd.DataFrame(
        {
            "title": ["FakeCo hits record high", "FakeCo expands globally"],
            "publisher": ["Reuters", "Bloomberg"],
            "sentiment": ["positive", "positive"],
        }
    )
    news.to_csv(sym_dir / "news.csv", index=False)

    # Patch DATA_DIR in the facts module
    monkeypatch.setattr(
        facts_module, "_read_csv", lambda sym, fname: _patched_read_csv(sym, fname, tmp_path)
    )
    return tmp_path


def _patched_read_csv(symbol: str, file_name: str, data_dir: Path) -> pd.DataFrame | None:
    path = data_dir / symbol / file_name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def test_build_task_facts_returns_all_keys(fake_data_dir):
    result = facts_module.build_task_facts("FAKE")
    expected_keys = {
        "analyze_valuation_ratios",
        "analyze_price_performance",
        "analyze_financial_health",
        "analyze_market_sentiment",
        "generate_investment_report",
    }
    assert expected_keys == set(result.keys())


def test_build_task_facts_valuation_contains_pe(fake_data_dir):
    result = facts_module.build_task_facts("FAKE")
    assert "P/E Ratio:" in result["analyze_valuation_ratios"]


def test_build_task_facts_performance_contains_return(fake_data_dir):
    result = facts_module.build_task_facts("FAKE")
    assert "Total Return" in result["analyze_price_performance"]


def test_build_task_facts_health_contains_status(fake_data_dir):
    result = facts_module.build_task_facts("FAKE")
    health = result["analyze_financial_health"]
    assert "Health Status:" in health


def test_build_task_facts_sentiment_not_empty(fake_data_dir):
    result = facts_module.build_task_facts("FAKE")
    assert len(result["analyze_market_sentiment"]) > 0


def test_build_task_facts_missing_csvs():
    """build_task_facts handles completely missing data gracefully."""
    import unittest.mock as mock

    with mock.patch("src.crew.facts._read_csv", return_value=None):
        result = facts_module.build_task_facts("MISSING")

    assert "analyze_valuation_ratios" in result
    assert "analyze_price_performance" in result
    # Performance falls back to insufficient-data message
    assert "Insufficient" in result["analyze_price_performance"]
