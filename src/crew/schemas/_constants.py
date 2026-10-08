# SPDX-License-Identifier: MIT
"""Schema validation constants — only values actively used by schema validators."""

from __future__ import annotations

import re

# ── Data Sanity ────────────────────────────────────────────────────────────────

DATA_SANITY_SUMMARY_RE = re.compile(r"^\d+ hard blocks?, \d+ soft blocks? identified\.?$")
FILE_STATUS_RE = re.compile(r"^[A-Za-z0-9_.-]+ -> [A-Za-z0-9_. -]+$")
FILE_LEVEL_ISSUE_RE = re.compile(r"^[A-Za-z0-9_.-]+ -> .+$")

DATA_SANITY_REQUIRED_FILES = (
    "company_info.csv",
    "historical_prices.csv",
    "income_statement.csv",
    "balance_sheet.csv",
    "cash_flow.csv",
    "recommendations.csv",
    "institutional_holders.csv",
    "insider_transactions.csv",
    "market_index.csv",
    "sector_index.csv",
    "news.csv",
)

# ── Final Report ───────────────────────────────────────────────────────────────

CONFIDENCE_FROM_ADJUSTMENT: dict[str, str] = {
    "increase": "High",
    "increased": "High",
    "unchanged": "Medium",
    "reduce": "Low",
    "reduced": "Low",
}

# Files without which the analysis cannot be trusted at all. Missing any of these
# fails the data quality gate; missing optional files (news, holders) does not.
CORE_DATA_FILES = (
    "company_info.csv",
    "historical_prices.csv",
    "income_statement.csv",
    "balance_sheet.csv",
    "cash_flow.csv",
)
