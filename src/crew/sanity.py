# SPDX-License-Identifier: MIT
"""Deterministic data-sanity report computed in Python.

Replaces the former LLM data-sanity agent. Every check is a fixed rule
(e.g. "trailing EPS must be positive for P/E to be meaningful"), so the
result is identical on every run for the same data, at zero LLM cost.

Status rules:
  HARD_BLOCKED - a required input is missing or zero (cannot compute)
  SOFT_BLOCKED - inputs exist but are negative (result would be misleading)
  VALID        - all inputs present and meaningful
"""

from __future__ import annotations

import pandas as pd

from src.core.config.data_contracts import (
    CSV_BALANCE_SHEET,
    CSV_CASH_FLOW,
    CSV_COMPANY_INFO,
    CSV_DIVIDENDS,
    CSV_INCOME_STATEMENT,
)
from src.crew.facts import _f, _read_csv, _s
from src.crew.schemas import DataSanityOutput
from src.crew.schemas._base import deterministic_data_sanity_file_statuses
from src.crew.schemas._items import ApplicabilityItem

# (label, value, must_be_positive)
Check = tuple[str, float | None, bool]

_MIN_DIVIDEND_PAYMENTS = 4


def _statement_value(df: pd.DataFrame | None, item: str) -> float | None:
    """Most recent value of a statement line item.

    Statements are stored with line items as rows (first column) and
    periods as columns, newest first.
    """
    if df is None or df.empty or df.shape[1] < 2:
        return None
    labels = df.iloc[:, 0].astype(str).str.strip()
    matches = df[labels == item]
    if matches.empty:
        return None
    value = matches.iloc[0, 1]
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rule(name: str, checks: list[Check]) -> ApplicabilityItem:
    """Missing or zero input -> HARD_BLOCKED; negative -> SOFT_BLOCKED."""
    hard: list[str] = []
    soft: list[str] = []
    ok: list[str] = []
    for label, value, must_be_positive in checks:
        if value is None:
            hard.append(f"{label} -> missing")
        elif must_be_positive and value == 0:
            hard.append(f"{label} -> zero")
        elif must_be_positive and value < 0:
            soft.append(f"{label} -> negative ({value:g})")
        else:
            ok.append(f"{label} -> {value:g}")

    if hard:
        return ApplicabilityItem(
            name=name,
            status="HARD_BLOCKED",
            reason="Required input is missing or zero",
            evidence=hard,
        )
    if soft:
        return ApplicabilityItem(
            name=name,
            status="SOFT_BLOCKED",
            reason="Input is negative, so the result would be misleading",
            evidence=soft,
        )
    return ApplicabilityItem(
        name=name,
        status="VALID",
        reason="All inputs present and meaningful",
        evidence=ok,
    )


def _dividend_payment_count(dividends: pd.DataFrame | None) -> int:
    if dividends is None or dividends.empty:
        return 0
    amounts = pd.to_numeric(dividends.iloc[:, -1], errors="coerce").fillna(0)
    return int((amounts > 0).sum())


def _ddm_rule(row: pd.Series, dividends: pd.DataFrame | None) -> ApplicabilityItem:
    rate = _f(row, "dividendRate")
    if rate is None or rate <= 0:
        shown = "missing" if rate is None else f"{rate:g}"
        return ApplicabilityItem(
            name="DDM",
            status="HARD_BLOCKED",
            reason="Company pays no dividend",
            evidence=[f"company_info.dividendRate -> {shown}"],
        )
    payments = _dividend_payment_count(dividends)
    evidence = [
        f"company_info.dividendRate -> {rate:g}",
        f"dividends.csv -> {payments} payments on record",
    ]
    if payments < _MIN_DIVIDEND_PAYMENTS:
        return ApplicabilityItem(
            name="DDM",
            status="SOFT_BLOCKED",
            reason="Dividend history too short for a dividend model",
            evidence=evidence,
        )
    return ApplicabilityItem(
        name="DDM",
        status="VALID",
        reason="Dividend paid with consistent history",
        evidence=evidence,
    )


