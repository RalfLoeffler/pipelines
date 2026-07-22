"""ProtocolQC pipeline entry point.

This module intentionally contains only the pipeline framework. The protocol
comparison logic, accepted metadata inputs, report schema, and XNAT output
behaviour still need to be specified before implementation.
"""

from __future__ import annotations

from frametree.core.row import DataRow


def protocol_qc(
    data_row: DataRow,
    protocol_definition: str = "",
    tolerance_percent: float = 5.0,
    fail_on_deviation: bool = False,
    dry_run: bool = True,
) -> None:
    """Run protocol quality control for one XNAT imaging session.

    Parameters
    ----------
    data_row:
        FrameTree row representing the selected XNAT session.
    protocol_definition:
        Identifier or path for the expected protocol definition. The accepted
        format has not yet been defined.
    tolerance_percent:
        Default relative tolerance for numeric protocol parameters. Individual
        parameter tolerances may replace this once the report specification is
        defined.
    fail_on_deviation:
        Whether a detected deviation should fail the pipeline process.
    dry_run:
        Whether to analyse without writing results back to XNAT.

    Notes
    -----
    This function is a scaffold. It deliberately fails rather than reporting a
    successful QC result before the comparison rules and output contract have
    been implemented.
    """
    del data_row
    del protocol_definition
    del tolerance_percent
    del fail_on_deviation
    del dry_run

    raise NotImplementedError(
        "ProtocolQC is a framework only. Define the protocol input format, "
        "comparison rules, report schema, and XNAT output destination before "
        "enabling it for operational use."
    )
