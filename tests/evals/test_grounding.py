# SPDX-License-Identifier: MIT
"""Unit tests for the eval grader (evals/grounding.py). Pure functions, no LLM or network."""

from evals.grounding import (
    blocked_violations,
    contradictions,
    extract_numbers,
    fact_value,
    grounding,
)

FACTS = """FINANCIAL SNAPSHOT
P/E Ratio: 28.41x
P/B Ratio: N/A
ROE (%): 147.25%
Free Cash Flow (USD B): $135.47B
Market Cap: $3,412,000,000,000
Total Return (%): 18.62%
Max Drawdown (%): -23.40%
Beta (vs market): 1.12x
Performance Badge: OUTPERFORMING
Valuation Verdict: Yes | Trading above fair value
Health Status: STRONG
"""


# ---------- number extraction ----------


def test_extracts_units_and_scales():
    nums = {n.text: n for n in extract_numbers("P/E of 28.4x, ROE 147%, FCF $135.5B, cap $3.41T")}
    assert nums["28.4x"].kind == "ratio"
    assert nums["147%"].kind == "pct"
    assert nums["$135.5B"].absolute == 135.5e9
    assert nums["$3.41T"].absolute == 3.41e12


def test_skips_years_index_names_time_spans_and_counts():
    text = "Since 2024 the stock beat the S&P 500 over 52-week and 12-month windows in Q3; 3 risks."
    assert extract_numbers(text) == []


def test_keeps_percent_that_looks_like_a_year():
    assert [n.text for n in extract_numbers("up 2023% (typo-ish)")] == ["2023%"]


# ---------- grounding ----------


def test_rounded_numbers_are_grounded():
    total, bad = grounding("P/E is 28.4x, ROE about 147%, return 18.6%, beta 1.1x", FACTS)
    assert total == 4 and bad == []


def test_scale_conversions_are_grounded():
    total, bad = grounding("Free cash flow of $135.5B on a $3.41T market cap", FACTS)
    assert total == 2 and bad == []


def test_dropped_sign_is_grounded():
    assert grounding("a 23.4% drawdown", FACTS)[1] == []


def test_invented_numbers_are_flagged():
    total, bad = grounding("P/E of 31.2x and a 12% dividend yield", FACTS)
    assert total == 2 and bad == ["31.2x", "12%"]


def test_wrong_rounding_is_flagged():
    # 28.41 can be written 28 or 28.4, but not 29
    assert grounding("P/E of 29x", FACTS)[1] == ["29x"]


# ---------- blocked metrics ----------


def test_blocked_metric_with_value_is_flagged():
    hits = blocked_violations("The price-to-book of 45.2x looks stretched.", {"P/B Ratio"})
    assert len(hits) == 1 and "45.2" in hits[0]


def test_blocked_metric_without_value_is_fine():
    assert blocked_violations("P/B is not meaningful here (N/A).", {"P/B Ratio"}) == []


def test_forward_pe_is_not_confused_with_pe():
    assert blocked_violations("Forward P/E of 25.1x", {"P/E Ratio"}) == []
    assert len(blocked_violations("Forward P/E of 25.1x", {"Forward P/E"})) == 1


# ---------- contradictions ----------


def test_fact_value():
    assert fact_value(FACTS, "Performance Badge") == "OUTPERFORMING"
    assert fact_value(FACTS, "Missing Label") is None


def test_contradiction_with_badge_is_flagged():
    found = contradictions("The stock has underperformed its index this year.", FACTS)
    assert len(found) == 1 and "OUTPERFORMING" in found[0]


def test_negated_mention_is_not_a_contradiction():
    assert contradictions("It did not underperform the market.", FACTS) == []


def test_valuation_and_health_contradictions():
    found = contradictions("Shares look undervalued despite a weak balance sheet.", FACTS)
    assert len(found) == 2


def test_consistent_text_has_no_contradictions():
    text = "Outperforming the index; trades above fair value; strong balance sheet."
    assert contradictions(text, FACTS) == []


def test_metric_items_are_graded_as_label_value_pairs():
    from evals.run_grounding_eval import _text_of
    from src.crew.schemas import ValuationOutput

    model = ValuationOutput(summary="ok", metrics=[{"label": "P/B Ratio", "value": "45.2x"}])
    text = _text_of(model, "")
    assert "P/B Ratio: 45.2x" in text
    assert len(blocked_violations(text, {"P/B Ratio"})) == 1


# ---------- source attribution (sentences taken from a real AAPL run) ----------

AAPL_FACTS = "P/E Ratio: 39.88x\nEV/EBITDA: 30.34x\nP/B Ratio: 47.25x"
AAPL_DATA = (
    "trailingEps,forwardEps,currentPrice,bookValue,earningsGrowth\n8.72,9.5707,347.73,7.36,0.287"
)
PROMPT = "Compare vs {market_index} average (~22x). State: tech avg is 5-15x. EV/EBITDA fair range 10-15x."


def _cls(text):
    from evals.grounding import classify

    return classify(text, AAPL_FACTS, AAPL_DATA, PROMPT)


def test_ranges_are_not_negative_numbers():
    assert [n.text for n in extract_numbers("a 10-15x range")] == ["10", "15x"]


