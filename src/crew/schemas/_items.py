# SPDX-License-Identifier: MIT
"""Shared Pydantic item models used across multiple output schemas.

Keyword-based content validators (evidence regex, comparative note checks) have
been removed to let LLM output pass through.  The strict versions are preserved
in ``_base.py`` / ``_constants.py`` for future re-enablement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ApplicabilityItem(BaseModel):
    """Ratio or valuation-model applicability entry for DataSanityOutput."""

    name: str = Field(min_length=1)
    status: Literal["VALID", "SOFT_BLOCKED", "HARD_BLOCKED", "NOT_APPLICABLE"]
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


class MetricItem(BaseModel):
    """A single labelled metric with optional comparative note and source."""

    label: str
    value: str
    note: str = ""
    source: str = ""


class CitationItem(BaseModel):
    """News or source citation attached to an output schema."""

    title: str = ""
    publisher: str = ""
    url: str = ""
