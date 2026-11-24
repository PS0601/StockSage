# SPDX-License-Identifier: MIT
"""Deterministic checks that agent output stays faithful to the code-computed facts.

StockSage's design is "Python computes, agents interpret": every metric is computed in
``src/crew/facts.py`` and handed to the agents. These checks measure whether the agents
actually respect that contract:

* number grounding   - every number an agent writes must match a number in its facts
* blocked metrics    - ratios the data-sanity gate blocked must not be given a value
* contradictions     - text must not contradict the computed badges/verdicts
* schema validity    - output parsed into the task's Pydantic model (no raw fallback)

All functions are pure (no LLM, no network), so they are unit-tested in tests/evals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------- number extraction

_SCALE = {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9,
          "t": 1e12, "tn": 1e12, "trillion": 1e12}  # fmt: skip

_NUM_RE = re.compile(
    r"(?P<cur>[$₹€£])?\s?"
    r"(?P<num>(?:(?<![\w.])-)?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?:(?<![\w.])-)?\d+(?:\.\d+)?)"
    r"(?:\s?(?P<suf>%|x\b|×|bn\b|billion\b|million\b|trillion\b|mn\b|tn\b|[KMBT]\b))?",
    re.IGNORECASE,
)

# Numbers that are names or time spans, not metrics ("S&P 500", "52-week", "Q3", "FY2024").
_NOT_METRICS_RE = re.compile(
    r"S&P\s?500|NIFTY\s?50|NASDAQ[\s-]?100|Russell\s?2000|SENSEX|DOW\s?30|FTSE\s?100"
    r"|\b\d+[\s-]?(?:year|yr|month|mo|week|wk|day|quarter)s?\b"
    r"|\bQ[1-4]\b|\bFY\s?'?\d{2,4}\b|\b10-[KQ]\b|\bH[12]\b"
    r"|\b(?:19|20)\d{2}\b(?!\s?%)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Num:
    value: float  # as written, e.g. 135.5 for "$135.5B"
    absolute: float | None  # scaled to units when a scale/currency is present, e.g. 1.355e11
    decimals: int  # decimals shown, used as rounding tolerance
    kind: str  # "pct", "ratio", "money", "plain"
    text: str  # the matched text, for reports


def extract_numbers(text: str) -> list[Num]:
    """Pull metric-like numbers out of text, skipping years, index names and time spans."""
    cleaned = _NOT_METRICS_RE.sub(" ", text or "")
    out: list[Num] = []
    for m in _NUM_RE.finditer(cleaned):
        raw, cur, suf = m.group("num"), m.group("cur"), (m.group("suf") or "").lower()
        # skip digits glued to letters (e.g. "Q4", "H100", "ABC123")
        start = m.start("num")
        if start > 0 and cleaned[start - 1].isalpha():
            continue
        value = float(raw.replace(",", ""))
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        if suf == "%":
            kind = "pct"
        elif suf in ("x", "×"):
            kind = "ratio"
        elif cur or suf in _SCALE:
            kind = "money"
        else:
            kind = "plain"
        # bare small integers are almost always counts ("3 risks", "top 5")
        if kind == "plain" and decimals == 0 and abs(value) < 10:
            continue
        absolute = None
        if suf in _SCALE:
            absolute = value * _SCALE[suf]
        elif cur or abs(value) >= 1e5:
            absolute = value
        out.append(Num(value, absolute, decimals, kind, m.group(0).strip()))
    return out


def _close(a: float, f: float, decimals: int) -> bool:
    """True if ``a`` is ``f`` written with ``decimals`` decimals, or within 1%."""
    if abs(a - f) <= 0.5 * 10 ** (-decimals) + 1e-9:
        return True
    return f != 0 and abs(a - f) / abs(f) <= 0.01


def is_grounded(n: Num, facts: list[Num]) -> bool:
    """A number is grounded if some fact number matches it (sign may be dropped, e.g. a
    drawdown of -23.4% written as "a 23% drawdown")."""
    for f in facts:
        if n.absolute is not None and f.absolute is not None:
            if _close(abs(n.absolute), abs(f.absolute), 0) or (
                abs(f.absolute) > 0
                and abs(abs(n.absolute) - abs(f.absolute)) / abs(f.absolute) <= 0.01
            ):
                return True
        if _close(abs(n.value), abs(f.value), n.decimals):
            return True
    return False


def grounding(agent_text: str, facts_text: str) -> tuple[int, list[str]]:
    """Return (number count, ungrounded numbers) for agent text vs its facts."""
    facts = extract_numbers(facts_text)
    nums = extract_numbers(agent_text)
    bad = [n.text for n in nums if not is_grounded(n, facts)]
    return len(nums), bad


def _matches_exactly(n: Num, pool: list[Num]) -> bool:
    """Stricter than is_grounded (no 1% slack): used for big pools like raw CSV data, where
    loose matching would let random numbers match by coincidence. Fractions in the data
    (0.287) may be written as percentages (28.7%)."""
    for f in pool:
        if n.absolute is not None and f.absolute is not None and n.value:
            scale = n.absolute / n.value
            if (
                abs(abs(n.absolute) - abs(f.absolute))
                <= 0.5 * 10 ** (-n.decimals) * abs(scale) + 1e-9
            ):
                return True
        candidates = [f.value]
        if n.kind == "pct" and abs(f.value) <= 10:
            candidates.append(f.value * 100)
        if any(abs(abs(n.value) - abs(c)) <= 0.5 * 10 ** (-n.decimals) + 1e-9 for c in candidates):
            return True
    return False


def _is_derived(n: Num, operands: list[float]) -> bool:
    """True if n is simple arithmetic on two numbers from the same sentence:
    a/b, % premium (a/b - 1), difference, or % change. Allows the agent's rounding."""
    target = abs(n.value)
    operands = [abs(x) for x in operands]
    for a in operands:  # unit conversion of a single number: 0.60x beta -> "60% as much"
        if any(abs(v - target) <= 0.5 * 10 ** (-n.decimals) + 1e-9 for v in (a * 100, a / 100)):
            return True
    for a in operands:
        for b in operands:
            if a == b or b == 0:
                continue
            for v in (a / b, (a / b - 1) * 100, a - b, (a - b) / abs(b) * 100):
                v = abs(v)
                if abs(v - target) <= 0.5 * 10 ** (-n.decimals) + 1e-9 or (
                    v and abs(v - target) / v <= 0.02
                ):
                    return True
    return False


_SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")

SOURCES = ("facts", "data", "prompt", "derived", "unexplained")


def classify(agent_text: str, facts_text: str, data_text: str = "", prompt_text: str = "") -> dict:
    """Attribute every number in agent text to where it came from:
    facts (code-computed), data (raw CSVs the agent read), prompt (benchmarks written in
    the task prompt), derived (arithmetic on numbers in the same sentence) or unexplained."""
    facts, data, prompt = (
        extract_numbers(facts_text),
        extract_numbers(data_text),
        extract_numbers(prompt_text),
    )
    out: dict[str, list[str]] = {k: [] for k in SOURCES}
    out["unexplained_context"] = []
    for sentence in _SENTENCE_RE.split(agent_text or ""):
        explained: list[float] = []
        pending: list[Num] = []
        for n in extract_numbers(sentence):
            if is_grounded(n, facts):
                out["facts"].append(n.text)
            elif _matches_exactly(n, data):
                out["data"].append(n.text)
            elif _matches_exactly(n, prompt):
                out["prompt"].append(n.text)
            else:
                pending.append(n)
                continue
            explained.append(n.value)
        for n in pending:
            if _is_derived(n, explained):
                out["derived"].append(n.text)
            else:
                out["unexplained"].append(n.text)
                out["unexplained_context"].append(" ".join(sentence.split())[:220].rstrip())
    return out


# ---------------------------------------------------------------- blocked metrics

BLOCKED_PATTERNS = {
    "P/E Ratio": [r"(?<!forward )\bp/e\b", r"(?<!forward )price[- ]to[- ]earnings", r"\bpe ratio"],
    "Forward P/E": [r"forward p/?e\b", r"forward price[- ]to[- ]earnings"],
    "P/B Ratio": [r"\bp/b\b", r"price[- ]to[- ]book"],
    "P/S Ratio": [r"\bp/s\b", r"price[- ]to[- ]sales"],
    "EV/EBITDA": [r"\bev/ebitda\b"],
    "PEG Ratio": [r"\bpeg\b"],
    "ROE (%)": [r"\broe\b", r"return on equity"],
    "ROA (%)": [r"\broa\b", r"return on assets"],
    "Gross Margin (%)": [r"gross margin"],
}
_VALUE_AFTER = r"[^.;\n]{0,25}?(?<![\w/])-?\d+(?:\.\d+)?\s?(?:x|×|%)?"


