# SPDX-License-Identifier: MIT
"""Health badge: STRONG needs growing revenue, low debt, positive cash flow AND growing earnings."""

from src.crew.facts import _health_status


def test_all_four_strong() -> None:
    assert _health_status(0.16, 78.0, 1e11, 0.29) == "STRONG"


def test_falling_earnings_is_not_strong() -> None:
    # TSLA-style: revenue up, low debt, positive cash flow, earnings down
    assert _health_status(0.255, 18.0, 1.9e10, -0.03) == "STABLE"


def test_cash_burner_with_high_debt_is_weak() -> None:
    # RIVN-style: revenue up only
    assert _health_status(0.27, 104.0, -1.8e9, None) == "WEAK"
