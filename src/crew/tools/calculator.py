# SPDX-License-Identifier: MIT
"""Financial calculator tool for computing ratios and performance metrics."""
from typing import Any, Optional, Type, Union

import numpy as np
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

PriceSeries = Optional[Union[str, list[float]]]


class FinancialCalculatorInput(BaseModel):
    """Every parameter any metric can take. Unused ones stay None."""

    metric: str = Field(..., description="Metric to compute, e.g. 'ps_ratio', 'beta'")
    price: Optional[float] = None
    earnings_per_share: Optional[float] = None
    book_value_per_share: Optional[float] = None
    revenue_per_share: Optional[float] = None
    enterprise_value: Optional[float] = None
    ebitda: Optional[float] = None
    pe_ratio: Optional[float] = None
    earnings_growth_rate: Optional[float] = None
    net_income: Optional[float] = None
    shareholders_equity: Optional[float] = None
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    revenue: Optional[float] = None
    cost_of_goods_sold: Optional[float] = None
    operating_income: Optional[float] = None
    free_cash_flow: Optional[float] = None
    growth_rate: Optional[float] = None
    discount_rate: Optional[float] = None
    terminal_growth_rate: Optional[float] = None
    years: Optional[int] = None
    shares_outstanding: Optional[float] = None
    dividend_per_share: Optional[float] = None
    dividend_growth_rate: Optional[float] = None
    required_return: Optional[float] = None
    sector_pe: Optional[float] = None
    market_pe: Optional[float] = None
    risk_free_rate: Optional[float] = None
    prices: PriceSeries = None
    stock_prices: PriceSeries = None
    market_prices: PriceSeries = None


class FinancialCalculatorTool(BaseTool):
    """Computes financial ratios and performance metrics from raw numbers."""

    name: str = "financial_calculator"
    args_schema: Type[BaseModel] = FinancialCalculatorInput
    description: str = (
        "Calculates a financial metric given its type and numeric inputs. "
        "Supported metric types and their required parameters:\n"
        "  pe_ratio: price, earnings_per_share\n"
        "  pb_ratio: price, book_value_per_share\n"
        "  ps_ratio: price, revenue_per_share\n"
        "  ev_ebitda: enterprise_value, ebitda\n"
        "  peg_ratio: pe_ratio, earnings_growth_rate\n"
        "  roe: net_income, shareholders_equity\n"
        "  roa: net_income, total_assets\n"
        "  debt_to_equity: total_debt, shareholders_equity\n"
        "  current_ratio: current_assets, current_liabilities\n"
        "  gross_margin: revenue, cost_of_goods_sold\n"
        "  net_margin: net_income, revenue\n"
        "  operating_margin: operating_income, revenue\n"
        "  dcf: free_cash_flow, growth_rate, discount_rate, terminal_growth_rate (default 0.03), years (default 5), shares_outstanding\n"
        "  ddm: dividend_per_share, dividend_growth_rate, required_return\n"
        "  graham_number: earnings_per_share, book_value_per_share\n"
        "  relative_valuation: earnings_per_share, sector_pe, market_pe\n"
        "  returns: prices (comma-separated, oldest first)\n"
        "  volatility: prices (comma-separated, oldest first)\n"
        "  sharpe_ratio: prices (comma-separated), risk_free_rate (default 0.04)\n"
        "  max_drawdown: prices (comma-separated, oldest first)\n"
        "  beta: stock_prices (comma-separated), market_prices (comma-separated)"
    )

    def _run(self, metric: str, **kwargs: Any) -> str:
        try:
            handler = _METRIC_HANDLERS.get(metric)
            if not handler:
                return f"Unknown metric '{metric}'. Supported: {', '.join(_METRIC_HANDLERS)}"
            # Drop fields the agent didn't fill in, so handler defaults still apply
            args = {k: v for k, v in kwargs.items() if v is not None}
            value = handler(**args)  # type: ignore[operator]
            return f"{metric} = {value}"
        except Exception as e:
            return f"Error calculating {metric}: {e}"


def _parse_number(val: str) -> float:
    """Parse a single numeric token, stripping %, $, and whitespace."""
    cleaned = val.strip().replace("$", "").replace(",", "")
    if cleaned.endswith("%"):
        return float(cleaned[:-1])
    return float(cleaned)


def _parse_prices(raw: Any) -> np.ndarray:
    if isinstance(raw, str):
        cleaned = raw.strip().strip("[]()").strip()
        return np.array([_parse_number(x) for x in cleaned.split(",") if x.strip()])
    if isinstance(raw, (list, tuple)):
        return np.array([float(x) for x in raw])
    raise ValueError("Prices must be a comma-separated string or list of numbers")