def test_prompt_benchmark_and_derived_premium():
    out = _cls("39.88x vs the S&P 500 average ~22x = ~81% premium")
    assert out["facts"] == ["39.88x"]
    assert out["prompt"] == ["22x"]
    assert out["derived"] == ["81%"]  # 39.88 / 22 - 1
    assert out["unexplained"] == []


def test_raw_data_numbers_and_fraction_as_percent():
    out = _cls("Forward EPS $9.57 vs trailing $8.72 while earnings grew 28.7%.")
    assert sorted(out["data"]) == ["$8.72", "$9.57", "28.7%"]


def test_derived_growth_from_same_sentence():
    out = _cls("The market expects ~9.8% EPS growth (forward EPS $9.57 vs trailing $8.72).")
    assert out["derived"] == ["9.8%"]


def test_derived_needs_operands_in_the_same_sentence():
    out = _cls("Forward EPS is $9.57. Trailing EPS is $8.72. Growth of 9.8% is expected.")
    assert out["unexplained"] == ["9.8%"]


def test_invented_number_is_unexplained():
    out = _cls("The dividend yield of 3.1% supports the valuation.")
    assert out["unexplained"] == ["3.1%"]


def test_data_matching_is_exact_not_approximate():
    # $347.73 is in the data; $350.10 is not, even though it is within 1%
    out = _cls("Price $347.73 today; target $350.10.")
    assert out["data"] == ["$347.73"] and out["unexplained"] == ["$350.10"]


# ---------- cases found by reading a real AAPL run ----------


def test_drawdown_in_dollars_from_a_negative_percentage():
    from evals.grounding import classify

    facts = "Max Drawdown (%): -13.80%"
    out = classify(
        "A -13.80% drawdown: for every $100 invested, the worst drop was to $86.20.",
        facts,
        "",
        "$100",
    )
    assert out["derived"] == ["$86.20"] and out["unexplained"] == []


def test_beta_written_as_a_percentage():
    from evals.grounding import classify

    out = classify(
        "With a beta of 0.60x, it moves only 60% as much as the index.", "Beta (vs market): 0.60x"
    )
    assert out["derived"] == ["60%"]


def test_metric_value_and_note_are_one_sentence():
    from evals.grounding import classify
    from evals.run_grounding_eval import _text_of
    from src.crew.schemas import FinancialHealthOutput

    model = FinancialHealthOutput(
        summary="ok",
        metrics=[
            {
                "label": "Net income growth",
                "value": "+19.49%",
                "note": "Net Income $93.74B → $112.01B",
            }
        ],
    )
    out = classify(_text_of(model, ""), "", "93740000000,112010000000")
    assert out["derived"] == ["19.49%"] and out["unexplained"] == []


def test_unexplained_numbers_keep_their_sentence_for_review():
    from evals.grounding import classify

    out = classify("Insider sales were well above $200M.", "")
    assert out["unexplained"] == ["$200M"]
    assert out["unexplained_context"] == ["Insider sales were well above $200M."]


# ---------- cases found in the 5-ticker run ----------


def test_review_agent_flagging_a_blocked_ratio_is_not_a_violation():
    text = "The valuation analyst used a PEG of ~4.54x even though PEG is SOFT_BLOCKED."
    assert blocked_violations(text, {"PEG Ratio"}) == []


def test_using_a_blocked_ratio_is_still_a_violation():
    hits = blocked_violations("A PEG of ~4.54x means growth is overpriced.", {"PEG Ratio"})
    assert len(hits) == 1 and "4.54x" in hits[0]


def test_far_from_counts_as_negation():
    # KO run: the agent said the stock is NOT in the undervalued zone, which agrees with the facts
    text = "Even with growth, the multiple is far from the sub-1.0 undervalued zone."
    assert contradictions(text, FACTS) == []


def test_something_else_outperforming_is_not_a_contradiction():
    # RELIANCE.NS run: "cash outperformed the stock" agrees with UNDERPERFORMING
    facts = "Performance Badge: UNDERPERFORMING"
    assert contradictions("A Sharpe of -0.88 means cash outperformed the stock.", facts) == []
    assert len(contradictions("The stock outperformed its peers this year.", facts)) == 1


def test_not_meaningful_counts_as_flagging():
    # JPM run: quoting the raw value while saying it doesn't apply to a bank is the right call
    text = "Gross margin is 0.0% (not meaningful for a bank)."
    assert blocked_violations(text, {"Gross Margin (%)"}) == []


def test_report_has_no_trailing_whitespace():
    # pre-commit's trailing-whitespace hook failed CI on a generated report
    from evals.run_grounding_eval import report

    long_sentence = "word " * 60 + "with 12.34% inside"
    rec = {
        "symbol": "X",
        "verdict": "HOLD",
        "confidence": "Low",
        "latency_s": 1.0,
        "data_as_of": "2026-01-01",
        "run": 1,
        "tasks": {
            "generate_investment_report": {
                "schema_valid": True,
                "numbers": 1,
                "sources": {
                    "facts": [],
                    "data": [],
                    "prompt": [],
                    "derived": [],
                    "unexplained": ["12.34%"],
                    "unexplained_context": [long_sentence[:220]],
                },
                "ungrounded": ["12.34%"],
                "blocked_violations": [],
                "contradictions": [],
            }
        },
    }
    md = report([rec], {"model": "m", "tickers": ["X"], "runs": 1})
    assert all(line == line.rstrip() for line in md.splitlines())
    assert md.endswith("\n")
