"""Platform-independent comparison functions for ProtocolQC."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .models import CandidateProtocolResult, ParameterResult


def compare_numeric_values(expected: Any, actual: Any, tolerance: float) -> bool:
    """Return True when two numeric values differ by no more than tolerance."""

    try:
        difference = round(abs(float(expected) - float(actual)), 5)
    except (TypeError, ValueError):
        return False
    return difference <= float(tolerance)


def compare_numeric_lists(
    expected: Sequence[Any], actual: Sequence[Any], tolerance: float
) -> bool:
    """Compare numeric lists without considering element order."""

    try:
        expected_values = sorted(float(value) for value in expected)
        actual_values = sorted(float(value) for value in actual)
    except (TypeError, ValueError):
        return False

    if len(expected_values) != len(actual_values):
        return False

    return all(
        round(abs(expected_value - actual_value), 5) <= float(tolerance)
        for expected_value, actual_value in zip(
            expected_values, actual_values, strict=True
        )
    )


def compare_string_lists(expected: Sequence[Any], actual: Sequence[Any]) -> bool:
    """Compare string-like lists without considering order."""

    return {str(value) for value in expected} == {str(value) for value in actual}


def compare_parameter(
    name: str,
    expected: Any,
    actual: Any,
    tolerance: float | None,
) -> ParameterResult:
    """Compare one parameter using the Flywheel gear's comparison semantics."""

    if isinstance(expected, list) or isinstance(actual, list):
        if not isinstance(expected, list) or not isinstance(actual, list):
            passed = False
        elif tolerance is None:
            passed = compare_string_lists(expected, actual)
        else:
            passed = compare_numeric_lists(expected, actual, tolerance)
    elif tolerance is not None and expected != "NA" and actual != "NA":
        passed = compare_numeric_values(expected, actual, tolerance)
    else:
        passed = expected == actual

    return ParameterResult(
        name=name,
        status="PASS" if passed else "FAIL",
        expected=expected,
        actual=actual,
        tolerance=tolerance,
    )


def compare_candidate_protocol(
    name: str,
    approved: dict[str, Any],
    acquired: dict[str, Any],
) -> CandidateProtocolResult:
    """Compare one approved candidate against one acquired series.

    TODO: port the Flywheel gear's Multi-Echo and DICOM file-count checks into
    dedicated functions and include them as ParameterResult records.
    """

    approved_parameters = approved.get("Acquisition_Parameters", {})
    acquired_parameters = acquired.get("Acquisition_Parameters", {})
    results: list[ParameterResult] = []

    for parameter_name, definition in approved_parameters.items():
        expected = definition.get("value")
        tolerance = definition.get("tolerance")
        actual = acquired_parameters.get(parameter_name, "NA")
        results.append(
            compare_parameter(parameter_name, expected, actual, tolerance)
        )

    return CandidateProtocolResult(
        name=name,
        passed=all(result.status == "PASS" for result in results),
        parameters=results,
    )
