# SPDX-License-Identifier: MIT
"""Remove units that cards append after a missing value ("N/Ax", "N/A%")."""

import re

# "N/A" followed by a unit, either directly ("N/A%", "N/Ax") or wrapped in its own
# span ('N/A<span class="...">%</span>'). The lookahead keeps words starting with "x".
_NA_WITH_UNIT = re.compile(r"N/A(?:\s*<span[^>]*>\s*(?:%|x)\s*</span>|(?:%|x)(?![A-Za-z]))")


def strip_units_after_na(html: str) -> str:
    return _NA_WITH_UNIT.sub("N/A", html)
