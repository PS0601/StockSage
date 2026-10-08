# SPDX-License-Identifier: MIT
"""Market detection helpers shared across the app."""

INDIAN_SYMBOL_SUFFIXES = (".NS", ".BO")


def is_indian_symbol(symbol: str) -> bool:
    """True for NSE/BSE tickers such as RELIANCE.NS or TCS.BO (case-insensitive)."""
    return symbol.strip().upper().endswith(INDIAN_SYMBOL_SUFFIXES)
