# Grounding eval

Run on 2026-11-23 21:45 · model `deepseek/deepseek-chat` · 2 tickers × 2 runs = 4 crew runs

| Metric | Result |
|---|---|
| **Unexplained numbers** (no source found: hallucination candidates) | **56/1332 (4%)**, lower is better |
| Numbers with a source | 1276/1332 (96%) |
| Sentiment agent: numbers with a source (web search results can't be checked) | 236/278 (85%) |
| Blocked ratios given a value anyway | 0 (lower is better) |
| Contradictions with computed badge / valuation / health | 0 (lower is better) |
| Outputs that parsed into the task schema | 24/24 (100%) |
| Same verdict on every run | 2/2 tickers |
| Crew run time | median 64s · max 68s |

## Where the numbers came from (all agents except sentiment)

| Source | Numbers | Share |
|---|---|---|
| Computed facts (facts.py) | 599 | 45% |
| Raw data the agent read (CSVs) | 534 | 40% |
| Benchmark written in the prompt | 9 | 1% |
| Derived: arithmetic on numbers in the same sentence | 78 | 6% |
| **Unexplained** | 56 | 4% |

## Per ticker

| Ticker | Data as of | Verdicts (confidence) | Numbers with a source | Blocked | Contradictions |
|---|---|---|---|---|---|
| TSLA | 2026-10-08 | SELL (Medium), SELL (High) | 666/700 | 0 | 0 |
| RELIANCE.NS | 2026-10-08 | HOLD (Medium), HOLD (Medium) | 610/632 | 0 | 0 |

## Unexplained numbers by agent task

| Task | Unexplained / numbers |
|---|---|
| analyze_valuation_ratios | 4/233 |
| analyze_price_performance | 7/207 |
| analyze_financial_health | 9/405 |
| analyze_market_sentiment | 42/278 |
| review_analysis | 19/342 |
| generate_investment_report | 17/145 |

## Numbers taken from benchmarks written in the prompt

These are static values in `src/crew/config/tasks.yaml`, not live data: `0.90`, `100`, `9x`

## Unexplained numbers to read

- TSLA · analyze_valuation_ratios: `2,800` in: vs a typical auto-manufacturer sector median of roughly 8-12x it is a ~2,800-4,200% premium.
- TSLA · analyze_valuation_ratios: `4,200%` in: vs a typical auto-manufacturer sector median of roughly 8-12x it is a ~2,800-4,200% premium.
- TSLA · analyze_price_performance: `29.2` in: TSLA returned -13.90% over the trailing year versus +15.30% for the S&P 500 — an underperformance of 29.2 percentage points — with 45.44% annualized volatility, a beta of 2.18x, a -39.10% max drawdown and a Sharpe ratio
- TSLA · analyze_financial_health: `283` in: Operating Margin (FY2025 vs FY2024): 5.11% vs 7.94% (FY2025 vs FY2024) - Operating margin compressed 283 bps YoY (operating income $4.849B on $94.827B revenue vs $7.76B on $97.69B);
- TSLA · analyze_financial_health: `41.2%` in: gross margin was roughly flat at 18.03% vs 17.86% (FY2025 vs FY2024), so the compression came from operating expense growth ($9.69B → $12.245B, +26.4%, driven by R&D up 41.2% to $6.411B).
- TSLA · analyze_financial_health: `26.4%` in: deteriorating — operating margin compressed to 5.11% (FY2025) from 7.94% (FY2024) and net margin to 4.00% from 7.30%, as operating expenses rose 26.4% to $12.245B (R&D +41.2% to $6.411B)
- TSLA · review_analysis: `51.1%` in: VALUATION vs SENTIMENT TENSION (valid, not a contradiction): Valuation says 'expensive on every valid multiple' (347.22x P/E, 135.22x EV/EBITDA) while sentiment is 'Negative' with a bearish-drifting consensus (43.2% Buy,
- TSLA · review_analysis: `100.6M` in: Sentiment agent's insider-sale total (~100.6M) is a sum of the listed open-market sales;
- TSLA · review_analysis: `0.94` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · review_analysis: `9.99` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · review_analysis: `9.27` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · review_analysis: `10.69` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · review_analysis: `26.72` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · review_analysis: `61.9M` in: the individual line items (Taneja 0.94+1.05+1.35+0.90, Wilson-Thompson 9.99+9.27+10.69, Murdoch 26.72) sum to ~61.9M, so the ~100.6M headline appears to include additional sales not itemized — the aggregate is not fully
- TSLA · generate_investment_report: `15.8x` in: Valuation leaves no room for error on any valid multiple — trailing P/E ~15.8x the S&P 500 and EV/EBITDA ~9x the 'expensive' threshold, while ROE and operating margin sit far below sector norms, so price capitalizes AI/r
- TSLA · generate_investment_report: `-46.8%` in: Profitability is contracting, not stabilizing: net income fell -46.8% YoY and is down -74.7% from FY2023, with operating margin compressing from 7.94% to 5.11% as R&D rose 41.2% — earnings are still shrinking on a TTM ba
- TSLA · generate_investment_report: `-74.7%` in: Profitability is contracting, not stabilizing: net income fell -46.8% YoY and is down -74.7% from FY2023, with operating margin compressing from 7.94% to 5.11% as R&D rose 41.2% — earnings are still shrinking on a TTM ba
- TSLA · generate_investment_report: `41.2%` in: Profitability is contracting, not stabilizing: net income fell -46.8% YoY and is down -74.7% from FY2023, with operating margin compressing from 7.94% to 5.11% as R&D rose 41.2% — earnings are still shrinking on a TTM ba
- TSLA · generate_investment_report: `51.1%` in: Sentiment is deteriorating on the sell side and among insiders — Buy share fell from 51.1% to 43.2% over three months with a plurality of analysts now on Hold, and ~$100M+ of open-market insider sales occurred against ze
- TSLA · analyze_valuation_ratios: `40x` in: vs auto-manufacturer sector norms of roughly 8-12x it is ~30-40x the sector.
- TSLA · analyze_price_performance: `21.8%` in: a 10% market move implies roughly a 21.8% TSLA move.
- TSLA · generate_investment_report: `3.9x` in: Free cash flow rose 73.7% YoY to $6.22B, with operating cash flow covering net income nearly 3.9x — healthy cash conversion underpins the capital-spending plan even as reported earnings fall (fundamental analyst)
- TSLA · generate_investment_report: `98.6%` in: Valuation is extreme on every valid metric: the premium to the market and to auto-sector norms is measured in multiples of the sector's entire multiple, and even the ~98.6% EPS growth implied by the forward/trailing P/E
- RELIANCE.NS · analyze_financial_health: `36.5%` in: cash up 36.5% YoY.
- RELIANCE.NS · analyze_financial_health: `2.38x` in: improving — free cash flow rose 78.64% YoY to ₹691.97B and OCF of ₹1.921T covers net income 2.38x, confirming real cash generation

Unexplained does not always mean wrong (e.g. a number from general knowledge, or arithmetic across sentences). Read the examples before drawing conclusions.
