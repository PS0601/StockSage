# SPDX-License-Identifier: MIT
"""Grounding eval: run the real 6-agent crew on a fixed set of tickers and grade every
agent's output against the code-computed facts it was given.

    uv run python -m evals.run_grounding_eval                       # default tickers, 2 runs each
    uv run python -m evals.run_grounding_eval --tickers AAPL KO --runs 3
    uv run python -m evals.run_grounding_eval --refresh             # re-download market data

Writes evals/results.md and evals/results.json. Uses the LLM configured in .env.
Market data is downloaded once and reused, so repeated runs grade the same inputs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.grounding import SOURCES, blocked_violations, classify, contradictions

DEFAULT_TICKERS = ["AAPL", "JPM", "KO", "TSLA", "RELIANCE.NS"]
OUT_DIR = Path(__file__).resolve().parent

# Which facts each task is graded against. Review and final report see everything.
_SENTIMENT = "analyze_market_sentiment"
_ALL = "__all__"
FACTS_FOR = {
    "analyze_valuation_ratios": ["analyze_valuation_ratios"],
    "analyze_price_performance": ["analyze_price_performance"],
    "analyze_financial_health": ["analyze_financial_health"],
    _SENTIMENT: [_SENTIMENT],
    "review_analysis": [_ALL],
    "generate_investment_report": [_ALL],
}


def _text_of(model: Any, raw: str) -> str:
    """All agent-written text in a task output (citations excluded: they quote sources)."""
    if model is None:
        return raw
    parts: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            if "label" in v and "value" in v:  # a metric: keep label and value on one line
                parts.append(f"{v['label']}: {v['value']} - {v.get('note', '')}")
                return
            for item in v.values():
                walk(item)
        elif isinstance(v, list):
            for item in v:
                walk(item)

    walk(model.model_dump(exclude={"citations"}))
    return "\n".join(parts)


def ensure_data(symbol: str, refresh: bool) -> str:
    from src.core.config.data_contracts import DATA_DIR
    from src.core.processing.download_pipeline import DownloadPipeline

    folder = DATA_DIR / symbol.upper()
    if refresh or not folder.exists() or not any(folder.iterdir()):
        print(f"  downloading data for {symbol}...")
        for _ in DownloadPipeline(symbol).run():
            pass
    if not folder.exists():
        raise RuntimeError(f"no data downloaded for {symbol}")
    newest = max(p.stat().st_mtime for p in folder.iterdir())
    return datetime.fromtimestamp(newest).strftime("%Y-%m-%d")


# Daily price files have hundreds of rows; keeping them all would let almost any price-like
# number match by coincidence, so only their header and first/last rows are used.
_LONG_FILES = {"daily.csv", "historical_prices.csv", "market_index.csv", "sector_index.csv"}
_SKIP_FILES = {"google_trends.csv"}  # 0-100 interest scores would match almost anything


def data_text(symbol: str) -> str:
    """The raw CSV data the agents can read with their csv_reader tool."""
    from src.core.config.data_contracts import DATA_DIR

    parts = []
    for path in sorted((DATA_DIR / symbol.upper()).glob("*.csv")):
        if path.name in _SKIP_FILES:
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if path.name in _LONG_FILES and len(lines) > 7:
            lines = lines[:4] + lines[-3:]
        parts.append("\n".join(lines))
    return "\n".join(parts)


def prompt_text() -> str:
    """Task and agent prompts: any benchmark numbers written there (e.g. "~22x")."""
    folder = Path(__file__).resolve().parent.parent / "src" / "crew" / "config"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(folder.glob("*.yaml")))


def prepare(symbol: str) -> tuple[dict[str, str], str, set[str]]:
    """Facts exactly as the app gives them to the agents, plus the blocked ratio labels."""
    from src.crew.facts import build_task_facts
    from src.crew.pipeline import _build_crew_inputs
    from src.crew.sanity import _FACT_LABELS, build_data_sanity_report, mask_blocked_metrics
    from src.crew.structured_output import serialize_structured_output

    facts = build_task_facts(symbol)
    report = build_data_sanity_report(symbol)
    facts["analyze_valuation_ratios"] = mask_blocked_metrics(
        facts.get("analyze_valuation_ratios", ""), report
    )
    sanity_text = serialize_structured_output("validate_data_sanity", report)
    inputs = _build_crew_inputs(symbol, facts, sanity_text)
    blocked = {
        _FACT_LABELS[i.name]
        for i in report.ratio_applicability
        if i.status != "VALID" and i.name in _FACT_LABELS
    }
    return inputs, sanity_text, blocked


def run_crew(inputs: dict[str, str]) -> list[tuple[str, Any, str]]:
    from src.crew.crew import StockAnalysisCrew
    from src.crew.pipeline import _raw_text
    from src.crew.structured_output import validate_task_output

    result = StockAnalysisCrew().crew().kickoff(inputs=inputs)
    out = []
    for t in getattr(result, "tasks_output", None) or []:
        name = getattr(t, "name", None) or ""
        out.append((name, validate_task_output(name, t), _raw_text(t)))
    return out


def grade_run(
    symbol: str,
    inputs: dict[str, str],
    blocked: set[str],
    tasks: list,
    data: str = "",
    prompts: str = "",
) -> dict:
    all_facts = "\n".join(v for k, v in inputs.items() if k.endswith("_facts"))
    rec: dict[str, Any] = {"symbol": symbol, "tasks": {}, "verdict": None, "confidence": None}
    for name, model, raw in tasks:
        text = _text_of(model, raw)
        scope = FACTS_FOR.get(name, [_ALL])
        facts_text = (
            all_facts if scope == [_ALL] else "\n".join(inputs.get(f"{s}_facts", "") for s in scope)
        )
        sources = classify(text, facts_text, data, prompts)
        rec["tasks"][name] = {
            "schema_valid": model is not None,
            "numbers": sum(len(v) for v in sources.values()),
            "sources": sources,
            "ungrounded": sources["unexplained"],
            "blocked_violations": blocked_violations(text, blocked),
            "contradictions": contradictions(text, all_facts),
        }
        if name == "generate_investment_report" and model is not None:
            rec["verdict"] = getattr(model, "verdict", None)
            rec["confidence"] = getattr(model, "confidence", None)
    return rec


def _pct(n: float, d: float) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def report(records: list[dict], meta: dict) -> str:
    ok = [r for r in records if not r.get("error")]
    tasks = [(r["symbol"], n, t) for r in ok for n, t in r["tasks"].items()]
    graded = [(s, n, t) for s, n, t in tasks if n != _SENTIMENT]
    sent = [(s, n, t) for s, n, t in tasks if n == _SENTIMENT]
    nums = sum(t["numbers"] for _, _, t in graded)
    bad = sum(len(t["ungrounded"]) for _, _, t in graded)
    by_source = {k: sum(len(t["sources"][k]) for _, _, t in graded) for k in SOURCES}
    s_nums = sum(t["numbers"] for _, _, t in sent)
    s_bad = sum(len(t["ungrounded"]) for _, _, t in sent)
    valid = sum(t["schema_valid"] for _, _, t in tasks)
    blocked = [(s, n, v) for s, n, t in tasks for v in t["blocked_violations"]]
    contra = [(s, n, c) for s, n, t in tasks for c in t["contradictions"]]
    lat = [r["latency_s"] for r in ok]

    by_sym: dict[str, list[dict]] = {}
    for r in ok:
        by_sym.setdefault(r["symbol"], []).append(r)
    stable = sum(len({r["verdict"] for r in rs}) == 1 for rs in by_sym.values() if len(rs) > 1)
    multi = sum(len(rs) > 1 for rs in by_sym.values())

    lines = [
        "# Grounding eval",
        "",
        f"Run on {datetime.now():%Y-%m-%d %H:%M} · model `{meta['model']}` · "
        f"{len(meta['tickers'])} tickers × {meta['runs']} runs = {len(records)} crew runs"
        + (f" · **{len(records) - len(ok)} failed**" if len(ok) < len(records) else ""),
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| **Unexplained numbers** (no source found: hallucination candidates) "
        f"| **{bad}/{nums} ({_pct(bad, nums)})**, lower is better |",
        f"| Numbers with a source | {nums - bad}/{nums} ({_pct(nums - bad, nums)}) |",
        f"| Sentiment agent: numbers with a source (web search results can't be checked) "
        f"| {s_nums - s_bad}/{s_nums} ({_pct(s_nums - s_bad, s_nums)}) |",
        f"| Blocked ratios given a value anyway | {len(blocked)} (lower is better) |",
        f"| Contradictions with computed badge / valuation / health | {len(contra)} (lower is better) |",
        f"| Outputs that parsed into the task schema | {valid}/{len(tasks)} ({_pct(valid, len(tasks))}) |",
        f"| Same verdict on every run | {stable}/{multi} tickers |",
        f"| Crew run time | median {statistics.median(lat):.0f}s · max {max(lat):.0f}s |"
        if lat
        else "| Crew run time | n/a |",
        "",
        "## Where the numbers came from (all agents except sentiment)",
        "",
        "| Source | Numbers | Share |",
        "|---|---|---|",
        *[
            f"| {label} | {by_source[k]} | {_pct(by_source[k], nums)} |"
            for k, label in [
                ("facts", "Computed facts (facts.py)"),
                ("data", "Raw data the agent read (CSVs)"),
                ("prompt", "Benchmark written in the prompt"),
                ("derived", "Derived: arithmetic on numbers in the same sentence"),
                ("unexplained", "**Unexplained**"),
            ]
        ],
        "",
        "## Per ticker",
        "",
        "| Ticker | Data as of | Verdicts (confidence) | Numbers with a source | Blocked | Contradictions |",
        "|---|---|---|---|---|---|",
    ]
    for sym, rs in by_sym.items():
        g = [t for r in rs for n, t in r["tasks"].items() if n != _SENTIMENT]
        n_, b_ = sum(t["numbers"] for t in g), sum(len(t["ungrounded"]) for t in g)
        verdicts = ", ".join(f"{r['verdict']} ({r['confidence']})" for r in rs)
        lines.append(
            f"| {sym} | {rs[0]['data_as_of']} | {verdicts} | {n_ - b_}/{n_} | "
            f"{sum(len(t['blocked_violations']) for r in rs for t in r['tasks'].values())} | "
            f"{sum(len(t['contradictions']) for r in rs for t in r['tasks'].values())} |"
        )
    per_task: Counter[str] = Counter()
    per_task_total: Counter[str] = Counter()
    for _, n, t in tasks:
        per_task[n] += len(t["ungrounded"])
        per_task_total[n] += t["numbers"]
    lines += [
        "",
        "## Unexplained numbers by agent task",
        "",
        "| Task | Unexplained / numbers |",
        "|---|---|",
    ]
    lines += [f"| {n} | {per_task[n]}/{per_task_total[n]} |" for n in per_task_total]

    seen: set[tuple[str, str, str]] = set()
    examples = []
    for sym_, task_, t in graded:
        for x, ctx in zip(t["ungrounded"], t["sources"].get("unexplained_context", [])):
            if (sym_, task_, x) not in seen:
                seen.add((sym_, task_, x))
                examples.append((sym_, task_, f"{x}` in: {ctx}"))
    examples = examples[:25]
    prompt_nums = sorted({x for _, _, t in graded for x in t["sources"]["prompt"]})
    if prompt_nums:
        lines += [
            "",
            "## Numbers taken from benchmarks written in the prompt",
            "",
            "These are static values in `src/crew/config/tasks.yaml`, not live data: "
            + ", ".join(f"`{x}`" for x in prompt_nums),
        ]
    if examples:
        lines += ["", "## Unexplained numbers to read", ""]
        lines += [f"- {s} · {n}: `{x}" for s, n, x in examples]
    if blocked:
        lines += ["", "## Blocked-ratio violations", ""] + [
            f"- {s} · {n}: {v}" for s, n, v in blocked[:10]
        ]
    if contra:
        lines += ["", "## Contradictions", ""] + [f"- {s} · {n}: {c}" for s, n, c in contra[:10]]
    errors = [r for r in records if r.get("error")]
    if errors:
        lines += ["", "## Failed runs", ""] + [
            f"- {r['symbol']}: {r['error'][:200]}" for r in errors
        ]
    lines += [
        "",
        "Unexplained does not always mean wrong (e.g. a number from general knowledge, or "
        "arithmetic across sentences). Read the examples before drawing conclusions.",
    ]
    # no trailing whitespace: the repo's pre-commit hooks reject it
    return "\n".join(line.rstrip() for line in lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--refresh", action="store_true", help="re-download market data first")
    args = ap.parse_args(argv)

    from src.core.config.config import LLM_MODEL

    records: list[dict] = []
    prompts = prompt_text()
    for sym in args.tickers:
        print(f"{sym}:")
        try:
            as_of = ensure_data(sym, args.refresh)
            inputs, _, blocked = prepare(sym)
            data = data_text(sym)
        except Exception as e:  # keep going with the other tickers
            records.append({"symbol": sym, "error": f"data: {e}"})
            print(f"  data failed: {e}")
            continue
        for i in range(args.runs):
            start = time.perf_counter()
            try:
                rec = grade_run(sym, inputs, blocked, run_crew(inputs), data, prompts)
            except Exception as e:
                rec = {"symbol": sym, "error": str(e)}
            rec["latency_s"] = round(time.perf_counter() - start, 1)
            rec["data_as_of"] = as_of
            rec["run"] = i + 1
            records.append(rec)
            summary = "ERROR" if rec.get("error") else f"verdict {rec['verdict']}"
            print(f"  run {i + 1}: {summary} ({rec['latency_s']}s)")

    meta = {"model": LLM_MODEL, "tickers": args.tickers, "runs": args.runs}
    md = report(records, meta)
    (OUT_DIR / "results.md").write_text(md, encoding="utf-8")
    (OUT_DIR / "results.json").write_text(
        json.dumps({"meta": meta, "records": records}, indent=2) + "\n", encoding="utf-8"
    )
    print("\n" + md)


if __name__ == "__main__":
    sys.exit(main())
