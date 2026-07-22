from australianimagingservice.quality_control.protocol_qc.comparison import (
    compare_numeric_lists,
    compare_numeric_values,
    compare_string_lists,
)


def test_compare_numeric_values_within_tolerance():
    assert compare_numeric_values(2.0, 2.04, 0.05)


def test_compare_numeric_values_outside_tolerance():
    assert not compare_numeric_values(2.0, 2.06, 0.05)


def test_compare_numeric_lists_ignore_order():
    assert compare_numeric_lists([1, 2], [2.01, 1.01], 0.02)


def test_compare_string_lists_ignore_order():
    assert compare_string_lists(["A", "B"], ["B", "A"])
