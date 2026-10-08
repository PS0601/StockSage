# SPDX-License-Identifier: MIT
"""Missing values must not carry units."""

from src.app.utils.formatters._units import strip_units_after_na


def test_attached_units_removed() -> None:
    assert strip_units_after_na("<p>N/Ax</p><p>N/A%</p>") == "<p>N/A</p><p>N/A</p>"


def test_unit_in_span_removed() -> None:
    html = '<p>N/A<span class="text-sm ml-0.5">%</span></p>'
    assert strip_units_after_na(html) == "<p>N/A</p>"


def test_real_values_untouched() -> None:
    html = "<p>12.50%</p><p>1.89x</p><p>N/A</p>"
    assert strip_units_after_na(html) == html


def test_word_after_na_untouched() -> None:
    assert strip_units_after_na("N/Axyz") == "N/Axyz"