# A sentence that reports the problem ("used PEG of 4.5x, which is blocked") is the review
# agent doing its job, not a violation.
_FLAGGING_RE = re.compile(
    r"blocked|violat|should not|shouldn't|not valid|invalid|sanity|excluded|disregard"
    r"|not meaningful|not applicable|meaningless"
)


def blocked_violations(agent_text: str, blocked_labels: set[str]) -> list[str]:
    """Sentences where a blocked metric is still given a numeric value."""
    hits = []
    for sentence in _SENTENCE_RE.split(agent_text or ""):
        low = sentence.lower()
        if _FLAGGING_RE.search(low):
            continue
        for label in sorted(blocked_labels):
            if any(re.search(pat + _VALUE_AFTER, low) for pat in BLOCKED_PATTERNS.get(label, [])):
                hits.append(f"{label}: '{' '.join(sentence.split())[:200]}'")
    return hits


# ---------------------------------------------------------------- contradictions

_NEGATION_RE = re.compile(
    r"(?:\bnot|n't|\bno|\bnever|\bwithout|\brather than|\bfar from|\baway from|\boutside)\W+(?:\S+\W+){0,3}$"
)


# "cash outperformed the stock" agrees with UNDERPERFORMING: something else is the subject.
_OTHER_SUBJECT_RE = re.compile(
    r"\b(?:cash|index|market|benchmark|nifty|s&p|sensex|peers?|bonds?|treasur\w*|sector)\W+(?:\S+\W+){0,1}$"
)


def _unnegated(pattern: str, text: str, check_subject: bool = False) -> list[str]:
    found = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        before = text[max(0, m.start() - 30) : m.start()].lower()
        if check_subject and _OTHER_SUBJECT_RE.search(before):
            continue
        if not _NEGATION_RE.search(before):
            found.append(" ".join(text[max(0, m.start() - 40) : m.end() + 20].split()))
    return found


def fact_value(facts_text: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}:\s*(.+)$", facts_text or "", re.MULTILINE)
    return m.group(1).strip() if m else None


def contradictions(agent_text: str, all_facts_text: str) -> list[str]:
    """Statements that contradict the computed performance badge, valuation verdict or
    health status. Negated mentions ("did not outperform") are allowed."""
    out = []
    badge = (fact_value(all_facts_text, "Performance Badge") or "").upper()
    if badge == "OUTPERFORMING":
        out += [
            f"badge OUTPERFORMING but: '{s}'"
            for s in _unnegated(r"\bunderperform\w*", agent_text, True)
        ]
    elif badge == "UNDERPERFORMING":
        out += [
            f"badge UNDERPERFORMING but: '{s}'"
            for s in _unnegated(r"\boutperform\w*", agent_text, True)
        ]

    verdict = (fact_value(all_facts_text, "Valuation Verdict") or "").lower()
    if verdict.startswith("yes"):  # trading above fair value
        out += [
            f"valuation ABOVE fair value but: '{s}'"
            for s in _unnegated(r"\bundervalued\b", agent_text)
        ]
    elif verdict.startswith("no"):  # trading below fair value
        out += [
            f"valuation BELOW fair value but: '{s}'"
            for s in _unnegated(r"\bovervalued\b", agent_text)
        ]

    health = (fact_value(all_facts_text, "Health Status") or "").upper()
    subject = r"(?:financial health|balance sheet|financials|financial position)"
    if health == "STRONG":
        pat = rf"\b(?:weak|poor|deteriorating|fragile)\s+{subject}"
        out += [f"health STRONG but: '{s}'" for s in _unnegated(pat, agent_text)]
    elif health == "WEAK":
        pat = rf"\b(?:strong|excellent|robust|solid)\s+{subject}"
        out += [f"health WEAK but: '{s}'" for s in _unnegated(pat, agent_text)]
    return out
