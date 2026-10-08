# SPDX-License-Identifier: MIT
"""Common-name fallback for Google Trends search terms."""

import pytest

from src.core.market.trends import common_name


@pytest.mark.parametrize(
    ("legal", "expected"),
    [
        ("Rivian Automotive, Inc.", "Rivian Automotive"),
        ("JPMorgan Chase & Co.", "JPMorgan Chase"),
        ("Reliance Industries Limited", "Reliance Industries"),
        ("McDonald's Corporation", "McDonald's"),
        ("Alphabet", "Alphabet"),
    ],
)
def test_common_name(legal: str, expected: str) -> None:
    assert common_name(legal) == expected
