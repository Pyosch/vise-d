import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.profile_startup import make_bar, format_row


def test_make_bar_full():
    assert make_bar(100, 100, width=10) == "██████████"


def test_make_bar_half():
    assert make_bar(50, 100, width=10) == "█████"


def test_make_bar_zero_ms():
    assert make_bar(0, 100, width=10) == ""


def test_make_bar_zero_max():
    assert make_bar(50, 0, width=10) == ""


def test_format_row_basic():
    row = format_row("pandas", 1234.5, "", max_ms=5000)
    assert "pandas" in row
    assert "1235" in row  # rounded ms


def test_format_row_with_note():
    row = format_row("vpplib", -1, "[not installed]", max_ms=5000)
    assert "[not installed]" in row
    assert "vpplib" in row


from scripts.profile_startup import time_subprocess_import


def test_time_subprocess_import_known_library():
    ms, note = time_subprocess_import("sys")
    assert ms > 0
    assert note == ""


def test_time_subprocess_import_missing_library():
    ms, note = time_subprocess_import("_nonexistent_library_xyz")
    assert ms < 0
    assert "[not installed]" in note
