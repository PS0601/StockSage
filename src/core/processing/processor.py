# SPDX-License-Identifier: MIT
"""Stock symbol processing pipeline."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import TypeVar

from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry
from src.core.processing.download_pipeline import DownloadPipeline
from src.core.validation.validation import validate_symbol

_ACTIVE_LOCK = asyncio.Lock()

_T = TypeVar("_T")

_SYNC_GEN_DONE = object()


async def _stream_sync_gen(gen: Generator[_T, None, object]) -> AsyncGenerator[_T, None]:
    """Bridge a sync generator to async, running it in the default executor."""
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def drain() -> None:
        try:
            for item in gen:
                loop.call_soon_threadsafe(q.put_nowait, item)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, _SYNC_GEN_DONE)

    fut = loop.run_in_executor(None, drain)
    while True:
        item = await q.get()
        if item is _SYNC_GEN_DONE:
            break
        yield item
    await fut


class StockProcessor:
    """Orchestrates the full processing pipeline for a stock symbol.

    Pipeline stages: validate -> download -> analyze.
    Each stage yields LogEntry objects for real-time UI streaming.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def _log(
        self,
        stage: ProcessingStage,
        substage: SubStage | None = None,
        status: StatusType = StatusType.IN_PROGRESS,
        message: str | None = None,
    ) -> LogEntry:
        return LogEntry(
            stage=stage, substage=substage, status_type=status, message=message, symbol=self.symbol
        )

    def _validate(self) -> Generator[LogEntry, None, bool]:
        """Validate the stock symbol format and existence (sync — fast, no I/O)."""
        yield self._log(ProcessingStage.VALIDATING)
        yield self._log(ProcessingStage.VALIDATING, SubStage.VALIDATING_SYMBOL)

        result = validate_symbol(self.symbol)
        if not result.is_valid:
            yield self._log(
                ProcessingStage.VALIDATING,
                SubStage.VALIDATING_SYMBOL,
                StatusType.FAILED,
                result.error_message,
            )
            return False

        yield self._log(ProcessingStage.VALIDATING, SubStage.VALIDATING_SYMBOL, StatusType.SUCCESS)
        return True

    async def _download(self) -> AsyncGenerator[LogEntry, None]:
        """Download all market data for the symbol, streaming progress entries."""
        yield self._log(ProcessingStage.DOWNLOADING_DATA)

        pipeline = DownloadPipeline(self.symbol)
        async for entry in _stream_sync_gen(pipeline.run()):
            yield entry

        self._download_ok = pipeline.critical_ok

    async def _analyze(self) -> AsyncGenerator[LogEntry, None]:
        """Run CrewAI-powered analysis on downloaded data."""
        from src.crew.pipeline import AnalysisPipeline

        self._pipeline = AnalysisPipeline(self.symbol)
        async for entry in self._pipeline.run():
            yield entry

    async def run(self) -> AsyncGenerator[LogEntry, None]:
        """Execute the full pipeline: validate -> download -> analyze."""
        if _ACTIVE_LOCK.locked():
            yield self._log(
                ProcessingStage.COMPLETE,
                status=StatusType.FAILED,
                message=(
                    "Another analysis is already running on this instance. "
                    "Please wait a moment and retry."
                ),
            )
            return

        async with _ACTIVE_LOCK:
            yield self._log(ProcessingStage.STARTING, message=f"Processing symbol: {self.symbol}")

            # The UI only shows an error for COMPLETE + FAILED entries; without one, a
            # failed validation or download ends as a normal "complete" and the page goes blank.
            failure = ""
            for entry in self._validate():
                yield entry
                if entry.status_type == StatusType.FAILED:
                    failure = entry.message or f"{self.symbol} is not a valid symbol"
            if failure:
                yield self._log(ProcessingStage.COMPLETE, status=StatusType.FAILED, message=failure)
                return

            self._download_ok = True
            async for entry in self._download():
                yield entry
                if entry.status_type == StatusType.FAILED and entry.message:
                    failure = entry.message
            if not self._download_ok:
                yield self._log(
                    ProcessingStage.COMPLETE,
                    status=StatusType.FAILED,
                    message=failure or f"Could not download data for {self.symbol}",
                )
                return

            async for entry in self._analyze():
                yield entry
            if not self._pipeline.success:
                yield self._log(
                    ProcessingStage.COMPLETE,
                    status=StatusType.FAILED,
                    message=f"Analysis failed for {self.symbol}",
                )
                return

            yield self._log(
                ProcessingStage.COMPLETE, message=f"Successfully processed {self.symbol}"
            )
