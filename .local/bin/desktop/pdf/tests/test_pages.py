import pytest
from pdf.pages import parse_groups, parse_ranges, RangeError


def test_all_when_empty():
    assert parse_groups("", 3) == [[0, 1, 2]]
    assert parse_groups("all", 2) == [[0, 1]]


def test_groups_and_open_ranges():
    assert parse_groups("1-3, 5 ,8-", 9) == [[0, 1, 2], [4], [7, 8]]
    assert parse_groups("-2", 5) == [[0, 1]]


def test_flatten_dedup_keeps_order():
    assert parse_ranges("3,1-3", 3) == [2, 0, 1]


@pytest.mark.parametrize("spec", ["0", "4", "2-1", "a", "1--2", "1,,2"])
def test_invalid(spec):
    with pytest.raises(RangeError):
        parse_groups(spec, 3)
