# SPDX-License-Identifier: MIT
"""Valuation & profitability card renderer."""

from src.app.utils.formatters._shared import (
    _card,
    _clean_line,
    _esc,
    _info_icon,
    _parse_kv,
)


def _render_valuation_card(raw: str, symbol: str) -> str:  # noqa: ARG001
    insight = _parse_kv(raw, "Insight") or ""

    val_verdict_line = _parse_kv(raw, "Valuation Verdict")
    val_answer = "Unknown"
    val_desc = ""
    if val_verdict_line and " | " in val_verdict_line:
        val_answer, val_desc = val_verdict_line.split(" | ", 1)
    elif val_verdict_line:
        val_answer = val_verdict_line

    is_expensive = val_answer.lower() in ("yes", "expensive", "overvalued")
    is_cheap = val_answer.lower() in ("no", "cheap", "undervalued")

    if is_expensive:
        badge_text, badge_cls = "OVERVALUED", "bg-red-100 text-red-700 border border-red-300"
    elif is_cheap:
        badge_text, badge_cls = "UNDERVALUED", "bg-green-100 text-green-700 border border-green-300"
    elif val_answer.lower() == "fair":
        badge_text, badge_cls = (
            "FAIR VALUE",
            "bg-yellow-100 text-yellow-700 border border-yellow-300",
        )
    else:
        # Unknown or missing verdict (e.g. no P/E because the company has losses).
        badge_text, badge_cls = (
            "INSUFFICIENT DATA",
            "bg-gray-100 text-gray-700 border border-gray-300",
        )

    pe = _parse_kv(raw, "P/E Ratio") or _parse_kv(raw, "P/E (x)")
    fwd_pe = _parse_kv(raw, "Forward P/E") or _parse_kv(raw, "Forward P/E (x)")
    pb = _parse_kv(raw, "P/B Ratio") or _parse_kv(raw, "P/B (x)")
    ps = _parse_kv(raw, "P/S Ratio") or _parse_kv(raw, "P/S (x)")
    peg = _parse_kv(raw, "PEG Ratio")
    ev_ebitda = _parse_kv(raw, "EV/EBITDA")

    def _val_style(val_str: str | None, high: float, low: float) -> tuple[str, str]:
        if not val_str:
            return "text-gray-900", "bg-white border border-gray-200"
        try:
            v = float(val_str.replace("x", "").replace(",", "").strip())
        except ValueError:
            return "text-gray-900", "bg-white border border-gray-200"
        if v >= high:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        if v <= low:
            return (
                "text-green-600",
                "bg-white border border-green-300 border-l-4 border-l-green-500",
            )
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    pe_c, pe_bg = _val_style(pe, 25, 12)
    fpe_c, fpe_bg = _val_style(fwd_pe, 25, 12)
    pb_c, pb_bg = _val_style(pb, 3, 1)
    ps_c, ps_bg = _val_style(ps, 5, 1)
    peg_c, peg_bg = _val_style(peg, 1.5, 0.8)
    ev_c, ev_bg = _val_style(ev_ebitda, 15, 8)

    def _metric_box(
        label: str,
        value: str | None,
        suffix: str,
        color: str,
        bg: str,
        tip: str = "",
        icon: str = "",
    ) -> str:
        v = value.rstrip(suffix).strip() if value else ""
        v = _esc(v) if v else "N/A"
        ic = f'<span class="text-gray-400 text-sm">{icon}</span>' if icon else ""
        return f'''<div class="{bg} rounded-xl p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">{label}</p>{_info_icon(tip)}</div>{ic}
          </div>
          <p class="text-2xl font-bold {color} mt-2">{v}<span class="text-sm font-semibold text-gray-400 ml-0.5">{suffix}</span></p>
        </div>'''

    implications = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("implication:"):
            implications.append(cl.split(":", 1)[1].strip())
    impl_html = (
        f"""<div class="flex items-start gap-2 mt-4 text-sm text-gray-600">
      <span class="font-bold text-gray-500">&#x1F4CA;</span>
      <p><span class="font-semibold">Implication:</span> {_esc(implications[0])}</p>
    </div>"""
        if implications
        else ""
    )

    body = f"""
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center"><span class="text-blue-600 text-lg">&#x1F4CA;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Valuation &amp; Profitability</h3>
          <p class="text-xs text-gray-500">Financial ratios &amp; metrics</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{badge_text}</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      {_metric_box("P/E Ratio", pe, "x", pe_c, pe_bg, "Price-to-Earnings: how much you pay per dollar of earnings. Lower = cheaper.")}
      {_metric_box("Forward P/E", fwd_pe, "x", fpe_c, fpe_bg, "Based on estimated future earnings. Lower = cheaper relative to growth.")}
      {_metric_box("P/B Ratio", pb, "x", pb_c, pb_bg, "Price-to-Book: stock price vs net asset value. Below 1 = trading below book value.")}
      {_metric_box("P/S Ratio", ps, "x", ps_c, ps_bg, "Price-to-Sales: what you pay per dollar of revenue. Useful for unprofitable companies.")}
      {_metric_box("PEG Ratio", peg, "x", peg_c, peg_bg, "P/E adjusted for growth. Below 1 = undervalued relative to growth rate.", "&#x1F4B2;")}
      {_metric_box("EV/EBITDA", ev_ebitda, "x", ev_c, ev_bg, "Enterprise value vs operating profit. Lower = cheaper on an operational basis.", "&#x1F4C8;")}
    </div>

    <div class="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0"><span class="text-amber-600">&#x1F4A1;</span></div>
      <div>
        <p class="text-sm font-bold text-gray-800">Valuation Insight</p>
        <p class="text-sm text-amber-800 mt-0.5">{_esc(insight or val_desc or "Valuation analysis completed.")}</p>
      </div>
    </div>

    {impl_html}
    """
    return _card(body, data_section="valuation")