def _safe_div(a: float, b: float, label: str = "value") -> float:
    a, b = float(a), float(b)
    if b == 0:
        raise ZeroDivisionError(f"Cannot compute {label}: divisor is zero")
    return round(a / b, 4)


def _pe_ratio(price: float, earnings_per_share: float, **_: Any) -> float:
    return _safe_div(price, earnings_per_share, "P/E ratio")


def _pb_ratio(price: float, book_value_per_share: float, **_: Any) -> float:
    return _safe_div(price, book_value_per_share, "P/B ratio")


def _ps_ratio(price: float, revenue_per_share: float, **_: Any) -> float:
    return _safe_div(price, revenue_per_share, "P/S ratio")


def _ev_ebitda(enterprise_value: float, ebitda: float, **_: Any) -> float:
    return _safe_div(enterprise_value, ebitda, "EV/EBITDA")


def _peg_ratio(pe_ratio: float, earnings_growth_rate: float, **_: Any) -> float:
    return _safe_div(pe_ratio, earnings_growth_rate, "PEG ratio")


def _roe(net_income: float, shareholders_equity: float, **_: Any) -> str:
    return f"{_safe_div(net_income, shareholders_equity, 'ROE') * 100:.2f}%"


def _roa(net_income: float, total_assets: float, **_: Any) -> str:
    return f"{_safe_div(net_income, total_assets, 'ROA') * 100:.2f}%"


def _debt_to_equity(total_debt: float, shareholders_equity: float, **_: Any) -> float:
    return _safe_div(total_debt, shareholders_equity, "Debt-to-Equity")


def _current_ratio(current_assets: float, current_liabilities: float, **_: Any) -> float:
    return _safe_div(current_assets, current_liabilities, "Current Ratio")


def _gross_margin(revenue: float, cost_of_goods_sold: float, **_: Any) -> str:
    margin = (float(revenue) - float(cost_of_goods_sold)) / float(revenue)
    return f"{round(margin * 100, 2)}%"


def _net_margin(net_income: float, revenue: float, **_: Any) -> str:
    return f"{_safe_div(net_income, revenue, 'Net Margin') * 100:.2f}%"


def _operating_margin(operating_income: float, revenue: float, **_: Any) -> str:
    return f"{_safe_div(operating_income, revenue, 'Operating Margin') * 100:.2f}%"


def _returns(prices: Any, **_: Any) -> str:
    p = _parse_prices(prices)
    if len(p) < 2:
        raise ValueError("Need at least 2 prices to compute returns")
    total_return = (p[-1] - p[0]) / p[0]
    trading_days = len(p)
    annualized = (1 + total_return) ** (252 / trading_days) - 1
    return f"Total: {total_return * 100:.2f}%, Annualized: {annualized * 100:.2f}%"


def _volatility(prices: Any, **_: Any) -> str:
    p = _parse_prices(prices)
    if len(p) < 3:
        raise ValueError("Need at least 3 prices to compute volatility")
    daily_returns = np.diff(p) / p[:-1]
    annual_vol = np.std(daily_returns, ddof=1) * np.sqrt(252)
    return f"{annual_vol * 100:.2f}% annualized"


def _sharpe_ratio(prices: Any, risk_free_rate: float = 0.04, **_: Any) -> float:
    p = _parse_prices(prices)
    if len(p) < 3:
        raise ValueError("Need at least 3 prices to compute Sharpe ratio")
    daily_returns = np.diff(p) / p[:-1]
    excess = daily_returns - float(risk_free_rate) / 252
    if np.std(excess, ddof=1) == 0:
        return 0.0
    return round(float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(252)), 4)


def _max_drawdown(prices: Any, **_: Any) -> str:
    p = _parse_prices(prices)
    peak = np.maximum.accumulate(p)
    drawdown = (p - peak) / peak
    return f"{np.min(drawdown) * 100:.2f}%"


