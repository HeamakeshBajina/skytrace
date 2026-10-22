import pytest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_satellites import tle_checksum, valid_tle_line



def test_checksum_counts_digits_and_minus_signs():
    line = "1" + "0" * 67 + "1"
    assert tle_checksum(line) == 1


def test_valid_checksum_is_accepted():
    line = "1" + "0" * 67
    line += str(tle_checksum(line))
    assert valid_tle_line(line, 1)


def test_wrong_checksum_is_rejected():
    line = "1" + "0" * 67 + "9"
    assert not valid_tle_line(line, 1)


def test_wrong_line_number_is_rejected():
    line = "1" + "0" * 67
    line += str(tle_checksum(line))
    assert not valid_tle_line(line, 2)


def test_short_line_is_rejected():
    with pytest.raises(ValueError):
        tle_checksum("1 123")
    assert not valid_tle_line("1 123", 1)


def test_nondigit_checksum_is_rejected():
    line = "1" + "0" * 67 + "X"
    assert not valid_tle_line(line, 1)
