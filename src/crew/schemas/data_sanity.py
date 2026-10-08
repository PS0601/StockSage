# SPDX-License-Identifier: MIT
"""DataSanityOutput — validates data completeness before analysis begins."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import (
    coerce_summary_text,
    normalize_payload_lists,
)
from src.crew.schemas._constants import (
    CORE_DATA_FILES,
    DATA_SANITY_SUMMARY_RE,
    FILE_LEVEL_ISSUE_RE,
    FILE_STATUS_RE,
)
from src.crew.schemas._items import ApplicabilityItem


class DataSanityOutput(BaseModel):
    """Structured output for the data-sanity gate task."""

    summary: str = Field(min_length=1)
    gate_status: Literal["PASS", "PASS_WITH_SKIPS", "FAIL"]
    market_context: Literal["US", "India"] = "US"
    company_type: Literal["Bank", "Financial", "Non-Financial"] = "Non-Financial"
    validated_files: list[str] = Field(default_factory=list)
    missing_or_invalid_files: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ratio_applicability: list[ApplicabilityItem] = Field(default_factory=list)
    valuation_model_applicability: list[ApplicabilityItem] = Field(default_factory=list)

    # ── Pre-normalisation ──────────────────────────────────────────────────

    @model_validator(mode="before")
    @classmethod
    def _normalize_common_data_sanity_shapes(cls, value: object) -> object:
        """[model_validator mode=before] Build deterministic file lists and gate status.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: coerces summary to counts-only format, computes gate_status
        from hard/soft block counts, replaces validated/missing file lists with
        filesystem-based truth when the active symbol is known, and normalises
        critical_issues / warnings to ``file -> issue`` format.  Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)

        ratios = payload.get("ratio_applicability") or []
        models = payload.get("valuation_model_applicability") or []
        statuses: list[str] = []
        for item in [*ratios, *models]:
            if isinstance(item, dict):
                statuses.append(str(item.get("status", "")).strip().upper())

        hard_count = sum(1 for s in statuses if s == "HARD_BLOCKED")
        soft_count = sum(1 for s in statuses if s == "SOFT_BLOCKED")

        summary_text = coerce_summary_text(
            payload.get("summary"),
            fallback=f"{hard_count} hard blocks, {soft_count} soft blocks identified",
        )
        payload["summary"] = summary_text
        if not DATA_SANITY_SUMMARY_RE.fullmatch(summary_text):
            payload["summary"] = f"{hard_count} hard blocks, {soft_count} soft blocks identified"

        # Gate = is the core data present? Blocked metrics are skips, not failures.
        missing = " ".join(str(f) for f in payload.get("missing_or_invalid_files") or [])
        if any(name in missing for name in CORE_DATA_FILES):
            payload["gate_status"] = "FAIL"
        elif hard_count > 0 or soft_count > 0:
            payload["gate_status"] = "PASS_WITH_SKIPS"
        else:
            payload["gate_status"] = "PASS"

        payload["validated_files"] = _normalize_file_statuses(
            payload.get("validated_files"), default_status="ok"
        )
        payload["missing_or_invalid_files"] = _normalize_file_statuses(
            payload.get("missing_or_invalid_files"), default_status="missing"
        )

        payload["critical_issues"] = _coerce_file_level_issues(payload.get("critical_issues"))
        payload["warnings"] = _coerce_file_level_issues(payload.get("warnings"))
        return payload

    # ── Field validators ───────────────────────────────────────────────────

    @field_validator("summary")
    @classmethod
    def _validate_counts_only_summary(cls, value: str) -> str:
        """[field_validator] Require summary to be a single counts sentence.

        Stage: runs per-field after the before-validator has normalised it.
        Behaviour: raises ``ValueError`` if the text doesn't match the pattern
        ``N hard blocks, M soft blocks identified``.
        """
        text = str(value).strip()
        if not DATA_SANITY_SUMMARY_RE.fullmatch(text):
            raise ValueError(
                "summary must be a single factual counts sentence, "
                "e.g. '2 hard blocks, 3 soft blocks identified'."
            )
        return text

    @field_validator("validated_files", "missing_or_invalid_files")
    @classmethod
    def _validate_file_status_format(cls, values: list[str]) -> list[str]:
        """[field_validator] Enforce ``file_name -> status`` format for file entries.

        Stage: runs per-field after parsing.
        Behaviour: raises ``ValueError`` if any entry fails the regex.
        """
        for entry in values:
            text = str(entry).strip()
            if not FILE_STATUS_RE.fullmatch(text):
                raise ValueError("Entries must match format: file_name -> status")
        return values

    @field_validator("critical_issues", "warnings")
    @classmethod
    def _validate_file_level_issue_scope(cls, values: list[str]) -> list[str]:
        """[field_validator] Ensure issues are file-level, not column-level.

        Stage: runs per-field after parsing.
        Behaviour: raises ``ValueError`` if any entry has a dot in the file-name
        portion (indicating column granularity) or fails the ``file -> issue`` regex.
        """
        for entry in values:
            text = str(entry).strip()
            left = text.split(" -> ", 1)[0]
            if "." in left:
                raise ValueError("critical_issues and warnings must be file-level only.")
            if not FILE_LEVEL_ISSUE_RE.fullmatch(text):
                raise ValueError(
                    "critical_issues and warnings must match format: file_name -> issue"
                )
        return values

    # ── Model-level consistency ────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_gate_status_consistency(self) -> DataSanityOutput:
        """[model_validator mode=after] Cross-check gate_status against applicability items.

        Stage: runs after all fields are validated.
        Behaviour: silently corrects gate_status if it doesn't match the
        expected value derived from core-file availability and block counts.
        """
        statuses = [item.status for item in self.ratio_applicability]
        statuses.extend(item.status for item in self.valuation_model_applicability)

        has_hard = any(s == "HARD_BLOCKED" for s in statuses)
        has_soft = any(s == "SOFT_BLOCKED" for s in statuses)

        # Gate = is the core data present? Blocked metrics are skips, not failures.
        missing = " ".join(self.missing_or_invalid_files)
        expected = "PASS"
        if any(name in missing for name in CORE_DATA_FILES):
            expected = "FAIL"
        elif has_hard or has_soft:
            expected = "PASS_WITH_SKIPS"

        if self.gate_status != expected:
            self.gate_status = expected  # type: ignore[assignment]

        return self


# ── Module-private helpers ─────────────────────────────────────────────────────


def _normalize_file_statuses(values: object, *, default_status: str) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        normalized.append(text if " -> " in text else f"{text} -> {default_status}")
    return normalized


def _coerce_file_level_issues(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        left, sep, right = text.partition(" -> ")
        left = left.strip()
        issue_text = right.strip() if sep else text
        file_name = left.split(".", 1)[0] if "." in left else left
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", file_name):
            file_name = "general"
        normalized.append(f"{file_name} -> {issue_text or 'issue'}")
    return normalized
