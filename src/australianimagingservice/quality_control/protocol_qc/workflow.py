"""XNAT-facing ProtocolQC task."""

from __future__ import annotations

import tempfile
from pathlib import Path

from frametree.core.row import DataRow

from .comparison import compare_candidate_protocol
from .dicom import combine_dicom_parameters, read_dicom_headers
from .models import ProtocolQcReport, SequenceQcResult
from .protocol import load_protocol_template
from .report import write_report
from .xnat_io import (
    dicom_paths,
    download_project_resource_file,
    iter_source_dicom_series,
    write_session_report,
)

PROTOCOL_QC_VERSION = "0.1.0-dev2"


def protocol_qc(
    data_row: DataRow,
    project_resource_label: str = "ProtocolQC",
    protocol_template_filename: str = "protocol-template.json",
    output_resource: str = "ProtocolQC@protocol-qc",
    fail_on_deviation: bool = False,
    dry_run: bool = True,
) -> None:
    """Compare XNAT session DICOM series with a project-specific template.

    The approved JSON template is downloaded at runtime from the selected XNAT
    project's resource folder. DICOM inputs and the output report use the
    FrameTree XNAT adapter.
    """

    project_id = data_row.frameset.id

    with tempfile.TemporaryDirectory(prefix="protocol-qc-") as temporary_dir:
        temporary_path = Path(temporary_dir)
        template_path = download_project_resource_file(
            project_id=project_id,
            resource_label=project_resource_label,
            filename=protocol_template_filename,
            destination=temporary_path / protocol_template_filename,
        )
        template = load_protocol_template(template_path)
        metadata = template["Metadata"]

        sequence_results: list[SequenceQcResult] = []
        messages: list[str] = []

        for resource_path, _order_key, series in iter_source_dicom_series(data_row):
            paths = dicom_paths(series)
            headers = read_dicom_headers(paths)
            acquired = combine_dicom_parameters(headers)
            sequence_name = acquired["Acquisition_Parameters"]["series_description"]
            approved_candidates = template.get(sequence_name)

            if not isinstance(approved_candidates, dict):
                sequence_results.append(
                    SequenceQcResult(
                        resource_path=resource_path,
                        sequence_name=sequence_name,
                        passed=False,
                        dicom_file_count=len(paths),
                        matched_protocol=None,
                        messages=["Sequence is not present in the approved template"],
                    )
                )
                continue

            candidate_results = [
                compare_candidate_protocol(name, approved, acquired)
                for name, approved in approved_candidates.items()
            ]
            passing_candidates = [
                result for result in candidate_results if result.passed
            ]
            sequence_results.append(
                SequenceQcResult(
                    resource_path=resource_path,
                    sequence_name=sequence_name,
                    passed=bool(passing_candidates),
                    dicom_file_count=len(paths),
                    matched_protocol=(
                        passing_candidates[0].name if passing_candidates else None
                    ),
                    candidates=candidate_results,
                )
            )

        expected_sequences = set(metadata.get("SequenceList", []))
        acquired_sequences = {result.sequence_name for result in sequence_results}
        missing_sequences = sorted(expected_sequences - acquired_sequences)
        if missing_sequences:
            messages.append(
                "Missing template sequences: " + ", ".join(missing_sequences)
            )

        passed = (
            bool(sequence_results)
            and all(result.passed for result in sequence_results)
            and not missing_sequences
        )

        report = ProtocolQcReport(
            protocol_qc_version=PROTOCOL_QC_VERSION,
            dictionary_version=metadata.get("DictionaryVersion"),
            template_path=template_path,
            project_id=project_id,
            subject_id=data_row.frequency_id("subject"),
            session_id=data_row.id,
            passed=passed,
            sequences=sequence_results,
            messages=messages,
        )

        report_path = write_report(
            report,
            temporary_path / "protocol-qc-report.json",
        )
        print(report_path.read_text(encoding="utf-8"))
        if not dry_run:
            write_session_report(data_row, report_path, output_resource)

    if fail_on_deviation and not passed:
        raise RuntimeError("ProtocolQC detected one or more protocol deviations")