def _company_type(row: pd.Series) -> str:
    sector = _s(row, "sector").lower()
    industry = _s(row, "industry").lower()
    if "bank" in industry:
        return "Bank"
    if "financial" in sector:
        return "Financial"
    return "Non-Financial"


def build_data_sanity_report(symbol: str) -> DataSanityOutput:
    """Run every data-sanity rule for ``symbol`` and return the full report."""
    sym = symbol.upper()
    company = _read_csv(sym, CSV_COMPANY_INFO)
    row = company.iloc[0] if company is not None and not company.empty else pd.Series(dtype=object)
    income = _read_csv(sym, CSV_INCOME_STATEMENT)
    balance = _read_csv(sym, CSV_BALANCE_SHEET)
    cash = _read_csv(sym, CSV_CASH_FLOW)
    dividends = _read_csv(sym, CSV_DIVIDENDS)

    def ci(key: str, positive: bool = True) -> Check:
        return (f"company_info.{key}", _f(row, key), positive)

    def inc(item: str, positive: bool = False) -> Check:
        return (f"income_statement.{item}", _statement_value(income, item), positive)

    def bal(item: str, positive: bool = False) -> Check:
        return (f"balance_sheet.{item}", _statement_value(balance, item), positive)

    def cf(item: str, positive: bool = False) -> Check:
        return (f"cash_flow.{item}", _statement_value(cash, item), positive)

    ratios = [
        _rule("PE Ratio", [ci("trailingEps")]),
        _rule("Forward PE", [ci("forwardPE")]),
        _rule("P/B Ratio", [ci("bookValue")]),
        _rule("P/S Ratio", [ci("revenuePerShare")]),
        _rule("EV/EBITDA", [ci("enterpriseValue"), ci("ebitda")]),
        _rule("PEG Ratio", [ci("trailingPE"), ci("earningsGrowth")]),
        _rule("ROE", [inc("Net Income"), bal("Stockholders Equity", positive=True)]),
        _rule("ROA", [inc("Net Income"), bal("Total Assets", positive=True)]),
        _rule("Debt-to-Equity", [bal("Total Debt"), bal("Stockholders Equity", positive=True)]),
        _rule("Current Ratio", [bal("Current Assets"), bal("Current Liabilities", positive=True)]),
        _rule("Gross Margin", [inc("Total Revenue", positive=True), inc("Cost Of Revenue")]),
        _rule("Net Margin", [inc("Net Income"), inc("Total Revenue", positive=True)]),
        _rule("Operating Margin", [inc("Operating Income"), inc("Total Revenue", positive=True)]),
    ]
    models = [
        _rule("DCF", [cf("Free Cash Flow", positive=True), ci("earningsGrowth", positive=False)]),
        _ddm_rule(row, dividends),
        _rule("Graham Number", [ci("trailingEps"), ci("bookValue")]),
        _rule("Relative Valuation", [ci("trailingEps")]),
    ]

    items = [*ratios, *models]
    hard = [item for item in items if item.status == "HARD_BLOCKED"]
    soft = [item for item in items if item.status == "SOFT_BLOCKED"]
    validated, missing = deterministic_data_sanity_file_statuses(sym)

    if hard:
        gate = "FAIL"
    elif soft:
        gate = "PASS_WITH_SKIPS"
    else:
        gate = "PASS"

    # Pass plain dicts: the schema's before-validator counts statuses from dicts.
    return DataSanityOutput.model_validate(
        {
            "summary": f"{len(hard)} hard blocks, {len(soft)} soft blocks identified",
            "gate_status": gate,
            "market_context": "India" if sym.endswith((".NS", ".BO")) else "US",
            "company_type": _company_type(row),
            "validated_files": validated,
            "missing_or_invalid_files": missing,
            "critical_issues": [f"{i.name}: {e}" for i in hard for e in i.evidence],
            "warnings": [f"{i.name}: {e}" for i in soft for e in i.evidence],
            "ratio_applicability": [i.model_dump() for i in ratios],
            "valuation_model_applicability": [i.model_dump() for i in models],
        }
    )
