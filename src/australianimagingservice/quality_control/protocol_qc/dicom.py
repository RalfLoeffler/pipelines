"""DICOM discovery and acquisition-parameter extraction."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataset import Dataset


DICTIONARY_VERSION = "1.1.2"


def read_dicom_headers(paths: Iterable[Path]) -> list[Dataset]:
    """Read DICOM headers without loading pixel data."""

    headers: list[Dataset] = []
    for path in paths:
        try:
            headers.append(pydicom.dcmread(path, stop_before_pixels=True))
        except Exception as error:  # TODO: narrow exceptions after fixture coverage.
            raise RuntimeError(f"Could not read DICOM file {path}: {error}") from error
    return headers


def extract_dicom_parameters(header: Dataset) -> dict[str, Any]:
    """Extract the ProtocolQC dictionary from one DICOM header.

    This is intentionally a partial scaffold. It extracts stable public DICOM
    attributes and preserves the output shape used by the existing Flywheel
    ProtocolQC gear. Siemens enhanced-MR functional groups, private tags,
    Phoenix protocol parsing, phase-encoding polarity and spectroscopy handling
    remain explicit TODOs.
    """

    def value(keyword: str, default: str = "NA") -> str:
        raw = getattr(header, keyword, default)
        return str(raw) if raw is not None else default

    pixel_spacing = getattr(header, "PixelSpacing", ["NA", "NA"])
    if len(pixel_spacing) < 2:
        pixel_spacing = ["NA", "NA"]

    return {
        "Sequence_Attributes": {
            "Multi-Echo": False,
            "Echo_lines_multiplier": False,
            "Temporal_positions_multiplier": False,
            "Check_DICOM_File_Number": True,
            "Comment": "ProtocolQC XNAT scaffold extraction",
        },
        "Acquisition_Parameters": {
            "coil": value("ReceiveCoilName"),
            "Field_strength": value("MagneticFieldStrength"),
            "series_description": value("SeriesDescription"),
            "Sequence": value("ScanningSequence"),
            "Sequence_options": value("SequenceVariant"),
            "Protocol": value("ProtocolName"),
            "Acquisition_type": value("MRAcquisitionType"),
            "TR": value("RepetitionTime"),
            "TE": value("EchoTime"),
            "TI": value("InversionTime"),
            "Flip_angle": value("FlipAngle"),
            "ETL": value("EchoTrainLength"),
            "Bandwidth": value("PixelBandwidth"),
            "PE_dir": value("InPlanePhaseEncodingDirection"),
            "PE_polarity": "NA",
            "Slice_thickness": value("SliceThickness"),
            "Slice_spacing": value("SpacingBetweenSlices"),
            "Pix_spacing_row": str(pixel_spacing[0]),
            "Pix_spacing_col": str(pixel_spacing[1]),
            "Rows": value("Rows"),
            "Columns": value("Columns"),
            "Number_slices": value("NumberOfFrames"),
            "NSA": value("NumberOfAverages"),
            "Temporal_positions": value("NumberOfTemporalPositions"),
        },
    }


def combine_dicom_parameters(headers: list[Dataset]) -> dict[str, Any]:
    """Combine parameter values across files in a DICOM series.

    Values that vary across files are represented as unique lists. This mirrors
    the multi-echo behaviour of the Flywheel gear at a high level.
    """

    if not headers:
        raise ValueError("Cannot combine an empty DICOM series")

    combined = extract_dicom_parameters(headers[0])
    acquired = combined["Acquisition_Parameters"]

    for header in headers[1:]:
        current = extract_dicom_parameters(header)["Acquisition_Parameters"]
        for name, current_value in current.items():
            existing_value = acquired.get(name, "NA")
            if existing_value == current_value:
                continue
            existing_values = (
                list(existing_value)
                if isinstance(existing_value, list)
                else [existing_value]
            )
            if current_value not in existing_values:
                existing_values.append(current_value)
            acquired[name] = existing_values

    return combined
