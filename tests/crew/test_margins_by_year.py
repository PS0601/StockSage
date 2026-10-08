# SPDX-License-Identifier: MIT
"""Fiscal-year margins must be computed in Python, current vs prior year."""

import pandas as pd

from src.crew.facts import _margins_by_year


def _income(rows: dict[str, tuple[float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "": list(rows),
            "2026-03-31": [v[0] for v in rows.values()],
            "2025-03-31": [v[1] for v in rows.values()],
        }
    )


def test_margins_for_both_years() -> None:
    income = _income(
        {
            "Total Revenue": (1000.0, 900.0),
            "Gross Profit": (256.0, 225.0),
            "Operating Income": (115.0, 105.0),
            "Net Income": (76.0, 65.0),
        }
    )
    lines = _margins_by_year(income)
    assert "Gross Margin FY2026: 25.60% (FY2025: 25.00%)" in lines
    assert "Net Margin FY2026: 7.60% (FY2025: 7.22%)" in lines


def test_bank_without_gross_profit_skips_that_line() -> None:
    income = _income({"Total Revenue": (100.0, 90.0), "Net Income": (30.0, 28.0)})
    lines = _margins_by_year(income)
    assert not any(line.startswith("Gross Margin") for line in lines)
    assert any(line.startswith("Net Margin") for line in lines)
