# SPDX-License-Identifier: MIT
"""Tests for the deterministic data-sanity report (src/crew/sanity.py)."""

from pathlib import Path

import pandas as pd
import pytest

import src.core.config.data_contracts as data_contracts
import src.crew.facts as facts
from src.crew.sanity import build_data_sanity_report
from src.crew.schemas._constants import DATA_SANITY_REQUIRED_FILES

HEALTHY_COMPANY = {
    "trailingEps": 5.0,
    "forwardPE": 20.0,
    "bookValue": 10.0,
    "revenuePerShare": 30.0,
    "enterpriseValue": 1e12,
    "ebitda": 1e11,
    "trailingPE": 25.0,
    "earningsGrowth": 0.10,
    "dividendRate": 1.0,
    "sector": "Technology",
    "industry": "Consumer Electronics",
}
INCOME = {
    "Net Income": 1e11,
    "Total Revenue": 4e11,
    "Cost Of Revenue": 2e11,
    "Operating Income": 1.3e11,
}
BALANCE = {
    "Stockholders Equity": 7e10,
    "Total Assets": 3.5e11,
    "Total Debt": 9e10,
    "Current Assets": 1.5e11,
    "Current Liabilities": 1.6e11,
}
CASH = {"Free Cash Flow": 9e10}


def _statement(items: dict[str, float]) -> pd.DataFrame:
    """Line items as rows, one period column, like the real statement CSVs."""
    return pd.DataFrame({"": list(items), "2025-09-30": list(items.values())})


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every data reader at an empty temporary folder."""
    monkeypatch.setattr(facts, "DATA_DIR", tmp_path)
    monkeypatch.setattr(data_contracts, "DATA_DIR", tmp_path)
    return tmp_path


def _write_dataset(
    root: Path,
    symbol: str = "TEST",
    company: dict | None = None,
    skip: tuple[str, ...] = (),
) -> None:
    folder = root / symbol
    folder.mkdir()
    frames = {
        "company_info.csv": pd.DataFrame([{**HEALTHY_COMPANY, **(company or {})}]),
        "income_statement.csv": _statement(INCOME),
        "balance_sheet.csv": _statement(BALANCE),
        "cash_flow.csv": _statement(CASH),
        "dividends.csv": pd.DataFrame(
            {
                "Date": ["2025-02-01", "2025-05-01", "2025-08-01", "2025-11-01"],
                "Dividends": [0.25, 0.25, 0.25, 0.25],
            }
        ),
    }
    for name in DATA_SANITY_REQUIRED_FILES:
        frames.setdefault(name, pd.DataFrame({"placeholder": [1]}))
    for name, frame in frames.items():
        if name not in skip:
            frame.to_csv(folder / name, index=False)


def _status(report, name: str) -> str:
    items = [*report.ratio_applicability, *report.valuation_model_applicability]
    return {item.name: item.status for item in items}[name]


def test_healthy_company_passes_every_check(data_dir: Path) -> None:
    _write_dataset(data_dir)
    report = build_data_sanity_report("TEST")

    assert report.gate_status == "PASS"
    assert report.missing_or_invalid_files == []
    assert len(report.validated_files) == len(DATA_SANITY_REQUIRED_FILES)
    statuses = [item.status for item in report.ratio_applicability]
    statuses += [item.status for item in report.valuation_model_applicability]
    assert set(statuses) == {"VALID"}
    assert len(statuses) == 17


def test_negative_eps_soft_blocks_earnings_based_checks(data_dir: Path) -> None:
    _write_dataset(data_dir, company={"trailingEps": -2.0})
    report = build_data_sanity_report("TEST")

    assert _status(report, "PE Ratio") == "SOFT_BLOCKED"
    assert _status(report, "Graham Number") == "SOFT_BLOCKED"
    assert _status(report, "Relative Valuation") == "SOFT_BLOCKED"
    assert _status(report, "P/S Ratio") == "VALID"
    assert report.gate_status == "PASS_WITH_SKIPS"


def test_missing_book_value_hard_blocks_pb(data_dir: Path) -> None:
    _write_dataset(data_dir, company={"bookValue": None})
    report = build_data_sanity_report("TEST")

    assert _status(report, "P/B Ratio") == "HARD_BLOCKED"
    assert report.gate_status == "FAIL"


def test_no_dividend_hard_blocks_ddm(data_dir: Path) -> None:
    _write_dataset(data_dir, company={"dividendRate": 0.0})
    report = build_data_sanity_report("TEST")

    assert _status(report, "DDM") == "HARD_BLOCKED"


def test_dividend_without_history_soft_blocks_ddm(data_dir: Path) -> None:
    _write_dataset(data_dir, skip=("dividends.csv",))
    report = build_data_sanity_report("TEST")

    assert _status(report, "DDM") == "SOFT_BLOCKED"


def test_missing_required_file_is_reported(data_dir: Path) -> None:
    _write_dataset(data_dir, skip=("news.csv",))
    report = build_data_sanity_report("TEST")

    assert any("news.csv" in entry for entry in report.missing_or_invalid_files)
    assert not any("news.csv" in entry for entry in report.validated_files)


def test_bank_is_classified_from_industry(data_dir: Path) -> None:
    _write_dataset(
        data_dir, company={"sector": "Financial Services", "industry": "Banks - Diversified"}
    )
    report = build_data_sanity_report("TEST")

    assert report.company_type == "Bank"


def test_indian_symbol_sets_market_context(data_dir: Path) -> None:
    _write_dataset(data_dir, symbol="TEST.NS")
    report = build_data_sanity_report("TEST.NS")

    assert report.market_context == "India"
