# SPDX-License-Identifier: MIT
"""CSV storage module for stock data."""

import logging
import re
from dataclasses import fields
from pathlib import Path
from typing import List

import pandas as pd

from src.core.config.data_contracts import (
    CSV_ALIASES_BY_FIELD,
    CSV_COMPANY_INFO,
    CSV_FILE_BY_FIELD,
    DATA_DIR,
)
from src.core.market.stock_data import StockData

logger = logging.getLogger(__name__)


_SAFE_SYMBOL_RE = re.compile(r"^[A-Z0-9.-]{1,20}$")


def _validate_symbol_for_path(symbol: str) -> str:
    """Reject symbols that could escape the data directory via path traversal."""
    # A name made only of dots ("." or "..") would point at the data folder or its parent.
    if not _SAFE_SYMBOL_RE.fullmatch(symbol) or set(symbol) == {"."}:
        raise ValueError(f"Invalid symbol for storage: {symbol!r}")
    return symbol


class CSVStorage:
    """Saves stock data to CSV files organized by symbol."""

    def __init__(self, base_dir: Path | str = DATA_DIR):
        self._base_dir = Path(base_dir)

    def save(self, stock_data: StockData) -> List[str]:
        """Save all stock data to CSVs under {base_dir}/{SYMBOL}/."""
        _validate_symbol_for_path(stock_data.symbol)
        symbol_dir = self._base_dir / stock_data.symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        saved: List[str] = []

        self._save_dict(stock_data.company_info, symbol_dir / CSV_COMPANY_INFO, saved)

        for sub in (
            stock_data.prices,
            stock_data.financials,
            stock_data.market_intel,
            stock_data.benchmarks,
        ):
            for f in fields(sub):
                data = getattr(sub, f.name)
                path = symbol_dir / CSV_FILE_BY_FIELD.get(f.name, f"{f.name}.csv")
                if isinstance(data, pd.DataFrame):
                    self._save_dataframe(data, path, saved)
                    for alias_name in CSV_ALIASES_BY_FIELD.get(f.name, ()):
                        self._save_dataframe(data, symbol_dir / alias_name, saved)
                elif isinstance(data, list) and data:
                    self._save_list(data, path, saved)

        return saved

    @staticmethod
    def _save_dataframe(df: pd.DataFrame, path: Path, saved: List[str]) -> None:
        if df is None or df.empty:
            return
        try:
            df.to_csv(path)
            saved.append(str(path))
        except Exception as e:
            logger.warning("Failed to save %s: %s", path.stem, e)

    @staticmethod
    def _save_dict(data: dict, path: Path, saved: List[str]) -> None:
        if not data:
            return
        try:
            pd.DataFrame([data]).to_csv(path, index=False)
            saved.append(str(path))
        except Exception as e:
            logger.warning("Failed to save %s: %s", path.stem, e)

    @staticmethod
    def _save_list(data: list, path: Path, saved: List[str]) -> None:
        try:
            pd.DataFrame(data).to_csv(path, index=False)
            saved.append(str(path))
        except Exception as e:
            logger.warning("Failed to save %s: %s", path.stem, e)
