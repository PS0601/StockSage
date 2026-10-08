# SPDX-License-Identifier: MIT
"""Deterministic facts builder for stable UI metrics."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.core.config.data_contracts import (
    CSV_BALANCE_SHEET,
    CSV_CASH_FLOW,
    CSV_COMPANY_INFO,
    CSV_HISTORICAL_PRICES,
    CSV_INCOME_STATEMENT,
    CSV_INSTITUTIONAL_HOLDERS,
    CSV_MARKET_INDEX,
    CSV_NEWS,
    CSV_RECOMMENDATIONS,
    DATA_DIR,
)
from src.core.config.markets import is_indian_symbol


def build_task_facts(symbol: str) -> dict[str, str]:
    sym = symbol.upper()
    company = _read_csv(sym, CSV_COMPANY_INFO)
    prices = _read_csv(sym, CSV_HISTORICAL_PRICES)
    market = _read_csv(sym, CSV_MARKET_INDEX)
    income = _read_csv(sym, CSV_INCOME_STATEMENT)
    cash = _read_csv(sym, CSV_CASH_FLOW)
    balance = _read_csv(sym, CSV_BALANCE_SHEET)
    recs = _read_csv(sym, CSV_RECOMMENDATIONS)
    holders = _read_csv(sym, CSV_INSTITUTIONAL_HOLDERS)
    news = _read_csv(sym, CSV_NEWS)

    company_row = (
        company.iloc[0] if company is not None and not company.empty else pd.Series(dtype=object)
    )

    facts: dict[str, str] = {}
    facts["analyze_valuation_ratios"] = _valuation_facts(company_row, cash, sym)
    facts["analyze_price_performance"] = _performance_facts(prices, market)
    facts["analyze_financial_health"] = _financial_health_facts(company_row, income, cash, balance)
    facts["analyze_market_sentiment"] = _sentiment_facts(recs, holders, news)
    facts["generate_investment_report"] = _company_basics_facts(
        company_row, sym, recs, holders, prices, market
    )
    return facts


def _read_csv(symbol: str, file_name: str) -> pd.DataFrame | None:
    path = DATA_DIR / symbol / file_name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _f(row: pd.Series, key: str, default: float | None = None) -> float | None:
    if key not in row:
        return default
    val = row.get(key)
    if pd.isna(val):
        return default
    try:
        return float(val)
    except Exception:
        return default


def _yoy_change(current: float, previous: float) -> float:
    """Change vs the prior period, as a fraction.

    Divides by abs(previous) so the sign stays meaningful when the prior value is
    negative (e.g. negative free cash flow): improvement is positive, deterioration
    is negative. For positive prior values this equals the usual formula.
    """
    return (current - previous) / abs(previous)


def _s(row: pd.Series, key: str, default: str = "") -> str:
    if key not in row:
        return default
    val = row.get(key)
    if pd.isna(val):
        return default
    return str(val).strip()


def _fmt_num(val: float | None, suffix: str = "", digits: int = 2, prefix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{digits}f}{suffix}"


def _currency_prefix(symbol: str) -> str:
    s = symbol.upper()
    if is_indian_symbol(s):
        return "\u20b9"
    return "$"


def _fmt_large(val: float | None, prefix: str = "$") -> str:
    if val is None:
        return "N/A"
    abs_v = abs(val)
    if abs_v >= 1_000_000_000_000:
        return f"{prefix}{val / 1_000_000_000_000:.2f}T"
    if abs_v >= 1_000_000_000:
        return f"{prefix}{val / 1_000_000_000:.2f}B"
    if abs_v >= 1_000_000:
        return f"{prefix}{val / 1_000_000:.2f}M"
    return f"{prefix}{val:,.0f}"


def _series_close(df: pd.DataFrame | None) -> np.ndarray:
    if df is None or df.empty or "Close" not in df.columns:
        return np.array([])
    s = pd.to_numeric(df["Close"], errors="coerce").dropna()
    return s.to_numpy(dtype=float)


def _to_usd_billions(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"${val / 1_000_000_000:.2f}B"


def _cap_size(market_cap: float | None) -> str:
    if market_cap is None:
        return "N/A"
    if market_cap >= 200_000_000_000:
        return "Very Large Cap"
    if market_cap >= 10_000_000_000:
        return "Large Cap"
    if market_cap >= 2_000_000_000:
        return "Mid Cap"
    if market_cap >= 300_000_000:
        return "Small Cap"
    return "Micro Cap"


def _monthly_chart_data(prices: pd.DataFrame | None, market: pd.DataFrame | None) -> str:
    """Build JSON payload for the stock-vs-benchmark bar chart."""

    def _resample(df: pd.DataFrame | None) -> list[tuple[str, float]]:
        if df is None or df.empty or "Close" not in df.columns:
            return []
        d = df.copy()
        if "Date" in d.columns:
            d["Date"] = pd.to_datetime(d["Date"], errors="coerce", utc=True)
            d = d.dropna(subset=["Date"]).set_index("Date")
        d["Close"] = pd.to_numeric(d["Close"], errors="coerce")
        d = d.dropna(subset=["Close"])
        if d.empty:
            return []
        monthly = d["Close"].resample("ME").last().dropna()
        returns = monthly.pct_change().dropna()
        return [(dt.strftime("%b"), round(float(r * 100), 2)) for dt, r in returns.items()]

    stock_m = _resample(prices)
    market_m = _resample(market)
    if not stock_m:
        return ""
    labels = [m[0] for m in stock_m]
    stock_vals = [m[1] for m in stock_m]
    market_dict = {m[0]: m[1] for m in market_m} if market_m else {}
    market_vals = [market_dict.get(l, 0) for l in labels]
    return json.dumps({"labels": labels, "stock": stock_vals, "benchmark": market_vals})


def _revenue_growth_desc(rate: float | None) -> str:
    if rate is None:
        return "Revenue data not available"
    pct = rate * 100
    if pct > 15:
        return "Growing rapidly"
    if pct > 8:
        return "Grows steadily every year"
    if pct > 3:
        return "Moderate revenue growth"
    if pct > 0:
        return "Small revenue gains"
    return "Revenue is declining"


def _earnings_growth_desc(rate: float | None) -> str:
    if rate is None:
        return "Earnings data not available"
    pct = rate * 100
    if pct > 15:
        return "Strong profit growth"
    if pct > 5:
        return "Healthy profit growth"
    if pct > 0:
        return "Small profit gains"
    return "Profits are declining"


def _debt_desc(de_ratio: float | None) -> str:
    if de_ratio is None:
        return "Debt data not available"
    if de_ratio < 30:
        return "Very low debt levels"
    if de_ratio < 60:
        return "Debt is manageable and under control"
    if de_ratio < 100:
        return "Moderate debt levels"
    return "High debt levels - needs monitoring"


def _cashflow_desc(ocf: float | None) -> str:
    if ocf is None:
        return "Cash flow data not available"
    if ocf > 0:
        return "Generates strong cash flow"
    return "Cash flow needs improvement"


def _health_status(rev_growth: float | None, de_ratio: float | None, ocf: float | None) -> str:
    score = 0
    if rev_growth is not None and rev_growth > 0.03:
        score += 1
    if de_ratio is not None and de_ratio < 80:
        score += 1
    if ocf is not None and ocf > 0:
        score += 1
    if score >= 3:
        return "STRONG"
    if score >= 2:
        return "STABLE"
    if score >= 1:
        return "MIXED"
    return "WEAK"


def _quick_answers(
    row: pd.Series,
    prices: pd.DataFrame | None,
    market: pd.DataFrame | None,
) -> str:
    """Compute the four Quick-Answer lines for the wireframe."""
    lines: list[str] = ["QUICK_ANSWERS"]

    rev_g = _f(row, "revenueGrowth")
    if rev_g is not None and rev_g > 0.10:
        lines.append("Good Business: Yes | Strong revenue growth indicates a solid business model")
    elif rev_g is not None and rev_g > 0.03:
        lines.append("Good Business: Mixed | Moderate growth with some areas of concern")
    else:
        lines.append("Good Business: No | Weak growth signals a struggling business")

    de = _f(row, "debtToEquity")
    ocf = _f(row, "operatingCashflow")
    if de is not None and de < 100 and ocf is not None and ocf > 0:
        lines.append(
            "Financially Healthy: Yes | Low debt and strong cash generation show solid financial footing"
        )
    elif de is not None and de < 200:
        lines.append("Financially Healthy: Mixed | Moderate debt levels with acceptable cash flow")
    else:
        lines.append("Financially Healthy: No | High debt or weak cash generation are concerning")

    sp = _series_close(prices)
    if len(sp) > 10:
        sr = np.diff(sp) / sp[:-1]
        vol = float(np.std(sr, ddof=1) * np.sqrt(252)) * 100
        if vol < 15:
            lines.append(
                f"Stock Risky: Low | Low volatility ({vol:.0f}% annualized) - relatively stable"
            )
        elif vol < 30:
            lines.append(
                "Stock Risky: Moderate | Moderate volatility - average risk for stock investments"
            )
        else:
            lines.append(
                f"Stock Risky: High | High volatility ({vol:.0f}% annualized) - significant price swings"
            )
    else:
        lines.append("Stock Risky: Unknown | Insufficient data to assess risk")

    pe = _f(row, "trailingPE")
    if pe is not None:
        if pe > 25:
            lines.append(
                "Expensive: Expensive | Trading above historical averages - may need strong growth to justify price"
            )
        elif pe > 15:
            lines.append("Expensive: Fair | Trading near fair value based on earnings")
        else:
            lines.append(
                "Expensive: Cheap | Trading below average valuations - potential opportunity"
            )
    else:
        lines.append("Expensive: Unknown | Insufficient data to assess valuation")

    return "\n".join(lines)


def _valuation_insight(row: pd.Series) -> str:
    pe = _f(row, "trailingPE")
    pb = _f(row, "priceToBook")
    peg = _f(row, "pegRatio")
    growth = _f(row, "earningsGrowth")
    if pe is None or pe <= 0:
        return (
            "No meaningful P/E (losses or missing earnings); "
            "judge value on sales and book multiples instead."
        )
    if pe > 25 or (pb is not None and pb > 3):
        if peg is not None and 0 < peg < 1 and growth is not None and growth > 0:
            return (
                f"Multiples look rich (P/E {pe:.1f}x), but a PEG of {peg:.2f}x "
                "suggests earnings growth may justify them."
            )
        return f"Multiples look rich (P/E {pe:.1f}x); earnings growth must stay strong to justify them."
    if pe > 15:
        return f"Valuation looks near fair value (P/E {pe:.1f}x)."
    return f"Multiples look low (P/E {pe:.1f}x); check whether weak growth or risk explains the discount."


def _performance_insight(
    total: float, market_total: float | None, vol: float, mdd: float, sharpe: float
) -> str:
    if market_total is None:
        head = "No market comparison is available"
    else:
        gap = (total - market_total) * 100
        word = "Outperformed" if gap >= 0 else "Underperformed"
        head = f"{word} the market by {abs(gap):.1f} percentage points"
    if vol > 0.35 or mdd < -0.30:
        tail = f"with large swings ({vol * 100:.1f}% volatility, {mdd * 100:.1f}% max drawdown)"
    elif sharpe < 0.5:
        tail = f"while risk-adjusted returns are weak (Sharpe {sharpe:.2f})"
    else:
        tail = f"with solid risk-adjusted returns (Sharpe {sharpe:.2f})"
    return f"{head}, {tail}."


def _health_insight(ocf: float | None, de_ratio: float | None) -> str:
    if ocf is None:
        cash = "Operating cash flow data is unavailable"
    elif ocf < 0:
        cash = "Operating cash flow is negative, so the business is consuming cash"
    else:
        cash = f"Operating cash flow is positive ({_fmt_large(ocf)})"
    if de_ratio is None:
        debt = "debt-to-equity is unavailable or not meaningful"
    elif de_ratio > 100:
        debt = f"leverage is high (debt-to-equity {de_ratio:.0f}%)"
    elif de_ratio > 50:
        debt = f"leverage is moderate (debt-to-equity {de_ratio:.0f}%)"
    else:
        debt = f"leverage is low (debt-to-equity {de_ratio:.0f}%)"
    return f"{cash}; {debt}."


def _sentiment_insight(buy_pct: float, sell_pct: float, total: int) -> str:
    if total == 0:
        return "No analyst ratings are available."
    if buy_pct >= 70:
        return (
            f"Analysts are strongly bullish ({buy_pct:.0f}% Buy); "
            "check whether price action and insider activity agree."
        )
    if sell_pct >= 30:
        return f"A sizable share of analysts rate it Sell ({sell_pct:.0f}%); sentiment is divided."
    if buy_pct >= 50:
        return f"Analysts lean positive ({buy_pct:.0f}% Buy), with a large Hold contingent."
    return f"Analyst views are cautious ({buy_pct:.0f}% Buy)."


def _valuation_verdict(row: pd.Series) -> str:
    pe = _f(row, "trailingPE")
    pb = _f(row, "priceToBook")
    if pe is None:
        return "Valuation Verdict: Unknown | Insufficient data"
    if pe > 25 or (pb is not None and pb > 3):
        return "Valuation Verdict: Yes | Trading above fair value"
    if pe > 15:
        return "Valuation Verdict: Fair | Trading near fair value"
    return "Valuation Verdict: No | Trading below fair value"


def _valuation_facts(row: pd.Series, cash: pd.DataFrame | None, symbol: str) -> str:
    peg = _f(row, "pegRatio")
    ev_ebitda = _f(row, "enterpriseToEbitda")
    lines = [
        "FINANCIAL SNAPSHOT",
        f"P/E Ratio: {_fmt_num(_f(row, 'trailingPE'), 'x')}",
        f"Forward P/E: {_fmt_num(_f(row, 'forwardPE'), 'x')}",
        f"P/B Ratio: {_fmt_num(_f(row, 'priceToBook'), 'x')}",
        f"P/S Ratio: {_fmt_num(_f(row, 'priceToSalesTrailing12Months'), 'x')}",
        f"PEG Ratio: {_fmt_num(peg, 'x') if peg else 'N/A'}",
        f"EV/EBITDA: {_fmt_num(ev_ebitda, 'x') if ev_ebitda else 'N/A'}",
        f"ROE (%): {_fmt_num(_f(row, 'returnOnEquity', 0) * 100 if _f(row, 'returnOnEquity') is not None else None, '%')}",  # type: ignore[operator]
        f"ROA (%): {_fmt_num(_f(row, 'returnOnAssets', 0) * 100 if _f(row, 'returnOnAssets') is not None else None, '%')}",  # type: ignore[operator]
        f"Gross Margin (%): {_fmt_num(_f(row, 'grossMargins', 0) * 100 if _f(row, 'grossMargins') is not None else None, '%')}",  # type: ignore[operator]
        "",
        _valuation_verdict(row),
        "",
        "INSIGHT",
        f"Insight: {_valuation_insight(row)}",
    ]
    if cash is not None and "Free Cash Flow" in cash.iloc[:, 0].values:
        try:
            idx = cash.iloc[:, 0] == "Free Cash Flow"
            val = pd.to_numeric(cash.loc[idx].iloc[0, 1], errors="coerce")
            if not pd.isna(val):
                lines.insert(10, f"Free Cash Flow (USD B): {_to_usd_billions(float(val))}")
        except Exception:
            pass
    return "\n".join(lines)


def _close_by_date(df: pd.DataFrame | None) -> pd.Series:
    """Close prices indexed by trading date (YYYY-MM-DD)."""
    if df is None or df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    closes = pd.to_numeric(df["Close"], errors="coerce").to_numpy()
    dates = df[date_col].astype(str).str[:10].to_numpy()
    return pd.Series(closes, index=dates).dropna()


def _beta_by_date(prices: pd.DataFrame | None, market: pd.DataFrame | None) -> float | None:
    """Beta of daily returns, pairing stock and market by date, not by row position.

    Stocks and their index can have different trading calendars (e.g. Indian holidays),
    so position-based pairing silently misaligns the two series.
    """
    stock = _close_by_date(prices).pct_change(fill_method=None)
    index = _close_by_date(market).pct_change(fill_method=None)
    joined = pd.concat([stock, index], axis=1, join="inner").dropna()
    if len(joined) < 3:
        return None
    market_var = joined.iloc[:, 1].var()
    if not market_var:
        return None
    return float(joined.iloc[:, 0].cov(joined.iloc[:, 1]) / market_var)


def _performance_facts(prices: pd.DataFrame | None, market: pd.DataFrame | None) -> str:
    sp = _series_close(prices)
    mp = _series_close(market)
    if len(sp) < 3:
        return "PERFORMANCE & RISK\nInsight: Insufficient price history to compute reliable performance metrics."

    total = (sp[-1] - sp[0]) / sp[0]
    annualized = (1 + total) ** (252 / len(sp)) - 1
    sr = np.diff(sp) / sp[:-1]
    vol = float(np.std(sr, ddof=1) * np.sqrt(252)) if len(sr) > 1 else 0.0
    peak = np.maximum.accumulate(sp)
    mdd = float(np.min((sp - peak) / peak))

    risk_free = 0.05
    sharpe = round((annualized - risk_free) / vol, 2) if vol > 0 else 0.0

    market_total = None
    if len(mp) >= 3:
        market_total = (mp[-1] - mp[0]) / mp[0]

    beta = _beta_by_date(prices, market)

    vol_pct = vol * 100
    if vol_pct < 15:
        vol_label = "Low"
    elif vol_pct < 30:
        vol_label = "Moderate"
    else:
        vol_label = "High"

    perf_badge = "IN LINE"
    if market_total is not None:
        if total > market_total + 0.02:
            perf_badge = "OUTPERFORMING"
        elif total < market_total - 0.02:
            perf_badge = "UNDERPERFORMING"

    chart_json = _monthly_chart_data(prices, market)

    lines = [
        "PERFORMANCE & RISK",
        f"Total Return (%): {_fmt_num(total * 100, '%')}",
        f"Annualized Return (%): {_fmt_num(annualized * 100, '%')}",
        f"Volatility (%): {_fmt_num(vol_pct, '%')}",
        f"Volatility Label: {vol_label}",
        f"Max Drawdown (%): {_fmt_num(mdd * 100, '%')}",
        f"Beta (vs market): {_fmt_num(beta, 'x')}",
        f"Sharpe Ratio: {sharpe}",
        "Risk Metric Basis: Beta above is computed from 1 year of daily prices vs the "
        "market index; Yahoo's company_info beta uses 5 years of monthly data, so the "
        "two differ by method, not error. Use the Beta above.",
        f"Market Total Return (%): {_fmt_num(market_total * 100, '%') if market_total is not None else 'N/A'}",
        f"Performance Badge: {perf_badge}",
    ]
    if chart_json:
        lines.append(f"CHART_DATA: {chart_json}")
    lines.extend(
        [
            "",
            "INSIGHT",
            "Insight: " + _performance_insight(total, market_total, vol, mdd, sharpe),
        ]
    )
    return "\n".join(lines)


def _debt_to_equity_by_year(balance: pd.DataFrame | None) -> list[str]:
    """Debt/Equity for the two latest fiscal years, both from the balance sheet."""
    if balance is None or balance.empty or balance.shape[1] < 3:
        return []
    labels = balance.iloc[:, 0].astype(str).str.strip()
    debt = balance[labels == "Total Debt"]
    equity = balance[labels == "Stockholders Equity"]
    if debt.empty or equity.empty:
        return []
    lines = []
    for col in balance.columns[1:3]:
        d = pd.to_numeric(debt.iloc[0][col], errors="coerce")
        e = pd.to_numeric(equity.iloc[0][col], errors="coerce")
        if pd.notna(d) and pd.notna(e) and e > 0:
            lines.append(f"Debt/Equity FY{str(col)[:4]} (balance sheet): {d / e:.2f}x")
    if lines:
        lines.append(
            "Debt/Equity Basis: the plain 'Debt/Equity' value is Yahoo's latest-quarter "
            "figure in percent (e.g. 78 means 0.78x). Compare fiscal years only with each other."
        )
    return lines


def _financial_health_facts(
    row: pd.Series,
    income: pd.DataFrame | None,
    cash: pd.DataFrame | None,
    balance: pd.DataFrame | None = None,
) -> str:
    rev_growth = _f(row, "revenueGrowth")
    earn_growth = _f(row, "earningsGrowth")
    de_ratio = _f(row, "debtToEquity")
    ocf = _f(row, "operatingCashflow")

    status = _health_status(rev_growth, de_ratio, ocf)

    lines = [
        "FINANCIAL HEALTH",
        f"Health Status: {status}",
    ]

    lines.append("HEALTH_DESCRIPTIONS")
    rg_pct = (
        _fmt_num(rev_growth * 100, "% YoY (latest quarter)") if rev_growth is not None else "N/A"
    )
    eg_pct = (
        _fmt_num(earn_growth * 100, "% YoY (latest quarter)") if earn_growth is not None else "N/A"
    )
    de_display = _fmt_num(de_ratio, "% ratio") if de_ratio is not None else "N/A"
    ocf_display = _fmt_large(ocf) if ocf is not None else "N/A"

    lines.extend(
        [
            f"Revenue Growth Desc: {_revenue_growth_desc(rev_growth)} | {rg_pct}",
            f"Profit Growth Desc: {_earnings_growth_desc(earn_growth)} | {eg_pct}",
            f"Debt Desc: {_debt_desc(de_ratio)} | {de_display}",
            f"Cash Desc: {_cashflow_desc(ocf)} | {ocf_display}",
        ]
    )

    lines.append("")
    lines.append("FINANCIAL METRICS")
    lines.append(
        "Growth Basis: Revenue/Earnings Growth Rate = latest quarter vs same quarter "
        "a year earlier; Revenue YoY = full fiscal year vs prior fiscal year"
    )
    lines.extend(_debt_to_equity_by_year(balance))
    if rev_growth is not None:
        lines.append(f"Revenue Growth Rate: {_fmt_num(rev_growth * 100, '%')}")
    if earn_growth is not None:
        lines.append(f"Earnings Growth Rate: {_fmt_num(earn_growth * 100, '%')}")
    lines.extend(
        [
            f"Debt/Equity: {_fmt_num(de_ratio)}",
            f"Current Ratio: {_fmt_num(_f(row, 'currentRatio'))}",
            f"Operating Cash Flow (USD B): {_to_usd_billions(ocf)}",
        ]
    )

    if income is not None and not income.empty and "Total Revenue" in income.iloc[:, 0].values:
        try:
            revenue_row = income[income.iloc[:, 0] == "Total Revenue"].iloc[0, 1:4]
            revenue_vals = pd.to_numeric(revenue_row, errors="coerce").dropna().to_numpy()
            if len(revenue_vals) >= 2:
                yoy = _yoy_change(revenue_vals[0], revenue_vals[1])
                lines.append(f"Revenue YoY (%): {_fmt_num(float(yoy) * 100, '%')}")
        except Exception:
            pass

    if cash is not None and not cash.empty and "Free Cash Flow" in cash.iloc[:, 0].values:
        try:
            fcf_row = cash[cash.iloc[:, 0] == "Free Cash Flow"].iloc[0, 1:3]
            fcf_vals = pd.to_numeric(fcf_row, errors="coerce").dropna().to_numpy()
            if len(fcf_vals) >= 2 and fcf_vals[1] != 0:
                fcf_yoy = _yoy_change(fcf_vals[0], fcf_vals[1])
                lines.append(f"Free Cash Flow YoY (%): {_fmt_num(float(fcf_yoy) * 100, '%')}")
        except Exception:
            pass

    lines.extend(["", "INSIGHT", f"Insight: {_health_insight(ocf, de_ratio)}"])
    return "\n".join(lines)


def _sentiment_facts(
    recs: pd.DataFrame | None, holders: pd.DataFrame | None, news: pd.DataFrame | None
) -> str:
    lines = ["SENTIMENT & ANALYST SUMMARY"]
    insight = "No analyst ratings are available."
    if recs is not None and not recs.empty:
        latest = recs.iloc[0]
        sb = int(pd.to_numeric(latest.get("strongBuy", 0), errors="coerce") or 0)
        b = int(pd.to_numeric(latest.get("buy", 0), errors="coerce") or 0)
        h = int(pd.to_numeric(latest.get("hold", 0), errors="coerce") or 0)
        s = int(pd.to_numeric(latest.get("sell", 0), errors="coerce") or 0)
        ss = int(pd.to_numeric(latest.get("strongSell", 0), errors="coerce") or 0)
        buy_count = sb + b
        sell_count = s + ss
        total = sb + b + h + s + ss
        # Hold is derived from the other two so the three always sum to exactly 100%.
        buy_pct = round(100 * buy_count / total, 1) if total else 0.0
        sell_pct = round(100 * sell_count / total, 1) if total else 0.0
        hold_pct = round(100 - buy_pct - sell_pct, 1) if total else 0.0
        insight = _sentiment_insight(buy_pct, sell_pct, total)
        signal = "Neutral"
        if buy_count > sell_count + h:
            signal = "Positive"
        elif sell_count > buy_count + h:
            signal = "Negative"
        lines.extend(
            [
                f"Analyst Consensus: Buy {buy_count} | Hold {h} | Sell {sell_count} ({total} analysts)",
                f"Analyst Consensus (%): Buy {buy_pct:.1f}% | Hold {hold_pct:.1f}% | Sell {sell_pct:.1f}%",
                f"Sentiment Signal: {signal}",
            ]
        )

    lines.extend(["", "OWNERSHIP"])
    if holders is not None and not holders.empty and "Holder" in holders.columns:
        top = holders.head(3)
        holder_names = ", ".join(str(x) for x in top["Holder"].tolist())
        lines.append(f"Top Holders: {holder_names}")

    lines.extend(
        [
            "",
            "INSIGHT",
            f"Insight: {insight}",
            "",
            "RELATED NEWS",
        ]
    )
    if news is not None and not news.empty and "url" in news.columns:
        lines.append("News Status: Latest cached news")
        news_rows = news.head(3).fillna("")
        for _, row in news_rows.iterrows():
            title = str(row.get("title", "")).strip()
            publisher = str(row.get("publisher", "")).strip().strip("{}").replace("'", "")
            url = str(row.get("url", "")).strip()
            if title and url:
                lines.append(f"News: {title} | {publisher or 'source'} | {url}")
    else:
        lines.append("News Status: No recent news available")
    return "\n".join(lines)


def _company_basics_facts(
    row: pd.Series,
    symbol: str,
    recs: pd.DataFrame | None,
    holders: pd.DataFrame | None,
    prices: pd.DataFrame | None,
    market: pd.DataFrame | None,
) -> str:
    name = _s(row, "longName") or _s(row, "shortName") or symbol
    mcap = _f(row, "marketCap")
    cur = _currency_prefix(symbol)
    lines = [
        "COMPANY BASICS:",
        f"Company Name: {name}",
        f"Ticker: {symbol}",
        f"Sector: {_s(row, 'sector')}",
        f"Segment: {_s(row, 'industry')}",
        f"Price: {_fmt_num(_f(row, 'currentPrice'), prefix=cur)}",
        f"Market Cap: {_fmt_large(mcap, prefix=cur)}",
        f"Cap Size: {_cap_size(mcap)}",
    ]

    peers: list[str] = []
    if holders is not None and not holders.empty and "Holder" in holders.columns:
        peers = [str(x) for x in holders["Holder"].dropna().head(5).tolist()]
    if not peers and recs is not None and not recs.empty:
        peers = ["Peer data not available in local files"]
    lines.append(f"Peers: {', '.join(peers) if peers else 'N/A'}")

    sp = _series_close(prices)
    mp = _series_close(market)
    stock_change = "N/A"
    market_change = "N/A"
    if len(sp) >= 2:
        stock_change = f"{((sp[-1] - sp[-2]) / sp[-2]) * 100:.2f}%"
    if len(mp) >= 2:
        market_change = f"{((mp[-1] - mp[-2]) / mp[-2]) * 100:.2f}%"

    lines.extend(
        [
            "",
            _quick_answers(row, prices, market),
            "",
            "MARKET PULSE",
            f"Mini Screener: Valuation=Watch | Momentum=Positive | Risk=Moderate | Sentiment=Constructive",
            f"Ticker Tape: {symbol} {_fmt_num(_f(row, 'currentPrice'), prefix=cur)} ({stock_change}) | S&P 500 ({market_change}) [cached]",
        ]
    )
    return "\n".join(lines)
