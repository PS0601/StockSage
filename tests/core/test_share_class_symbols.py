# SPDX-License-Identifier: MIT
# Share-class tickers (BRK-B) are valid; storage still rejects unsafe names.

import pytest

from src.core.market.storage import _validate_symbol_for_path
from src.core.validation.validation import validate_symbol


@pytest.mark.parametrize("symbol", ["AAPL", "BRK-B", "BF-B", "RELIANCE.NS"])
def test_valid_symbols(symbol: str) -> None:
    assert validate_symbol(symbol).is_valid


@pytest.mark.parametrize("symbol", ["BRK-BB", "BRK-", "-B", "TOOLONG"])
def test_invalid_symbols(symbol: str) -> None:
    assert not validate_symbol(symbol).is_valid


def test_storage_accepts_share_class() -> None:
    assert _validate_symbol_for_path("BRK-B") == "BRK-B"


@pytest.mark.parametrize("symbol", [".", "..", "../X", "A/B"])
def test_storage_rejects_unsafe_names(symbol: str) -> None:
    with pytest.raises(ValueError):
        _validate_symbol_for_path(symbol)
