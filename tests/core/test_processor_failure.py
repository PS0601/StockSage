# SPDX-License-Identifier: MIT
"""A rejected symbol must end with COMPLETE + FAILED so the UI can show the reason."""

import asyncio

from src.core.config.enums import ProcessingStage, StatusType
from src.core.processing.processor import StockProcessor


def test_invalid_symbol_ends_with_visible_failure() -> None:
    async def collect() -> list:
        return [entry async for entry in StockProcessor("!!!").run()]

    last = asyncio.run(collect())[-1]

    assert last.stage == ProcessingStage.COMPLETE
    assert last.status_type == StatusType.FAILED
    assert last.message
