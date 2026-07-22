"""ProtocolQC report serialisation."""

from __future__ import annotations

import json
from pathlib import Path

from .models import ProtocolQcReport


def write_report(report: ProtocolQcReport, output_path: Path) -> Path:
    """Write a ProtocolQC report as UTF-8 JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path
