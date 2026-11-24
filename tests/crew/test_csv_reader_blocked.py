# SPDX-License-Identifier: MIT
"""The CSV tool hides blocked ratios so agents can't quote them from raw data."""

from types import SimpleNamespace

import pandas as pd

import src.crew.tools.csv_reader as csv_reader
from src.crew.tools.csv_reader import BLOCKED_VALUE, CSVReaderTool, blocked_columns


def _report(*items):
    return SimpleNamespace(
        ratio_applicability=[SimpleNamespace(name=n, status=s) for n, s in items]
    )


def _write_company_info(tmp_path, monkeypatch):
    folder = tmp_path / "TSLA"
    folder.mkdir()
    pd.DataFrame(
        [
            {
                "trailingPE": 210.5,
                "pegRatio": 4.52,
                "trailingPegRatio": 4.54,
                "earningsGrowth": -0.17,
                "sector": "Auto",
            }
        ]
    ).to_csv(folder / "company_info.csv", index=False)
    monkeypatch.setattr(csv_reader, "DATA_DIR", tmp_path)


def test_blocked_ratio_columns_are_hidden(tmp_path, monkeypatch):
    _write_company_info(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.crew.sanity.build_data_sanity_report",
        lambda symbol: _report(("PE Ratio", "VALID"), ("PEG Ratio", "SOFT_BLOCKED")),
    )
    out = CSVReaderTool()._run("TSLA", "company_info.csv")
    assert f"pegRatio: {BLOCKED_VALUE}" in out
    assert f"trailingPegRatio: {BLOCKED_VALUE}" in out
    assert "4.52" not in out and "4.54" not in out
    # valid ratios and the inputs of the blocked ratio stay readable
    assert "trailingPE: 210.5" in out and "earningsGrowth: -0.17" in out and "sector: Auto" in out


def test_nothing_hidden_when_all_ratios_valid(tmp_path, monkeypatch):
    _write_company_info(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.crew.sanity.build_data_sanity_report", lambda symbol: _report(("PEG Ratio", "VALID"))
    )
    out = CSVReaderTool()._run("TSLA", "company_info.csv")
    assert "pegRatio: 4.52" in out and BLOCKED_VALUE not in out


def test_sanity_failure_hides_nothing(monkeypatch):
    def boom(symbol):
        raise RuntimeError("no data")

    monkeypatch.setattr("src.crew.sanity.build_data_sanity_report", boom)
    assert blocked_columns("TSLA") == set()


def test_every_mapped_rule_exists_in_the_sanity_report(tmp_path, monkeypatch):
    """Guard against renamed rules silently disabling the masking."""
    import inspect

    import src.crew.sanity as sanity

    source = inspect.getsource(sanity)
    for rule in csv_reader.BLOCKED_RATIO_COLUMNS:
        assert f'_rule("{rule}"' in source, rule
