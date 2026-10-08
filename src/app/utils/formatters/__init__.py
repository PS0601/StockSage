# SPDX-License-Identifier: MIT
"""Log formatting utilities — wireframe-matched Tailwind HTML rendering.

Public API: ``format_log_entry(log_entry) -> str``

Card renderers are split into one module per analysis section:
  _report.py        — Final investment report (company header + guidance)
  _performance.py   — Price performance & risk
  _health.py        — Financial health
  _valuation.py     — Valuation & profitability
  _sentiment.py     — Market sentiment & news
  _review.py        — Quality review
  _data_quality.py  — Data sanity check
  _shared.py        — Shared helpers, constants, badge utilities
"""

from src.app.utils.formatters._data_quality import _render_data_quality_card
from src.app.utils.formatters._health import _render_health_card
from src.app.utils.formatters._performance import _render_performance_card
from src.app.utils.formatters._report import _render_report_cards
from src.app.utils.formatters._review import _render_review_card
from src.app.utils.formatters._sentiment import _render_sentiment_card
from src.app.utils.formatters._shared import (
    LogEntry,
    StatusType,
    _esc,
    _extract_ws_summary,
    _is_analysis_entry,
)
from src.app.utils.formatters._units import strip_units_after_na
from src.app.utils.formatters._valuation import _render_valuation_card

_RENDERERS = {
    "analyzing_valuation_ratios": _render_valuation_card,
    "analyzing_price_performance": _render_performance_card,
    "analyzing_financial_health": _render_health_card,
    "analyzing_market_sentiment": _render_sentiment_card,
    "reviewing_analysis": _render_review_card,
    "generating_investment_report": _render_report_cards,
    "validating_data_sanity": _render_data_quality_card,
}


def _format_analysis_block(log_entry: LogEntry) -> str:
    substage_val = log_entry.substage.value if log_entry.substage is not None else ""
    raw = log_entry.message or ""
    symbol = (log_entry.symbol or "").upper()

    ws_summary = _extract_ws_summary(raw)
    extra_attrs = f' data-substage="{substage_val}"'
    if ws_summary:
        extra_attrs += f' data-ws-summary="{ws_summary}"'

    renderer = _RENDERERS.get(substage_val)
    if renderer:
        # Cards append units after values; a missing value must read plain N/A.
        result = strip_units_after_na(renderer(raw, symbol))
        tag_end = result.index(">")
        return result[:tag_end] + extra_attrs + result[tag_end:]

    return ""


def _ws_entry(
    text: str, status: str = "success", arrow: bool = False, stage: str = "", substage: str = ""
) -> str:
    """Build a single workspace-entry div."""
    prefix = "&rarr; " if arrow else ""
    sub_attr = f' data-substage="{substage}"' if substage else ""
    return (
        f'<div class="workspace-entry" data-status="{status}" data-stage="{stage}"{sub_attr}>'
        f'<span class="ws-icon"></span>'
        f'<span class="ws-text">{prefix}{text}</span></div>'
    )


def format_log_entry(log_entry: LogEntry) -> str:
    """Format a log entry for HTML display.

    Analysis entries (SUCCESS) get rich cards. Everything else gets compact
    workspace-entry lines.
    """
    # Stage-level entries (no substage) — no arrow prefix
    if log_entry.substage is None:
        text = _esc(log_entry.message or log_entry.stage.display_name)
        return _ws_entry(
            text, log_entry.status_type.value, arrow=False, stage=log_entry.stage.value
        )

    # Analysis entries — rich card for SUCCESS, workspace line for progress/failed
    if _is_analysis_entry(log_entry):
        if log_entry.status_type == StatusType.SUCCESS:
            return _format_analysis_block(log_entry)
        label = _esc(log_entry.substage.display_name)
        return (
            f'<div class="workspace-entry" data-status="{log_entry.status_type.value}" '
            f'data-stage="{log_entry.stage.value}" data-substage="{log_entry.substage.value}">'
            f'<span class="ws-icon"></span>'
            f'<span class="ws-text">&rarr; {label}</span></div>'
        )

    # Non-analysis substage entries (download, validation, etc.) — with arrow
    text = _esc(log_entry.message or log_entry.substage.display_name)
    return _ws_entry(
        text,
        log_entry.status_type.value,
        arrow=True,
        stage=log_entry.stage.value,
        substage=log_entry.substage.value,
    )
