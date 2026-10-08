# SPDX-License-Identifier: MIT
"""Tests for the web search tool factory."""

import pytest

from src.crew.tools.search import (
    NOT_CONFIGURED_MESSAGE,
    SEARCH_TOOL_NAME,
    SearchUnavailableTool,
    create_search_tool,
)


def test_missing_key_returns_graceful_stand_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    tool = create_search_tool()

    assert isinstance(tool, SearchUnavailableTool)
    assert tool.name == SEARCH_TOOL_NAME
    assert tool.run(search_query="AAPL news") == NOT_CONFIGURED_MESSAGE


def test_key_present_returns_real_serper_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    tool = create_search_tool()

    assert not isinstance(tool, SearchUnavailableTool)
