# SPDX-License-Identifier: MIT
"""Symbol validation module with hierarchical checks."""

import re

import yfinance as yf

from src.core.config.enums import ValidationErrorCode
from src.core.config.markets import is_indian_symbol as _is_indian_symbol
from src.core.config.models import ValidationResult
from src.core.validation.base import FormatValidator, MarketValidator

MARKET_NAMES = {"US": "US", "IN": "Indian"}


class USFormatValidator(FormatValidator):
    """Validates US ticker format."""

    # Optional share class, as Yahoo writes it: BRK-B, BF-B, HEI-A
    PATTERN = re.compile(r"^[A-Z]{1,5}(-[A-Z])?$")

    def validate(self, symbol: str) -> ValidationResult:
        if self.PATTERN.match(symbol):
            return ValidationResult(is_valid=True, market="US")
        return ValidationResult(
            is_valid=False,
            error_code=ValidationErrorCode.INVALID_FORMAT.value,
            error_message="Invalid symbol format. US symbols: 1-5 letters (e.g., AAPL).",
            market="US",
        )


class IndianFormatValidator(FormatValidator):
    """Validates Indian ticker format."""

    PATTERN = re.compile(r"^[A-Z0-9]+\.(NS|BO)$")

    def validate(self, symbol: str) -> ValidationResult:
        if self.PATTERN.match(symbol):
            return ValidationResult(is_valid=True, market="IN")
        return ValidationResult(
            is_valid=False,
            error_code=ValidationErrorCode.INVALID_FORMAT.value,
            error_message="Invalid symbol format. Indian symbols: SYMBOL.NS or SYMBOL.BO (e.g., RELIANCE.NS).",
            market="IN",
        )


class YFinanceMarketValidator(MarketValidator):
    """Validates symbol exists in market using yfinance."""

    def __init__(self, market: str):
        self.market = market

    def validate(self, symbol: str) -> ValidationResult:
        try:
            data = yf.Ticker(symbol).history(period="1d")

            if data.empty:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.SYMBOL_NOT_FOUND.value,
                    error_message=f"Symbol '{symbol}' not found in {MARKET_NAMES[self.market]} market.",
                    market=self.market,
                )

            return ValidationResult(is_valid=True, market=self.market)
        except (ConnectionError, TimeoutError, OSError) as e:
            return ValidationResult(
                is_valid=False,
                error_code=ValidationErrorCode.MARKET_ERROR.value,
                error_message=f"Network error validating symbol: {e}",
                market=self.market,
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_code=ValidationErrorCode.MARKET_ERROR.value,
                error_message=f"Error validating symbol: {e}",
                market=self.market,
            )


class ValidatorFactory:
    """Factory for creating validators based on symbol format."""

    @staticmethod
    def is_indian_symbol(symbol: str) -> bool:
        return _is_indian_symbol(symbol)

    @staticmethod
    def create_format_validator(symbol: str) -> FormatValidator:
        if ValidatorFactory.is_indian_symbol(symbol):
            return IndianFormatValidator()
        return USFormatValidator()

    @staticmethod
    def create_market_validator(symbol: str) -> MarketValidator:
        market = "IN" if ValidatorFactory.is_indian_symbol(symbol) else "US"
        return YFinanceMarketValidator(market)


def validate_symbol(symbol: str) -> ValidationResult:
    """
    Validate if a stock symbol exists and is valid for US or Indian markets.

    Performs hierarchical validation:
    1. Format validation (regex) - Fast check
    2. Market validation (yfinance) - Verifies symbol actually exists

    Args:
        symbol: Stock symbol to validate (e.g., "AAPL", "RELIANCE.NS")

    Returns:
        ValidationResult with is_valid, error_code, error_message, and market
    """
    symbol_upper = symbol.upper()

    format_result = ValidatorFactory.create_format_validator(symbol_upper).validate(symbol_upper)
    if not format_result.is_valid:
        return format_result

    return ValidatorFactory.create_market_validator(symbol_upper).validate(symbol_upper)
