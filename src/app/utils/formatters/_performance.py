# SPDX-License-Identifier: MIT
"""Price performance & risk card renderer."""

from src.app.utils.formatters._shared import (
    _badge_classes,
    _card,
    _esc,
    _info_icon,
    _parse_kv,
)


def _strip_suffix(val: str, *suffixes: str) -> str:
    """Strip trailing units like '%' or 'x' so the formatter can append its own."""
    v = val.strip()
    for s in suffixes:
        if v.endswith(s):
            v = v[: -len(s)].strip()
    return v


def _render_performance_card(raw: str, symbol: str) -> str:  # noqa: ARG001
    total_return = _strip_suffix(_parse_kv(raw, "Total Return (%)"), "%")
    annualized = _strip_suffix(_parse_kv(raw, "Annualized Return (%)"), "%")
    volatility = _strip_suffix(_parse_kv(raw, "Volatility (%)"), "%")
    vol_label = _parse_kv(raw, "Volatility Label") or "Moderate"
    max_dd = _strip_suffix(_parse_kv(raw, "Max Drawdown (%)"), "%")
    beta = _strip_suffix(_parse_kv(raw, "Beta (vs market)"), "x")
    sharpe = _parse_kv(raw, "Sharpe Ratio")
    market_return = _strip_suffix(_parse_kv(raw, "Market Total Return (%)"), "%")
    perf_badge = _parse_kv(raw, "Performance Badge") or "IN LINE"
    insight = _parse_kv(raw, "Insight") or ""

    badge_cls = _badge_classes(perf_badge.split()[0] if perf_badge else "IN LINE")

    def _is_pos(val: str | None) -> bool:
        return bool(val) and val is not None and not val.strip().startswith("-")

    def _ret_style(val: str | None) -> tuple[str, str, str]:
        if not val:
            return "text-gray-900", "bg-white border border-gray-200", ""
        if _is_pos(val):
            return (
                "text-green-600",
                "bg-white border border-green-300 border-l-4 border-l-green-500",
                '<span class="text-green-500 mr-1">&#x2191;</span>',
            )
        return (
            "text-red-600",
            "bg-white border border-red-300 border-l-4 border-l-red-500",
            '<span class="text-red-500 mr-1">&#x2193;</span>',
        )

    def _vol_style(label: str) -> tuple[str, str]:
        low = label.lower()
        if low in ("low", "stable"):
            return (
                "text-green-600",
                "bg-white border border-green-300 border-l-4 border-l-green-500",
            )
        if low in ("high", "very high"):
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        return "text-orange-500", "bg-white border border-orange-300 border-l-4 border-l-orange-500"

    def _beta_style(val: str | None) -> tuple[str, str]:
        if not val:
            return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"
        try:
            b = float(val.replace("x", "").strip())
        except ValueError:
            return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"
        if b > 1.3:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        if b < 0.7:
            return (
                "text-green-600",
                "bg-white border border-green-300 border-l-4 border-l-green-500",
            )
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    def _sharpe_style(val: str | None) -> tuple[str, str]:
        if not val:
            return "text-gray-900", "bg-white border border-gray-200"
        try:
            s = float(val.strip())
        except ValueError:
            return "text-gray-900", "bg-white border border-gray-200"
        if s >= 1.0:
            return (
                "text-green-600",
                "bg-white border border-green-300 border-l-4 border-l-green-500",
            )
        if s < 0.5:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    tr_c, tr_bg, tr_arrow = _ret_style(total_return)
    ar_c, ar_bg, _ = _ret_style(annualized)
    vol_c, vol_bg = _vol_style(vol_label)
    beta_c, beta_bg = _beta_style(beta)
    sharpe_c, sharpe_bg = _sharpe_style(sharpe)

    comparison = ""
    if total_return and market_return:
        index_name = _parse_kv(raw, "Market Index") or "S&P 500"
        comparison = f"{_esc(total_return)}% over the past year vs. {_esc(market_return)}% for the {_esc(index_name)} (market index)"

    tr_sign = "+" if _is_pos(total_return) else ""
    ar_sign = "+" if _is_pos(annualized) else ""

    body = f'''
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center"><span class="text-orange-600 text-lg">&#x1F4C8;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Price Performance &amp; Risk</h3>
          <p class="text-xs text-gray-500">Returns &amp; volatility metrics</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(perf_badge)}</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <div class="{tr_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Total Return</p>{_info_icon("Cumulative price return over the analysis period.")}</div>
        <p class="text-2xl font-bold {tr_c} mt-2">{tr_arrow}{tr_sign}{_esc(total_return) if total_return else "N/A"}%</p>
        <p class="text-xs text-gray-400 mt-1 leading-snug">{comparison}</p>
      </div>
      <div class="{ar_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Annualized Return</p>{_info_icon("Return normalized to a yearly rate for comparison across time periods.")}</div>
        <p class="text-2xl font-bold {ar_c} mt-2">{ar_sign}{_esc(annualized) if annualized else "N/A"}%</p>
      </div>

      <div class="{vol_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Volatility</p>{_info_icon("Annualized standard deviation of returns. Higher = more price swings.")}</div>
        <p class="text-2xl font-bold {vol_c} mt-2">{_esc(volatility) if volatility else "N/A"}%</p>
      </div>
      <div class="{beta_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Beta</p>{_info_icon("Sensitivity to market moves. 1.0 = moves with market, >1 = more volatile.")}</div>
        <p class="text-2xl font-bold {beta_c} mt-2">{_esc(beta) if beta else "N/A"}x</p>
      </div>

      <div class="{sharpe_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Sharpe Ratio</p>{_info_icon("Risk-adjusted return. Above 1.0 = good, above 2.0 = excellent.")}</div>
        <p class="text-2xl font-bold {sharpe_c} mt-2"><span class="text-gray-400 mr-1">&#x301C;</span>{_esc(sharpe) if sharpe else "N/A"}</p>
      </div>
      <div class="bg-white border border-red-300 border-l-4 border-l-red-500 rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Max Drawdown</p>{_info_icon("Largest peak-to-trough decline. Shows worst-case loss scenario.")}</div>
        <p class="text-2xl font-bold text-red-600 mt-2"><span class="text-red-500 mr-1">&#x2193;</span>{_esc(max_dd) if max_dd else "N/A"}%</p>
      </div>
    </div>

    <div class="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0"><span class="text-amber-600">&#x26A1;</span></div>
      <div>
        <p class="text-sm font-bold text-gray-800">Performance Insight</p>
        <p class="text-sm text-amber-800 mt-0.5">{_esc(insight) if insight else "Performance analysis completed."}</p>
      </div>
    </div>
    '''
    return _card(body, data_section="performance")
