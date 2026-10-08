# SPDX-License-Identifier: MIT
"""Final investment report card renderer."""

import re

from src.app.utils.formatters._shared import (
    _NOT_IDEAL_TEMPLATES,
    _SUITED_TEMPLATES,
    _badge_classes,
    _badge_icon,
    _card,
    _esc,
    _extract_verdict,
    _info_icon,
    _parse_kv,
    _parse_kv_all,
    _parse_sections,
    _verdict_colors,
    _verdict_dot_color,
    _verdict_icon,
)


def _render_report_cards(raw: str, symbol: str) -> str:
    verdict, confidence, cleaned = _extract_verdict(raw)
    sections = _parse_sections(cleaned)

    name = _parse_kv(raw, "Company Name") or symbol
    ticker = _parse_kv(raw, "Ticker") or symbol
    sector = _parse_kv(raw, "Sector") or ""
    segment = _parse_kv(raw, "Segment") or ""
    price = _parse_kv(raw, "Price (USD)") or _parse_kv(raw, "Price") or ""
    mcap = _parse_kv(raw, "Market Cap") or ""
    cap_size = _parse_kv(raw, "Cap Size") or ""
    summary = _parse_kv(raw, "Structured Summary") or ""

    vbg, vtxt = _verdict_colors(verdict)
    dot_color = _verdict_dot_color(verdict)
    vicon = _verdict_icon(verdict)
    conf_low = confidence.lower()
    if conf_low in ("n/a", "inconclusive", ""):
        conf_cls = "border-gray-300 text-gray-500"
    elif conf_low == "high":
        conf_cls = "border-green-400 text-green-700"
    elif conf_low == "medium":
        conf_cls = "border-yellow-400 text-yellow-700"
    else:
        conf_cls = "border-red-400 text-red-700"

    _agent_tag = re.compile(r"\s*\([^)]*analyst[^)]*\)", re.IGNORECASE)

    def _clean(items: list[str]) -> list[str]:
        return [_agent_tag.sub("", s).strip() for s in items]

    strengths = _clean(_parse_kv_all(raw, "Strength", limit=3))
    risks = _clean(_parse_kv_all(raw, "Risk", limit=3))
    suited = _clean(_parse_kv_all(raw, "Best Suited For", limit=2))

    tip_why = _esc("; ".join(strengths)) if strengths else "Strengths data not available."
    tip_who = _esc("; ".join(suited)) if suited else "Suitability data not available."
    tip_risk = _esc("; ".join(risks)) if risks else "Risk data not available."

    # ── Company Header Card ──
    company_header = f'''
    <div class="mb-3">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-3xl font-bold text-gray-900">{_esc(name)}</h2>
          <p class="text-base font-mono text-green-600 mt-0.5">{_esc(ticker)}</p>
        </div>
        <span class="px-4 py-1.5 rounded-full border border-gray-300 text-sm font-semibold text-gray-700">{_esc(cap_size) if cap_size else "N/A"}</span>
      </div>
      <div class="flex items-baseline gap-8 mt-4">
        <div>
          <p class="text-sm text-gray-500">Current Price</p>
          <p class="text-4xl font-bold text-gray-900">{_esc(price) if price else "N/A"}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Market Cap</p>
          <p class="text-xl font-bold text-gray-700">{_esc(mcap) if mcap else "N/A"}</p>
        </div>
      </div>
    </div>

    <div class="bg-slate-50 border border-gray-200 rounded-xl p-6 mt-4">
      <div class="flex items-center gap-2 mb-4">
        <span class="w-3 h-3 rounded-full {dot_color}"></span>
        <span class="text-sm font-bold text-gray-500 uppercase tracking-wider">Overall Verdict</span>
      </div>
      <div class="flex items-center gap-5 flex-wrap">
        <span class="inline-flex items-center gap-2.5 px-7 py-3 rounded-xl text-xl font-extrabold shadow-md {vbg} {vtxt}">
          {vicon} {_esc(verdict)}
        </span>
        <div>
          <p class="text-sm text-gray-500">Confidence Level</p>
          <span class="inline-block px-3 py-1 rounded border text-sm font-semibold {conf_cls}">{_esc(confidence)}</span>
        </div>
      </div>
      <div class="mt-5 border border-gray-200 rounded-lg p-4 bg-white">
        <p class="text-base text-gray-700 leading-relaxed">{_esc(summary) if summary else "Summary not available."}</p>
      </div>
      <div class="flex flex-wrap gap-2.5 mt-4">
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_why}">Why this verdict?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_who}">Who should invest?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_risk}">Key risks</span>
      </div>
    </div>

    <div class="flex items-center gap-4 mt-5 text-base">
      <span class="text-gray-500">Sector:</span>
      <span class="px-2.5 py-0.5 bg-gray-100 rounded text-sm font-semibold text-gray-700">{_esc(sector) if sector else "N/A"}</span>
      <span class="text-gray-500">Segment:</span>
      <span class="text-gray-700 text-sm">{_esc(segment) if segment else "N/A"}</span>
    </div>
    '''

    # ── Quick Answers Card ──
    qa_lines = sections.get("QUICK_ANSWERS", [])
    qa_data: dict[str, tuple[str, str]] = {}
    for line in qa_lines:
        for key in ("Good Business", "Financially Healthy", "Stock Risky", "Expensive"):
            if line.startswith(f"{key}:"):
                val_part = line.split(":", 1)[1].strip()
                if " | " in val_part:
                    badge, desc = val_part.split(" | ", 1)
                    qa_data[key] = (badge.strip(), desc.strip())
                else:
                    qa_data[key] = (val_part, "")

    def _qa_card(question: str, key: str, fallback_badge: str, fallback_desc: str) -> str:
        badge, desc = qa_data.get(key, (fallback_badge, fallback_desc))
        icon = _badge_icon(badge)
        bcls = _badge_classes(badge)
        return f"""
        <div class="bg-white border border-gray-200 rounded-xl p-4 relative">
          <div class="absolute top-3 right-3">{_info_icon()}</div>
          <p class="text-sm font-semibold text-gray-800 mb-2">{question}</p>
          <div class="flex items-center gap-2 mb-1.5">
            {icon}
            <span class="px-2 py-0.5 rounded text-xs font-bold {bcls}">{_esc(badge)}</span>
          </div>
          <p class="text-xs text-gray-500 leading-relaxed">{_esc(desc) if desc else ""}</p>
        </div>"""

    quick_answers = f"""
    <div class="flex items-center gap-2 mb-4">
      <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <div>
        <h3 class="text-lg font-bold text-gray-900">Quick Answers</h3>
        <p class="text-xs text-gray-500">Decision snapshot to help you decide</p>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-4">
      {_qa_card("Is this a good business?", "Good Business", "N/A", "Not enough data to answer.")}
      {_qa_card("Is the company financially healthy?", "Financially Healthy", "N/A", "Not enough data to answer.")}
      {_qa_card("Is the stock risky?", "Stock Risky", "N/A", "Not enough data to answer.")}
      {_qa_card("Is it expensive right now?", "Expensive", "N/A", "Not enough data to answer.")}
    </div>
    """

    # ── Final Guidance Card ──
    parsed_suited = _clean(_parse_kv_all(raw, "Best Suited For", limit=4))
    parsed_not_ideal = _clean(_parse_kv_all(raw, "Not Ideal For", limit=4))
    suited = (
        parsed_suited
        if parsed_suited
        else _SUITED_TEMPLATES.get(verdict, ["Insufficient data to determine suitability."])
    )
    not_ideal = (
        parsed_not_ideal
        if parsed_not_ideal
        else _NOT_IDEAL_TEMPLATES.get(verdict, ["Insufficient data to determine."])
    )

    strengths = [
        line.split(":", 1)[1].strip()
        for line in sections.get("OTHER", [])
        if line.lower().startswith("strength:")
    ]
    risks = [
        line.split(":", 1)[1].strip()
        for line in sections.get("OTHER", [])
        if line.lower().startswith("risk:")
    ]

    advice_own = _parse_kv(raw, "Guidance For Existing Holders") or ""
    advice_buy = _parse_kv(raw, "Guidance For New Buyers") or ""
    if not advice_own:
        advice_lines = [
            line.split(":", 1)[1].strip()
            for line in sections.get("OTHER", [])
            if line.lower().startswith("advice:")
        ]
        advice_own = advice_lines[0] if len(advice_lines) > 0 else ""
        advice_buy = advice_lines[1] if len(advice_lines) > 1 else ""

    suited_html = "".join(
        f'<div class="flex items-center gap-2 text-sm text-green-800"><span class="text-green-500 font-bold">&#10003;</span> {_esc(s)}</div>'
        for s in suited
    )
    not_ideal_html = "".join(
        f'<div class="flex items-center gap-2 text-sm text-red-700"><span class="text-red-500 font-bold">&#10007;</span> {_esc(n)}</div>'
        for n in not_ideal
    )

    final_guidance = f"""
    <div class="flex items-center gap-2 mb-5">
      <span class="text-xl">&#x1F3AF;</span>
      <h3 class="text-lg font-bold text-gray-900">Final Guidance</h3>
    </div>

    <div class="mb-4">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        <p class="text-sm font-bold text-gray-800">Best Suited For</p>
      </div>
      <div class="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
        {suited_html}
      </div>
    </div>

    <div class="mb-5">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
        <p class="text-sm font-bold text-gray-800">Not Ideal For</p>
      </div>
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
        {not_ideal_html}
      </div>
    </div>

    <div class="border border-gray-200 rounded-xl overflow-hidden">
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div class="flex items-center gap-2">
          <span class="text-lg">&#x1F4C8;</span>
          <h4 class="text-base font-bold text-gray-900">Final Recommendation</h4>
        </div>
        <span class="px-3 py-1 rounded text-xs font-bold {vbg} {vtxt}">{_esc(verdict)}</span>
      </div>
      <div class="p-4 space-y-3">
        <div class="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p class="text-sm font-bold text-gray-800 mb-1">&#x1F4CA; If you already own this stock:</p>
          <p class="text-sm text-gray-600">{_esc(advice_own) if advice_own else "Guidance not available."}</p>
        </div>
        <div class="bg-white border border-gray-100 rounded-lg p-4">
          <p class="text-sm font-bold text-gray-800 mb-1">&#x1F3AF; If you&#39;re considering buying today:</p>
          <p class="text-sm text-gray-600">{_esc(advice_buy) if advice_buy else "Guidance not available."}</p>
        </div>
      </div>
    </div>

    <div class="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <p class="text-xs text-yellow-800">
        <span class="font-bold">&#x26A0; Important Disclaimer:</span>
        <em>This analysis is for educational and informational purposes only. It is not personalized financial advice. Always do your own research, consider your financial situation, risk tolerance, and investment goals. Past performance does not guarantee future results. Consult a qualified financial advisor before making investment decisions.</em>
      </p>
    </div>
    """

    _ = quick_answers  # Kept for future optional use; hidden in wireframe-accurate layout.
    return _card(company_header, data_section="company-header") + _card(
        final_guidance, data_section="final-guidance"
    )
