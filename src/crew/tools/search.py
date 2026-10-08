# SPDX-License-Identifier: MIT
"""Web search tool using SerperDevTool for live news and market research."""

import logging
import os

from crewai.tools import BaseTool
from crewai_tools import SerperDevTool

logger = logging.getLogger(__name__)

SEARCH_TOOL_NAME = "search_the_internet_with_serper"
NOT_CONFIGURED_MESSAGE = (
    "Web search is not configured (no SERPER_API_KEY). Use the saved news.csv headlines instead."
)


class SearchUnavailableTool(BaseTool):
    """Stand-in used when no Serper key is set, so agents get a clear message, not an error."""

    name: str = SEARCH_TOOL_NAME
    description: str = (
        "Web search is currently unavailable. Calling this returns a notice; "
        "rely on locally saved news instead."
    )

    def _run(self, search_query: str = "") -> str:
        return NOT_CONFIGURED_MESSAGE


def create_search_tool() -> BaseTool:
    """Create the web search tool, or a graceful stand-in if no API key is set.

    Get a free key at https://serper.dev/ and set SERPER_API_KEY in .env.
    """
    if not os.getenv("SERPER_API_KEY"):
        logger.info("SERPER_API_KEY not set; web search disabled for this run")
        return SearchUnavailableTool()
    # Keep result volume compact to avoid large prompt payloads and TPM spikes.
    return SerperDevTool(n_results=3)
