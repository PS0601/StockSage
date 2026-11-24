# Grounding eval

Run on 2026-11-23 22:13 · model `deepseek/deepseek-chat` · 5 tickers × 2 runs = 10 crew runs

| Metric | Result |
|---|---|
| **Unexplained numbers** (no source found: hallucination candidates) | **77/3042 (3%)**, lower is better |
| Numbers with a source | 2965/3042 (97%) |
| Sentiment agent: numbers with a source (web search results can't be checked) | 681/783 (87%) |
| Blocked ratios given a value anyway | 0 (lower is better) |
| Contradictions with computed badge / valuation / health | 0 (lower is better) |
| Outputs that parsed into the task schema | 60/60 (100%) |
| Same verdict on every run | 5/5 tickers |
| Crew run time | median 60s · max 70s |

## Where the numbers came from (all agents except sentiment)

| Source | Numbers | Share |
|---|---|---|
| Computed facts (facts.py) | 1489 | 49% |
| Raw data the agent read (CSVs) | 1220 | 40% |
| Benchmark written in the prompt | 19 | 1% |
| Derived: arithmetic on numbers in the same sentence | 160 | 5% |
| **Unexplained** | 77 | 3% |

## Per ticker

| Ticker | Data as of | Verdicts (confidence) | Numbers with a source | Blocked | Contradictions |
|---|---|---|---|---|---|
| AAPL | 2026-10-25 | HOLD (Medium), HOLD (Medium) | 583/605 | 0 | 0 |
| JPM | 2026-10-08 | HOLD (Medium), HOLD (Medium) | 526/528 | 0 | 0 |
| KO | 2026-10-08 | HOLD (High), HOLD (Medium) | 633/639 | 0 | 0 |
| TSLA | 2026-10-08 | SELL (Medium), SELL (High) | 682/706 | 0 | 0 |
| RELIANCE.NS | 2026-10-08 | HOLD (Medium), HOLD (Low) | 541/564 | 0 | 0 |

## Unexplained numbers by agent task

| Task | Unexplained / numbers |
|---|---|
| analyze_valuation_ratios | 3/578 |
| analyze_price_performance | 13/519 |
| analyze_financial_health | 20/965 |
| analyze_market_sentiment | 102/783 |
| review_analysis | 13/689 |
| generate_investment_report | 28/291 |

## Numbers taken from benchmarks written in the prompt

These are static values in `src/crew/config/tasks.yaml`, not live data: `$100`, `0.04%`, `100`, `4.00%`, `72%`, `₹100`

## Unexplained numbers to read

- AAPL · analyze_price_performance: `$86.20` in: a $100 peak position bottomed near $86.20, a shallow downside relative to the +32.80% total return earned.
- AAPL · analyze_financial_health: `19.5%` in: Free cash flow declined 9.23% YoY to $98.77B (FY2025) from $108.81B (FY2024) even as net income rose 19.5% — cash generation lagging earnings
- AAPL · review_analysis: `63.6%` in: No material mismatch: sentiment agent's 6/18/14/3/3 = 44 analysts (54.5% Buy / 31.9% Hold / 13.6% Sell) and -3m 6/22/14/2/2 (63.6%/31.8%/4.5%) match recommendations.csv exactly.
- AAPL · review_analysis: `9.8%` in: Valuation's PEG of 2.79x is paired with 28.7% earnings growth (company_info earningsGrowth, latest quarter) while the same agent notes only ~9.8% forward EPS growth — the PEG is
- AAPL · review_analysis: `9.1` in: Sentiment agent's 'Positive' signal coexists with a ~9.1pp Buy-share decline and one-sided insider selling;
- AAPL · generate_investment_report: `20.6` in: Risk-adjusted performance is strong: AAPL beat the S&P 500 by ~20.6 percentage points with a Sharpe above 1.0 and a contained sub-15% max drawdown — holders have been well compensated per unit of risk (performance analys
- AAPL · generate_investment_report: `19.5%` in: Cash generation is lagging earnings: FCF fell 9.23% YoY despite 19.5% net income growth and cash conversion slipped to ~1.00x, with working capital turning negative and a tight liquidity position (fundamental analyst)
- AAPL · generate_investment_report: `9.8%` in: Forward EPS revisions — forward P/E implies only ~9.8% growth;
- AAPL · analyze_financial_health: `19.50%` in: AAPL's business is getting stronger: FY2025 revenue rose 6.43% to $416.16B (from $391.04B), net income jumped 19.50% to $112.01B, and all three fiscal-year margins expanded (gross 46.91%, operating 31.97%, net 26.92%), w
- AAPL · review_analysis: `111.482` in: OCF/NI = 111.482/112.010 = 1.00x correct.
- AAPL · review_analysis: `112.010` in: OCF/NI = 111.482/112.010 = 1.00x correct.
- AAPL · generate_investment_report: `19.50%` in: All three margins expanded in FY2025 (gross, operating and net), with net income growing 19.50% on only 6.43% revenue growth — earnings are outgrowing sales and sector-leading profitability is what partly earns the premi
- AAPL · generate_investment_report: `$160M` in: Corporate insiders are monetizing at record highs with zero open-market buys — roughly $160M+ of disclosed sales in six months including the CEO and a 250,000-share director sale — a positioning mismatch against the stoc
- AAPL · generate_investment_report: `250,000` in: Corporate insiders are monetizing at record highs with zero open-market buys — roughly $160M+ of disclosed sales in six months including the CEO and a 250,000-share director sale — a positioning mismatch against the stoc
- AAPL · generate_investment_report: `34.6%` in: Cash generation is lagging earnings: free cash flow fell 9.23% YoY on a 34.6% CapEx increase, OCF/NI dropped to 1.00x, and the current ratio of 1.00 with negative working capital keeps liquidity tight (fundamental analys
- AAPL · generate_investment_report: `89%` in: Short-horizon traders sensitive to headlines — 24.09% annualized volatility is ~89% above the market's, and insider selling into all-time highs is a visible overhang
- JPM · analyze_financial_health: `10.1%` in: Cash and cash equivalents fell from $469.32B (FY2024) to $343.34B (FY2025), -26.8%, while total debt rose 10.1% to $499.98B and D/E increased from 1.32x to 1.38x
- JPM · review_analysis: `-1.62534` in: No mismatch: financial health's 46.90% earnings growth (earningsGrowth 0.469), 34.92% TTM net margin (profitMargins 0.34921), 30.40% TTM revenue growth (revenueGrowth 0.304), -$162.53B TTM OCF (operatingCashflow -1.62534
- KO · analyze_financial_health: `1.08x` in: Cash conversion is weak — FY2025 operating cash flow of $7.41B is only 0.56x net income of $13.11B, versus 0.64x in FY2024 and 1.08x in FY2023, driven by a -$7.21B change in working capital
- KO · review_analysis: `$166M` in: Sentiment's 'Positive' signal rests on a stale four-month analyst consensus while insiders are net sellers (~$166M, zero buys) — the agent correctly flags the disconnect, but the headline signal label understates the ins
- KO · generate_investment_report: `$166M` in: KO is a high-quality but fully-priced defensive franchise: the valuation analyst flags it as expensive on every metric (26.36x trailing P/E, 23.49x EV/EBITDA and a 3.90x PEG that already discounts growth), while the fund
- KO · generate_investment_report: `$47.5M` in: Insiders are one-directional sellers — 30+ open-market sales and zero open-market buys in six months, led by the Chairman/CEO's ~$47.5M July sale, which is a positioning mismatch against bullish analyst consensus even if
- TSLA · analyze_valuation_ratios: `40x` in: Trailing P/E: 347.22x - 347.22x vs S&P 500 average ~22x — a ~1,478% premium, and vs a typical auto-manufacturer sector median of roughly 8-12x it is a ~30-40x multiple of the sector;
- TSLA · analyze_price_performance: `29.3` in: TSLA returned -13.90% over the trailing 1-year window (annualized -13.95%) versus +15.30% for the market index — an underperformance of roughly 29.3 percentage points — while carrying 45.44% annualized volatility (3.5x t
- TSLA · analyze_price_performance: `29.2` in: 1Y Total Return (TSLA vs Market): -13.90% - TSLA -13.90% vs market index +15.30% — underperformed by 29.2 percentage points;

Unexplained does not always mean wrong (e.g. a number from general knowledge, or arithmetic across sentences). Read the examples before drawing conclusions.
