"""Regression tests for schema validation behaviour.

Tests cover the normalisation, coercion, and list-capping validators that
exist in the schema models. Tests for removed keyword-based validators
(banned terms, stance checks, CSV source enforcement) have been removed.
"""

from __future__ import annotations

from src.crew.schemas import (
    DataSanityOutput,
    FinalReportOutput,
    FinancialHealthOutput,
    PerformanceOutput,
    ReviewOutput,
    SentimentOutput,
    ValuationOutput,
)
from src.crew.schemas._base import (
    coerce_summary_text,
    normalize_sentiment_signal,
    strip_bracket_prefix,
    strip_count_patterns,
    strip_explanatory_tail,
)

# ── coerce_summary_text ───────────────────────────────────────────────────────


class TestCoerceSummaryText:
    def test_string_passthrough(self):
        assert coerce_summary_text("Hello.", fallback="fb") == "Hello."

    def test_empty_string_fallback(self):
        assert coerce_summary_text("", fallback="fb") == "fb"

    def test_none_fallback(self):
        assert coerce_summary_text(None, fallback="fb") == "fb"

    def test_dict_probes_keys(self):
        assert coerce_summary_text({"conclusion": "done"}, fallback="fb") == "done"

    def test_dict_no_match_fallback(self):
        assert coerce_summary_text({"x": "y"}, fallback="fb") == "fb"

    def test_arbitrary_object_fallback(self):
        assert coerce_summary_text(object(), fallback="fb") != "fb"

    def test_whitespace_only_fallback(self):
        assert coerce_summary_text("   ", fallback="fb") == "fb"


# ── strip_explanatory_tail ────────────────────────────────────────────────────


class TestStripExplanatoryTail:
    def test_strips_because(self):
        assert strip_explanatory_tail("High risk because debt is large") == "High risk"

    def test_no_marker(self):
        assert strip_explanatory_tail("Clean sentence") == "Clean sentence"


# ── strip_bracket_prefix / strip_count_patterns ──────────────────────────────


class TestStripBracketPrefix:
    def test_removes_bracket_tag(self):
        assert strip_bracket_prefix("[POSITIVE] - Outlook is bullish") == "Outlook is bullish"

    def test_no_bracket_passthrough(self):
        assert strip_bracket_prefix("Outlook is bullish") == "Outlook is bullish"

    def test_empty_after_strip(self):
        assert strip_bracket_prefix("[TAG]") == ""


class TestStripCountPatterns:
    def test_removes_x_out_of_y(self):
        assert strip_count_patterns("3 out of 5 analysts bullish") == "analysts bullish"

    def test_removes_n_analysts(self):
        assert (
            strip_count_patterns("Consensus among 12 analysts is positive")
            == "Consensus among is positive"
        )

    def test_preserves_meaningful_digits(self):
        result = strip_count_patterns("Q4 outlook positive")
        assert "Q4" in result


# ── normalize_sentiment_signal ────────────────────────────────────────────────


class TestNormalizeSentimentSignal:
    def test_alias_positive(self):
        assert normalize_sentiment_signal("positive") == "Positive"

    def test_alias_mixed_to_neutral(self):
        assert normalize_sentiment_signal("mixed") == "Neutral"

    def test_unknown_defaults_to_neutral(self):
        assert normalize_sentiment_signal("unknown") == "Neutral"


# ── normalize_payload_lists (via ValuationOutput) ─────────────────────────────


class TestNormalizePayloadLists:
    def test_json_string_list_for_list_str(self):
        model = ValuationOutput.model_validate(
            {
                "summary": "Valuation summary.",
                "implications": '["First implication.", "Second."]',
            }
        )
        assert model.implications == ["First implication.", "Second."]

    def test_dict_items_flattened_for_list_str(self):
        model = ValuationOutput.model_validate(
            {
                "summary": "Valuation summary.",
                "implications": [{"text": "hello"}, {"note": "world"}],
            }
        )
        assert model.implications[0] == "hello"
        assert model.implications[1] == "world"


