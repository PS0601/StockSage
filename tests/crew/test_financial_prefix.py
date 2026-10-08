# SPDX-License-Identifier: MIT
# Operating cash flow uses the financial-statement currency, not always dollars.

import pandas as pd

from src.crew.facts import _financial_prefix, _health_insight


def test_prefix_by_financial_currency() -> None:
    assert _financial_prefix(pd.Series({"financialCurrency": "INR"})) == "\u20b9"
    assert _financial_prefix(pd.Series({"financialCurrency": "USD"})) == "$"
    assert _financial_prefix(pd.Series({"financialCurrency": "TWD"})) == "TWD "


def test_insight_uses_given_prefix() -> None:
    assert "\u20b9" in _health_insight(5.2e11, 10.0, "\u20b9")
