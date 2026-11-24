# Grounding eval

Run on 2026-11-23 21:40 · model `deepseek/deepseek-chat` · 2 tickers × 2 runs = 4 crew runs

| Metric | Result |
|---|---|
| **Unexplained numbers** (no source found: hallucination candidates) | **70/1390 (5%)**, lower is better |
| Numbers with a source | 1320/1390 (95%) |
| Sentiment agent: numbers with a source (web search results can't be checked) | 274/312 (88%) |
| Blocked ratios given a value anyway | 2 (lower is better) |
| Contradictions with computed badge / valuation / health | 1 (lower is better) |
| Outputs that parsed into the task schema | 24/24 (100%) |
| Same verdict on every run | 1/2 tickers |
| Crew run time | median 67s · max 69s |

## Where the numbers came from (all agents except sentiment)

| Source | Numbers | Share |
|---|---|---|
| Computed facts (facts.py) | 635 | 46% |
| Raw data the agent read (CSVs) | 518 | 37% |
| Benchmark written in the prompt | 8 | 1% |
| Derived: arithmetic on numbers in the same sentence | 89 | 6% |
| **Unexplained** | 70 | 5% |

## Per ticker

| Ticker | Data as of | Verdicts (confidence) | Numbers with a source | Blocked | Contradictions |
|---|---|---|---|---|---|
| TSLA | 2026-10-08 | SELL (Medium), HOLD (Medium) | 688/728 | 2 | 0 |
| RELIANCE.NS | 2026-10-08 | HOLD (Medium), HOLD (Medium) | 632/662 | 0 | 1 |

## Unexplained numbers by agent task

| Task | Unexplained / numbers |
|---|---|
| analyze_valuation_ratios | 13/276 |
| analyze_price_performance | 13/223 |
| analyze_financial_health | 14/434 |
| analyze_market_sentiment | 38/312 |
| review_analysis | 8/248 |
| generate_investment_report | 22/209 |

## Numbers taken from benchmarks written in the prompt

These are static values in `src/crew/config/tasks.yaml`, not live data: `100`, `35x`, `800%`, `9x`

## Unexplained numbers to read

- TSLA · analyze_valuation_ratios: `2,900` in: vs the Auto Manufacturers industry norm of roughly 8-12x it is a ~2,900-4,200% premium.
- TSLA · analyze_valuation_ratios: `4,200%` in: vs the Auto Manufacturers industry norm of roughly 8-12x it is a ~2,900-4,200% premium.
- TSLA · analyze_valuation_ratios: `575` in: Even against high-multiple consumer-cyclical peers (typically 10-20x), this is a ~575-1,250% premium;
- TSLA · analyze_valuation_ratios: `1,250%` in: Even against high-multiple consumer-cyclical peers (typically 10-20x), this is a ~575-1,250% premium;
- TSLA · analyze_valuation_ratios: `43` in: Even against premium software-like multiples (5-10x) it is a ~43-186% premium, and with net margin of only 3.67% (TTM) the sales multiple is not backed by profitability — expensive.
- TSLA · analyze_valuation_ratios: `186%` in: Even against premium software-like multiples (5-10x) it is a ~43-186% premium, and with net margin of only 3.67% (TTM) the sales multiple is not backed by profitability — expensive.
- TSLA · analyze_valuation_ratios: `15.8x` in: Trailing P/E of 347.22x and forward P/E of 174.85x mean the market is paying ~15.8x the S&P 500 multiple today and still ~8x after assuming EPS nearly doubles (+98.6%) — the premium is not supported by current earnings a
- TSLA · analyze_price_performance: `29.2` in: TSLA returned -13.90% over the trailing 1-year window (annualized -13.95%) while the S&P 500 returned +15.30% — an underperformance of roughly 29.2 percentage points — and it did so with 45.44% annualized volatility (3.5
- TSLA · analyze_price_performance: `$86.10` in: a $100 position in TSLA became $86.10 while the same $100 in the index became $115.30.
- TSLA · analyze_price_performance: `$115.30` in: a $100 position in TSLA became $86.10 while the same $100 in the index became $115.30.
- TSLA · analyze_price_performance: `21.8%` in: Beta vs S&P 500: 2.18x - Beta 2.18x vs market 1.00x — TSLA moves 2.18x the market on average (1-year daily basis), so a 10% index move implies roughly a 21.8% TSLA move in the same direction;
- TSLA · analyze_price_performance: `2.6x` in: That is roughly 2.6x the 15% 'low risk' threshold and beyond the 30% 'high risk' line.
- TSLA · analyze_financial_health: `283` in: Operating Margin (FY2025 vs FY2024): 5.11% vs 7.94% - Operating margin compressed 283 bps YoY (FY2025 5.11% vs FY2024 7.94%);
- TSLA · generate_investment_report: `3.89x` in: Free cash flow rose 73.69% YoY to $6.22B with operating cash flow running 3.89x net income, showing strong cash conversion (fundamental analyst)
- TSLA · generate_investment_report: `15.8x` in: Priced at extreme premiums on every valid multiple — trailing P/E ~15.8x the S&P 500, EV/EBITDA ~9x the 'expensive' threshold and P/B above even the top of the tech band — with no valuation cushion, and PEG is unusable
- TSLA · analyze_valuation_ratios: `2,800` in: vs a typical auto-manufacturer sector median of roughly 8-12x it is a ~2,800-4,200% premium.
- TSLA · analyze_valuation_ratios: `440` in: even against a premium tech/auto range of 15-25x it is a ~440-800% premium, signaling the operating cash generation is a tiny fraction of the enterprise value.
- TSLA · analyze_valuation_ratios: `1.5x` in: P/S Ratio: 14.29x - 14.29x sales (price $375.00 / revenue per share $32.055) vs a typical auto-manufacturer 0.5-1.5x and a broad market ~2-3x — a ~850-2,750% premium to auto peers, only partially explained by 25.5% reven
- TSLA · analyze_valuation_ratios: `850` in: P/S Ratio: 14.29x - 14.29x sales (price $375.00 / revenue per share $32.055) vs a typical auto-manufacturer 0.5-1.5x and a broad market ~2-3x — a ~850-2,750% premium to auto peers, only partially explained by 25.5% reven
- TSLA · analyze_financial_health: `0.17` in: Net 4.00% (vs 7.30%) - Gross margin expanded slightly (+0.17pp) but operating margin compressed -2.83pp and net margin compressed -3.30pp;
- TSLA · analyze_financial_health: `-2.83` in: Net 4.00% (vs 7.30%) - Gross margin expanded slightly (+0.17pp) but operating margin compressed -2.83pp and net margin compressed -3.30pp;
- TSLA · analyze_financial_health: `-37.5%` in: deteriorating — net income fell -46.8% YoY to $3.79B (from $7.13B) and operating income fell -37.5% to $4.85B, the second consecutive year of steep profit decline (FY2024 net income was -52.5% vs FY2023's $14.999B)
- TSLA · analyze_financial_health: `41.2%` in: deteriorating — operating expense grew 26.4% ($9.69B → $12.245B) with R&D up 41.2% to $6.41B while revenue declined -2.93%, so cost growth is outpacing the top line
- TSLA · review_analysis: `-46.8%` in: also the 'net income fell -46.8%' is correct but the FY2024 decline is mislabeled as -52.5% vs FY2023 $14.999B (actual -52.5% is correct) — the main real issue is the unlabeled TTM-vs-FY mixing and the performance agent'
- TSLA · review_analysis: `-52.5%` in: also the 'net income fell -46.8%' is correct but the FY2024 decline is mislabeled as -52.5% vs FY2023 $14.999B (actual -52.5% is correct) — the main real issue is the unlabeled TTM-vs-FY mixing and the performance agent'

## Blocked-ratio violations

- TSLA · analyze_valuation_ratios: PEG Ratio: 'note the reported trailing PEG of 4.54x (company_info.csv) is also far above the 2.0x 'expensive' line.'
- TSLA · review_analysis: PEG Ratio: 'MINOR — Valuation cites 'reported trailing PEG of 4.54x' (trailingPegRatio 4.5442) while company_info pegRatio is 4.52;'

## Contradictions

- RELIANCE.NS · generate_investment_report: badge UNDERPERFORMING but: 'eturns — the Sharpe of -0.88 means cash outperformed the stock over the'

Unexplained does not always mean wrong (e.g. a number from general knowledge, or arithmetic across sentences). Read the examples before drawing conclusions.
