"""Data models used by ProtocolQC."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParameterResult:
    """Result of comparing one acquired value with its expected value."""

    name: str
    status: str
    expected: Any
    actual: Any
    tolerance: float | None = None


@dataclass(frozen=True)
class CandidateProtocolResult:
    """Result for one approved candidate protocol for a sequence."""

    name: str
    passed: bool
    parameters: list[ParameterResult] = field(default_factory=list)


@dataclass(frozen=True)
class SequenceQcResult:
    """ProtocolQC result for one XNAT scan/DICOM series."""

    resource_path: str
    sequence_name: str
    passed: bool
    dicom_file_count: int
    matched_protocol: str | None
    candidates: list[CandidateProtocolResult] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProtocolQcReport:
    """Session-level ProtocolQC report."""

    protocol_qc_version: str
    dictionary_version: str | None
    template_path: Path
    project_id: str
    subject_id: str
    session_id: str
    passed: bool
    sequences: list[SequenceQcResult] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the report into a JSON-serialisable dictionary."""

        result = asdict(self)
        result["template_path"] = str(self.template_path)
        result["overall_status"] = "PASS" if self.passed else "FAIL"
        return result