# ── DataSanityOutput ──────────────────────────────────────────────────────────


class TestDataSanityOutput:
    def test_pass_gate_status(self):
        model = DataSanityOutput.model_validate(
            {
                "summary": "anything",
                "gate_status": "PASS",
                "market_context": "US",
                "company_type": "Non-Financial",
                "ratio_applicability": [{"name": "PE", "status": "VALID"}],
            }
        )
        assert model.gate_status == "PASS"
        assert "0 hard blocks" in model.summary

    def test_hard_block_is_a_skip_not_a_failure(self):
        model = DataSanityOutput.model_validate(
            {
                "summary": "anything",
                "gate_status": "PASS",
                "market_context": "US",
                "company_type": "Non-Financial",
                "ratio_applicability": [{"name": "PE", "status": "HARD_BLOCKED"}],
            }
        )
        assert model.gate_status == "PASS_WITH_SKIPS"

    def test_pass_with_skips_from_soft_block(self):
        model = DataSanityOutput.model_validate(
            {
                "summary": "anything",
                "gate_status": "PASS",
                "market_context": "US",
                "company_type": "Non-Financial",
                "ratio_applicability": [{"name": "PE", "status": "SOFT_BLOCKED"}],
            }
        )
        assert model.gate_status == "PASS_WITH_SKIPS"


# ── ValuationOutput ──────────────────────────────────────────────────────────


class TestValuationOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "Valuation appears fair relative to peers.",
            "metrics": [
                {"label": "P/E", "value": "22x", "source": "company_info.csv"},
            ],
            "implications": ["Growth expectations priced into current valuation."],
            "citations": [],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = ValuationOutput.model_validate(self._valid_payload())
        assert "fair" in model.summary.lower()

    def test_metrics_capped_at_5(self):
        metrics = [
            {"label": f"M{i}", "value": "1x", "source": "company_info.csv"} for i in range(10)
        ]
        model = ValuationOutput.model_validate(self._valid_payload(metrics=metrics))
        assert len(model.metrics) <= 5

    def test_implications_capped_at_4(self):
        imps = [f"Implication {i}" for i in range(8)]
        model = ValuationOutput.model_validate(self._valid_payload(implications=imps))
        assert len(model.implications) <= 4


# ── PerformanceOutput ─────────────────────────────────────────────────────────


class TestPerformanceOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "Returns are mixed with moderate downside risk.",
            "metrics": [
                {"label": "Total Return", "value": "12%", "source": "prices.csv"},
            ],
            "risk_notes": ["High drawdown severity during corrections."],
            "citations": [],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = PerformanceOutput.model_validate(self._valid_payload())
        assert model.summary

    def test_risk_notes_capped_at_3(self):
        model = PerformanceOutput.model_validate(
            self._valid_payload(risk_notes=["Note 1", "Note 2", "Note 3", "Note 4", "Note 5"])
        )
        assert len(model.risk_notes) <= 3


# ── FinancialHealthOutput ────────────────────────────────────────────────────


class TestFinancialHealthOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "Financial health appears stable with controlled leverage.",
            "metrics": [
                {"label": "Revenue Growth YoY", "value": "8%"},
            ],
            "growth_signals": ["improving"],
            "caution_signals": ["Leverage risk elevated"],
            "citations": [],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = FinancialHealthOutput.model_validate(self._valid_payload())
        assert "stable" in model.summary.lower()

    def test_growth_signals_passthrough(self):
        model = FinancialHealthOutput.model_validate(
            self._valid_payload(growth_signals=["Revenue is expanding quickly"])
        )
        assert model.growth_signals == ["Revenue is expanding quickly"]

    def test_growth_signals_capped_at_3(self):
        model = FinancialHealthOutput.model_validate(
            self._valid_payload(growth_signals=["a", "b", "c", "d"])
        )
        assert len(model.growth_signals) <= 3


# ── SentimentOutput ──────────────────────────────────────────────────────────


class TestSentimentOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "Market expectations are stable with mixed sentiment pressure.",
            "sentiment_signal": "Neutral",
            "analyst_consensus": "Consensus remains neutral and stable",
            "key_points": ["Analyst consensus shows institutional flow stability."],
            "news": [],
            "citations": [],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = SentimentOutput.model_validate(self._valid_payload())
        assert model.sentiment_signal in {"Positive", "Neutral", "Negative"}

    def test_consensus_strips_bracket_prefix_and_counts(self):
        model = SentimentOutput.model_validate(
            self._valid_payload(analyst_consensus="[POSITIVE] - 3 out of 5 analysts lean bullish")
        )
        assert not any(c.isdigit() for c in model.analyst_consensus)
        assert "bullish" in model.analyst_consensus.lower()

    def test_unknown_signal_defaults_to_neutral(self):
        model = SentimentOutput.model_validate(self._valid_payload(sentiment_signal="unknown"))
        assert model.sentiment_signal == "Neutral"

    def test_key_points_capped_at_4(self):
        model = SentimentOutput.model_validate(
            self._valid_payload(key_points=["a", "b", "c", "d", "e", "f"])
        )
        assert len(model.key_points) <= 4


# ── ReviewOutput ──────────────────────────────────────────────────────────────


class TestReviewOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "No material inconsistencies found.",
            "confidence_adjustment": "Unchanged",
            "data_accuracy": [],
            "watchouts": [],
            "confirmed_findings": ["All metrics validated."],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = ReviewOutput.model_validate(self._valid_payload())
        assert model.confidence_adjustment == "Unchanged"

    def test_confidence_alias_normalization(self):
        model = ReviewOutput.model_validate(self._valid_payload(confidence_adjustment="increased"))
        assert model.confidence_adjustment == "Increase"

    def test_confirmed_cleared_when_issues_present(self):
        model = ReviewOutput.model_validate(
            self._valid_payload(
                data_accuracy=["PE vs actual: 22.1 mismatch with 24.3."],
                confirmed_findings=["Something confirmed."],
            )
        )
        assert model.confirmed_findings == []

    def test_confirmed_findings_capped_at_3(self):
        model = ReviewOutput.model_validate(
            self._valid_payload(confirmed_findings=["a", "b", "c", "d"])
        )
        assert len(model.confirmed_findings) <= 3


# ── FinalReportOutput ─────────────────────────────────────────────────────────


class TestFinalReportOutput:
    def _valid_payload(self, **overrides):
        base = {
            "summary": "At current prices, risk-reward appears balanced.",
            "strengths": ["Strong cash generation."],
            "risks": ["Margin compression risk ahead."],
            "watch_next": ["Earnings guidance revision."],
            "best_suited_for": ["Growth-oriented portfolios."],
            "not_ideal_for": ["Income-seeking strategies."],
            "guidance_for_existing_holders": "Maintain current exposure.",
            "guidance_for_new_buyers": "Stage entries on dips.",
            "verdict": "HOLD",
            "confidence": "Medium",
            "citations": [],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        model = FinalReportOutput.model_validate(self._valid_payload())
        assert model.verdict == "HOLD"
        assert model.confidence == "Medium"

    def test_verdict_normalization(self):
        model = FinalReportOutput.model_validate(self._valid_payload(verdict="strong-buy"))
        assert model.verdict == "STRONG BUY"

    def test_confidence_from_adjustment_fallback(self):
        payload = self._valid_payload()
        del payload["confidence"]
        payload["confidence_adjustment"] = "increase"
        model = FinalReportOutput.model_validate(payload)
        assert model.confidence == "High"

    def test_key_reasons_alias(self):
        payload = self._valid_payload()
        del payload["strengths"]
        payload["key_reasons"] = ["Strong brand."]
        model = FinalReportOutput.model_validate(payload)
        assert model.strengths == ["Strong brand."]

    def test_strengths_capped_at_4(self):
        model = FinalReportOutput.model_validate(
            self._valid_payload(strengths=["a", "b", "c", "d", "e", "f"])
        )
        assert len(model.strengths) <= 4
