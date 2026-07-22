"""Tests for the initial ProtocolQC framework."""

from __future__ import annotations

import inspect

import pytest

from australianimagingservice.quality_control.protocol_qc import protocol_qc


def test_protocol_qc_public_signature() -> None:
    """The entry point should expose the parameters declared in the spec."""
    parameters = inspect.signature(protocol_qc).parameters

    assert list(parameters) == [
        "data_row",
        "protocol_definition",
        "tolerance_percent",
        "fail_on_deviation",
        "dry_run",
    ]


def test_protocol_qc_fails_until_implemented() -> None:
    """The framework must not produce a false successful QC result."""
    with pytest.raises(NotImplementedError, match="ProtocolQC is a framework only"):
        protocol_qc(data_row=object())  # type: ignore[arg-type]
