from __future__ import annotations

import pytest

from scraper.v3.line_filter import is_half_line


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("0.5", True),
        ("1.5", True),
        ("2.5", True),
        ("6.5", True),
        ("1", False),
        ("2", False),
        ("2.25", False),
        ("3.75", False),
        ("", False),
        (None, False),
        ("1,5", True),
    ],
)
def test_is_half_line(line, expected):
    assert is_half_line(line) is expected
