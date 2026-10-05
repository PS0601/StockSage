# SPDX-License-Identifier: MIT
"""Analysis pipeline that bridges CrewAI execution with the LogEntry streaming system."""

import asyncio
import logging
import random
import re
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.crew.facts import build_task_facts
from src.crew.structured_output import (
    serialize_structured_output,
    validate_task_output,
)

_TASK_SUBSTAGE_MAP = {
    "validate_data_sanity": SubStage.VALIDATING_DATA_SANITY,
    "analyze_valuation_ratios": SubStage.ANALYZING_VALUATION_RATIOS,
    "analyze_price_performance": SubStage.ANALYZING_PRICE_PERFORMANCE,
    "analyze_financial_health": SubStage.ANALYZING_FINANCIAL_HEALTH,
    "analyze_market_sentiment": SubStage.ANALYZING_MARKET_SENTIMENT,
    "review_analysis": SubStage.REVIEWING_ANALYSIS,
    "generate_investment_report": SubStage.GENERATING_INVESTMENT_REPORT,
}
_RATE_LIMIT_WAIT_RE = re.compile(r"Please try again in ([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)
_MAX_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_JITTER_SECONDS = (0.2, 0.8)
logger = logging.getLogger(__name__)


def _extract_retry_wait(error: Exception) -> float:
    match = _RATE_LIMIT_WAIT_RE.search(str(error))
    return float(match.group(1)) if match else 2.0


def _is_rate_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return "rate_limit_exceeded" in msg or "rate limit reached" in msg


def _raw_text(task_output: Any) -> str:
    raw = getattr(task_output, "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return str(task_output).strip()


_SKIP_SECTIONS = {"INSIGHT", "RECOMMENDATION", "QUICK_ANSWERS", "MARKET PULSE"}
_SKIP_PREFIXES = ("CHART_DATA", "Peers:")


def _is_section_header(line: str) -> bool:
    text = line.strip().rstrip(":")
    return bool(text) and text.isupper()


def _build_crew_inputs(symbol: str, facts: dict[str, str]) -> dict[str, str]:
    """Pass verified, code-computed metrics to the agents as task inputs."""
    inputs = {"symbol": symbol}
    for task_name, text in facts.items():
        lines = []
        skipping = False
        for line in text.splitlines():
            if _is_section_header(line):
                skipping = line.strip().rstrip(":") in _SKIP_SECTIONS
            if skipping or line.startswith(_SKIP_PREFIXES):
                continue
            lines.append(line)
        inputs[f"{task_name}_facts"] = "\n".join(lines).strip() or "No verified facts available."
    return inputs


class AnalysisPipeline:
    """Runs the CrewAI stock analysis crew and yields LogEntry objects for UI streaming."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.success: bool = False

    def _log(
        self, substage: SubStage | None, status: StatusType, message: str | None = None
    ) -> LogEntry:
        return LogEntry(
            stage=ProcessingStage.ANALYZING,
            substage=substage,
            status_type=status,
            message=message,
            symbol=self.symbol,
        )

    def _safe_failure_message(self, error: Exception) -> str:
        ref = uuid4().hex[:8]
        logger.exception("Analysis failed for %s (ref=%s)", self.symbol, ref, exc_info=error)
        return f"Analysis failed. See server logs (ref: {ref})."

    def _build_success_text(
        self, task_name: str, task_output: Any, deterministic_facts: dict[str, str]
    ) -> str:
        """Validate, serialize, and enrich a single task's output."""
        structured_model = validate_task_output(task_name, task_output)
        output_text = (
            serialize_structured_output(task_name, structured_model)
            if structured_model
            else _raw_text(task_output)
        )
        facts_text = deterministic_facts.get(task_name or "", "")
        if facts_text:
            output_text = f"{facts_text}\n\n{output_text}" if output_text else facts_text
        return output_text

    async def run(self) -> AsyncGenerator[LogEntry, None]:
        """Execute the analysis crew, yielding progress entries. Sets self.success."""
        yield self._log(None, StatusType.IN_PROGRESS, "Starting AI-powered analysis...")

        try:
            from src.crew.crew import StockAnalysisCrew

            crew = StockAnalysisCrew().crew()
            task_names = [
                getattr(t, "name", None) or f"task_{i}" for i, t in enumerate(crew.tasks, 1)
            ]
            total = len(task_names)
            completed = 0
            loop = asyncio.get_running_loop()
            deterministic_facts = build_task_facts(self.symbol)

            progress_q: asyncio.Queue[tuple[str, str, Any]] = asyncio.Queue()

            def on_task_done(task_output: Any) -> None:
                nonlocal completed
                done_name = task_names[completed]
                completed += 1
                loop.call_soon_threadsafe(progress_q.put_nowait, ("done", done_name, task_output))
                if completed < total:
                    loop.call_soon_threadsafe(
                        progress_q.put_nowait, ("start", task_names[completed], None)
                    )

            crew.task_callback = on_task_done

            result = None
            rate_limit_retries = 0
            started_substages: set[SubStage] = set()
            completed_substages: set[SubStage] = set()

            while True:
                try:
                    if task_names:
                        await progress_q.put(("start", task_names[0], None))

                    kickoff_task = asyncio.create_task(
                        crew.kickoff_async(inputs=_build_crew_inputs(self.symbol, deterministic_facts))
                    )

                    while not kickoff_task.done() or not progress_q.empty():
                        try:
                            event, task_name, task_output = await asyncio.wait_for(
                                progress_q.get(), timeout=0.2
                            )
                        except asyncio.TimeoutError:
                            continue

                        substage = _TASK_SUBSTAGE_MAP.get(task_name)
                        if not substage:
                            continue

                        if event == "start":
                            if substage not in started_substages:
                                started_substages.add(substage)
                                yield self._log(
                                    substage,
                                    StatusType.IN_PROGRESS,
                                    f"{substage.display_name}...",
                                )
                        elif event == "done":
                            output_text = self._build_success_text(
                                task_name, task_output, deterministic_facts
                            )
                            if output_text:
                                if substage not in started_substages:
                                    yield self._log(substage, StatusType.IN_PROGRESS)
                                    started_substages.add(substage)
                                yield self._log(substage, StatusType.SUCCESS, output_text)
                                completed_substages.add(substage)

                    result = await kickoff_task
                    break

                except Exception as exc:
                    if _is_rate_limit_error(exc) and rate_limit_retries < _MAX_RATE_LIMIT_RETRIES:
                        wait = _extract_retry_wait(exc) + random.uniform(
                            *_RATE_LIMIT_JITTER_SECONDS
                        )
                        rate_limit_retries += 1
                        yield self._log(
                            None,
                            StatusType.IN_PROGRESS,
                            f"Rate limit hit. Retrying in {wait:.1f}s ({rate_limit_retries}/{_MAX_RATE_LIMIT_RETRIES})...",
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise

            if result is None:
                raise RuntimeError("Crew returned no result")

            # Safety net: yield any tasks the callback/queue race may have missed
            for task_output in getattr(result, "tasks_output", None) or []:
                task_name_str: str = getattr(task_output, "name", None) or ""
                substage = _TASK_SUBSTAGE_MAP.get(task_name_str)
                if not substage or substage in completed_substages:
                    continue

                output_text = self._build_success_text(
                    task_name_str, task_output, deterministic_facts
                )
                if not output_text:
                    continue
                if substage not in started_substages:
                    yield self._log(substage, StatusType.IN_PROGRESS)
                yield self._log(substage, StatusType.SUCCESS, output_text)

            if not getattr(result, "tasks_output", None):
                report_facts = deterministic_facts.get("generate_investment_report", "")
                raw_output = str(result).strip()
                output_text = f"{report_facts}\n\n{raw_output}" if report_facts else raw_output
                yield self._log(
                    SubStage.GENERATING_INVESTMENT_REPORT, StatusType.SUCCESS, output_text
                )

            self.success = True

        except Exception as exc:
            yield self._log(None, StatusType.FAILED, self._safe_failure_message(exc))
            self.success = False