def _dcf(
    free_cash_flow: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
    shares_outstanding: float = 1,
    **_: Any,
) -> str:
    """Discounted Cash Flow intrinsic value estimation."""
    fcf = float(free_cash_flow)
    g = float(growth_rate)
    r = float(discount_rate)
    tg = float(terminal_growth_rate)
    n = int(years)
    shares = float(shares_outstanding)

    if r <= tg:
        raise ValueError("Discount rate must exceed terminal growth rate")
    if shares <= 0:
        raise ValueError("Shares outstanding must be positive")

    pv_fcfs = sum(fcf * (1 + g) ** t / (1 + r) ** t for t in range(1, n + 1))
    terminal_fcf = fcf * (1 + g) ** n * (1 + tg)
    terminal_value = terminal_fcf / (r - tg)
    pv_terminal = terminal_value / (1 + r) ** n
    enterprise_value = pv_fcfs + pv_terminal
    intrinsic_per_share = enterprise_value / shares

    return (
        f"Intrinsic Value: ${intrinsic_per_share:,.2f}/share "
        f"(PV of FCFs: ${pv_fcfs:,.0f}, PV of Terminal: ${pv_terminal:,.0f}, "
        f"Total Enterprise Value: ${enterprise_value:,.0f})"
    )


def _ddm(
    dividend_per_share: float,
    dividend_growth_rate: float,
    required_return: float,
    **_: Any,
) -> str:
    """Gordon Growth / Dividend Discount Model."""
    d = float(dividend_per_share)
    g = float(dividend_growth_rate)
    r = float(required_return)

    if r <= g:
        raise ValueError("Required return must exceed dividend growth rate")
    if d <= 0:
        return "DDM not applicable — company does not pay dividends"

    d1 = d * (1 + g)
    intrinsic = d1 / (r - g)
    return f"Intrinsic Value (DDM): ${intrinsic:,.2f}/share (next year dividend: ${d1:.2f}, r={r:.1%}, g={g:.1%})"


def _graham_number(earnings_per_share: float, book_value_per_share: float, **_: Any) -> str:
    """Benjamin Graham's intrinsic value formula: sqrt(22.5 * EPS * BVPS)."""
    eps = float(earnings_per_share)
    bvps = float(book_value_per_share)

    if eps <= 0:
        return f"Graham Number not applicable — EPS is negative (${eps:.2f})"
    if bvps <= 0:
        return f"Graham Number not applicable — Book Value is negative (${bvps:.2f})"

    graham = np.sqrt(22.5 * eps * bvps)
    return f"Graham Number: ${graham:,.2f}/share (based on EPS=${eps:.2f}, Book Value=${bvps:.2f})"


def _relative_valuation(
    earnings_per_share: float, sector_pe: float, market_pe: float, **_: Any
) -> str:
    """Fair value estimate based on sector and market average P/E multiples."""
    eps = float(earnings_per_share)
    s_pe = float(sector_pe)
    m_pe = float(market_pe)

    if eps <= 0:
        return f"Relative valuation not applicable — EPS is negative (${eps:.2f})"

    sector_fair = eps * s_pe
    market_fair = eps * m_pe
    blended_fair = (sector_fair + market_fair) / 2

    return (
        f"Sector-based Fair Value: ${sector_fair:,.2f}/share (EPS x sector P/E of {s_pe:.1f}x), "
        f"Market-based Fair Value: ${market_fair:,.2f}/share (EPS x market P/E of {m_pe:.1f}x), "
        f"Blended Estimate: ${blended_fair:,.2f}/share"
    )


def _beta(stock_prices: Any, market_prices: Any, **_: Any) -> float:
    sp = _parse_prices(stock_prices)
    mp = _parse_prices(market_prices)
    min_len = min(len(sp), len(mp))
    if min_len < 3:
        raise ValueError("Need at least 3 price points for beta")
    sr = np.diff(sp[:min_len]) / sp[: min_len - 1]
    mr = np.diff(mp[:min_len]) / mp[: min_len - 1]
    cov = np.cov(sr, mr)
    if cov[1, 1] == 0:
        return 0.0
    return round(float(cov[0, 1] / cov[1, 1]), 4)


_METRIC_HANDLERS = {
    "pe_ratio": _pe_ratio,
    "pb_ratio": _pb_ratio,
    "ps_ratio": _ps_ratio,
    "ev_ebitda": _ev_ebitda,
    "peg_ratio": _peg_ratio,
    "roe": _roe,
    "roa": _roa,
    "debt_to_equity": _debt_to_equity,
    "current_ratio": _current_ratio,
    "gross_margin": _gross_margin,
    "net_margin": _net_margin,
    "operating_margin": _operating_margin,
    "dcf": _dcf,
    "ddm": _ddm,
    "graham_number": _graham_number,
    "relative_valuation": _relative_valuation,
    "returns": _returns,
    "volatility": _volatility,
    "sharpe_ratio": _sharpe_ratio,
    "max_drawdown": _max_drawdown,
    "beta": _beta,
}
