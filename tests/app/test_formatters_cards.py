"""Unit tests for each formatter card renderer and shared helpers."""

from src.app.utils.formatters._data_quality import _render_data_quality_card
from src.app.utils.formatters._health import _render_health_card
from src.app.utils.formatters._performance import _render_performance_card
from src.app.utils.formatters._review import _render_review_card
from src.app.utils.formatters._sentiment import _render_sentiment_card
from src.app.utils.formatters._shared import (
    _badge_classes,
    _card,
    _clean_line,
    _esc,
    _extract_verdict,
    _extract_ws_summary,
    _parse_kv,
    _parse_kv_all,
    _parse_kv_split,
    _parse_sections,
)
from src.app.utils.formatters._valuation import _render_valuation_card

# ---------------------------------------------------------------------------
# _shared helpers
# ---------------------------------------------------------------------------


def test_esc_ampersand():
    assert _esc("AT&T") == "AT&amp;T"


def test_esc_angle_brackets():
    assert _esc("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"


def test_parse_kv_found():
    text = "P/E Ratio: 22.5x\nP/B Ratio: 3.0x"
    assert _parse_kv(text, "P/E Ratio") == "22.5x"


def test_parse_kv_case_insensitive():
    text = "gate status: PASS"
    assert _parse_kv(text, "Gate Status") == "PASS"


def test_parse_kv_missing():
    assert _parse_kv("no relevant lines", "Missing Key") == ""


def test_parse_kv_all_multiple():
    text = "Warning: disk low\nWarning: cpu high\nWarning: memory low"
    results = _parse_kv_all(text, "Warning")
    assert results == ["disk low", "cpu high", "memory low"]


def test_parse_kv_all_limit():
    text = "\n".join(f"Warning: item {i}" for i in range(10))
    results = _parse_kv_all(text, "Warning", limit=3)
    assert len(results) == 3


def test_parse_kv_split_with_pipe():
    text = "Valuation Verdict: Yes | Trading above fair value"
    val, note = _parse_kv_split(text, "Valuation Verdict")
    assert val == "Yes"
    assert note == "Trading above fair value"


def test_parse_kv_split_no_pipe():
    text = "Valuation Verdict: Fair"
    val, note = _parse_kv_split(text, "Valuation Verdict")
    assert val == "Fair"
    assert note == ""


def test_clean_line_strips_bullets():
    assert _clean_line("  - **Bold item**  ") == "Bold item"


def test_clean_line_strips_numbers():
    assert _clean_line("1. First item") == "First item"


def test_extract_ws_summary_found():
    raw = "Some preamble\nStructured Summary: Company shows strong growth.\nMore text"
    assert _extract_ws_summary(raw) == "Company shows strong growth."


def test_extract_ws_summary_missing():
    assert _extract_ws_summary("no summary here") == ""


def test_extract_ws_summary_escapes_html():
    raw = "Structured Summary: A&B <Corp>"
    result = _extract_ws_summary(raw)
    assert "&amp;" in result
    assert "&lt;" in result


def test_extract_verdict_buy():
    text = "VERDICT: BUY | Confidence: High"
    v, c, _ = _extract_verdict(text)
    assert v == "BUY"
    assert c == "High"


def test_extract_verdict_strong_buy():
    text = "analysis...\nVERDICT: STRONG BUY | Confidence: Medium\nmore"
    v, c, cleaned = _extract_verdict(text)
    assert v == "STRONG BUY"
    assert c == "Medium"
    assert "VERDICT:" not in cleaned


def test_extract_verdict_inconclusive_fallback():
    v, c, _ = _extract_verdict("no verdict in here")
    assert v == "INCONCLUSIVE"
    assert c == "N/A"


def test_badge_classes_positive():
    cls = _badge_classes("yes")
    assert "green" in cls


def test_badge_classes_negative():
    cls = _badge_classes("no")
    assert "red" in cls


def test_badge_classes_neutral():
    cls = _badge_classes("fair")
    assert "yellow" in cls


def test_card_contains_data_section():
    html = _card("<p>body</p>", data_section="valuation")
    assert 'data-section="valuation"' in html


def test_card_without_data_section():
    html = _card("<p>body</p>")
    assert "data-section" not in html


def test_card_materializes_todos():
    html = _card("<!-- TODO: add more data -->")
    assert "TODO: add more data" in html
    assert "<!--" not in html


def test_parse_sections_splits_by_header():
    text = "FINANCIAL SNAPSHOT\nP/E: 20x\nVALUATION VERDICT\nVerdict: Fair"
    sections = _parse_sections(text)
    assert "FINANCIAL SNAPSHOT" in sections
    assert any("P/E: 20x" in line for line in sections.get("FINANCIAL SNAPSHOT", []))


# ---------------------------------------------------------------------------
# _render_valuation_card
# ---------------------------------------------------------------------------

_VALUATION_RAW = """\
FINANCIAL SNAPSHOT
P/E Ratio: 20.00x
Forward P/E: 18.00x
P/B Ratio: 3.00x
P/S Ratio: 5.00x
PEG Ratio: 1.50x
EV/EBITDA: 12.00x

Valuation Verdict: Yes | Trading above fair value
Insight: Valuation is rich; watch earnings growth.
"""


def test_valuation_card_data_section():
    html = _render_valuation_card(_VALUATION_RAW, "AAPL")
    assert 'data-section="valuation"' in html


def test_valuation_card_overvalued_badge():
    html = _render_valuation_card(_VALUATION_RAW, "AAPL")
    assert "OVERVALUED" in html


def test_valuation_card_pe_ratio_present():
    html = _render_valuation_card(_VALUATION_RAW, "AAPL")
    assert "P/E Ratio" in html


def test_valuation_card_insight():
    html = _render_valuation_card(_VALUATION_RAW, "AAPL")
    assert "Valuation is rich" in html


def test_valuation_card_undervalued():
    raw = _VALUATION_RAW.replace("Valuation Verdict: Yes", "Valuation Verdict: No")
    html = _render_valuation_card(raw, "AAPL")
    assert "UNDERVALUED" in html


def test_valuation_card_fair_value():
    raw = _VALUATION_RAW.replace("Valuation Verdict: Yes", "Valuation Verdict: Fair")
    html = _render_valuation_card(raw, "AAPL")
    assert "FAIR VALUE" in html


def test_valuation_card_minimal_input():
    html = _render_valuation_card("", "MSFT")
    assert 'data-section="valuation"' in html
    assert "INSUFFICIENT DATA" in html  # no verdict means no valuation claim


# ---------------------------------------------------------------------------
# _render_performance_card
# ---------------------------------------------------------------------------

_PERF_RAW = """\
PERFORMANCE & RISK
Total Return (%): 25.00%
Annualized Return (%): 12.50%
Volatility (%): 18.00%
Volatility Label: Moderate
Max Drawdown (%): -15.00%
Beta (vs market): 1.10x
Sharpe Ratio: 0.85
Performance Badge: OUTPERFORMING
Structured Summary: Strong risk-adjusted returns over the period.
"""


def test_performance_card_data_section():
    html = _render_performance_card(_PERF_RAW, "AAPL")
    assert 'data-section="performance"' in html


def test_performance_card_total_return():
    html = _render_performance_card(_PERF_RAW, "AAPL")
    assert "25.00%" in html


def test_performance_card_outperforming_badge():
    html = _render_performance_card(_PERF_RAW, "AAPL")
    assert "OUTPERFORMING" in html


def test_performance_card_sharpe():
    html = _render_performance_card(_PERF_RAW, "AAPL")
    assert "Sharpe" in html


def test_performance_card_minimal():
    html = _render_performance_card("", "TSLA")
    assert 'data-section="performance"' in html


# ---------------------------------------------------------------------------
# _render_health_card
# ---------------------------------------------------------------------------

_HEALTH_RAW = """\
FINANCIAL HEALTH
Health Status: STRONG
HEALTH_DESCRIPTIONS
Revenue Growth Desc: Growing rapidly | 15.00% annually
Profit Growth Desc: Strong profit growth | 18.00% annually
Debt Desc: Very low debt levels | 25.00% ratio
Cash Desc: Generates strong cash flow | $5.00B

FINANCIAL METRICS
Revenue Growth Rate: 15.00%
Earnings Growth Rate: 18.00%
Debt/Equity: 25.00
Current Ratio: 2.50
Operating Cash Flow (USD B): $5.00B

Structured Summary: Healthy balance sheet with strong cash generation.
"""


def test_health_card_data_section():
    html = _render_health_card(_HEALTH_RAW, "AAPL")
    assert 'data-section="health"' in html


def test_health_card_strong_badge():
    html = _render_health_card(_HEALTH_RAW, "AAPL")
    assert "STRONG" in html


def test_health_card_revenue_growth():
    html = _render_health_card(_HEALTH_RAW, "AAPL")
    assert "Growing rapidly" in html


def test_health_card_cash_flow():
    html = _render_health_card(_HEALTH_RAW, "AAPL")
    assert "Cash" in html


def test_health_card_minimal():
    html = _render_health_card("", "MSFT")
    assert 'data-section="health"' in html


# ---------------------------------------------------------------------------
# _render_sentiment_card
# ---------------------------------------------------------------------------

_SENTIMENT_RAW = """\
SENTIMENT & ANALYST SUMMARY
Analyst Consensus: Buy
Strong Buy: 10
Buy: 15
Hold: 5
Sell: 2
Strong Sell: 0
Top Holder: Vanguard Group | 7.50%
News Headline: Company beats Q3 earnings expectations.
News Headline: Expansion into new markets drives growth.
Structured Summary: Positive analyst consensus with strong institutional backing.
"""


def test_sentiment_card_data_section():
    html = _render_sentiment_card(_SENTIMENT_RAW, "AAPL")
    assert 'data-section="sentiment"' in html


def test_sentiment_card_contains_buy():
    html = _render_sentiment_card(_SENTIMENT_RAW, "AAPL")
    assert "Buy" in html


def test_sentiment_card_minimal():
    html = _render_sentiment_card("", "NVDA")
    assert 'data-section="sentiment"' in html


# ---------------------------------------------------------------------------
# _render_review_card
# ---------------------------------------------------------------------------

_REVIEW_RAW = """\
Data Accuracy: P/E ratio verified against SEC filings.
Confirmed: Revenue growth matches quarterly reports.
Watchout: Debt-to-equity ratio elevated vs industry peers.
Structured Summary: Data integrity verified with minor caveats.
"""


def test_review_card_data_section():
    html = _render_review_card(_REVIEW_RAW, "AAPL")
    assert 'data-section="review"' in html


def test_review_card_data_accuracy():
    html = _render_review_card(_REVIEW_RAW, "AAPL")
    assert "Data Accuracy" in html


def test_review_card_watchout():
    html = _render_review_card(_REVIEW_RAW, "AAPL")
    assert "Watchout" in html


def test_review_card_confirmed():
    html = _render_review_card(_REVIEW_RAW, "AAPL")
    assert "Confirmed" in html


def test_review_card_symbol_badge():
    html = _render_review_card(_REVIEW_RAW, "AAPL")
    assert "AAPL" in html


def test_review_card_empty_raw():
    html = _render_review_card("", "MSFT")
    assert 'data-section="review"' in html
    assert "No review items available" in html


# ---------------------------------------------------------------------------
# _render_data_quality_card
# ---------------------------------------------------------------------------

_DQ_RAW = """\
Gate Status: PASS
Structured Summary: All critical data files validated successfully.
Market Context: US Equity
Company Type: Large Cap Tech
Validated File: company_info.csv
Validated File: historical_prices.csv
Validated File: income_statement.csv
Warning: google_trends.csv unavailable - using fallback
"""


def test_data_quality_card_data_section():
    html = _render_data_quality_card(_DQ_RAW, "AAPL")
    assert 'data-section="data-quality"' in html


def test_data_quality_card_pass_badge():
    html = _render_data_quality_card(_DQ_RAW, "AAPL")
    assert "PASS" in html
    assert "green" in html


def test_data_quality_card_validated_count():
    html = _render_data_quality_card(_DQ_RAW, "AAPL")
    assert "3 validated" in html


def test_data_quality_card_warning_count():
    html = _render_data_quality_card(_DQ_RAW, "AAPL")
    assert "1 warnings" in html


def test_data_quality_card_summary():
    html = _render_data_quality_card(_DQ_RAW, "AAPL")
    assert "All critical data files validated" in html


def test_data_quality_card_fail_badge():
    raw = _DQ_RAW.replace("Gate Status: PASS", "Gate Status: FAIL")
    html = _render_data_quality_card(raw, "AAPL")
    assert "FAIL" in html
    assert "red" in html


def test_data_quality_card_warn_gate():
    raw = _DQ_RAW.replace("Gate Status: PASS", "Gate Status: WARN")
    html = _render_data_quality_card(raw, "AAPL")
    assert "WARN" in html
    assert "yellow" in html


def test_data_quality_card_missing_data():
    raw = "Gate Status: FAIL\nMissing/Invalid File: balance_sheet.csv\nCritical Issue: No price data\n"
    html = _render_data_quality_card(raw, "AAPL")
    assert "1 missing" in html
    assert "1 critical" in html


def test_valuation_badge_fair_verdict_shows_fair_value() -> None:
    from src.app.utils.formatters._valuation import _render_valuation_card

    html = _render_valuation_card("Valuation Verdict: Fair | Trading near fair value", "TEST")
    assert "FAIR VALUE" in html


def test_valuation_badge_unknown_verdict_shows_insufficient_data() -> None:
    from src.app.utils.formatters._valuation import _render_valuation_card

    html = _render_valuation_card("Valuation Verdict: Unknown | Insufficient data", "TEST")
    assert "INSUFFICIENT DATA" in html
    assert "FAIR VALUE" not in html
