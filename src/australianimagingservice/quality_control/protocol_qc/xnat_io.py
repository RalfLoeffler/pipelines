"""XNAT and FrameTree file access for ProtocolQC."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote

import requests
from fileformats.generic import File
from fileformats.medimage.dicom import DicomSeries
from frametree.core.row import DataRow


class XnatProjectResourceError(RuntimeError):
    """Raised when the project-level protocol template cannot be retrieved."""


def iter_source_dicom_series(
    data_row: DataRow,
) -> Iterator[tuple[str, str | int | None, DicomSeries]]:
    """Yield original DICOM series available in an XNAT session row.

    FrameTree populates ``data_row.entries_dict`` from the selected XNAT
    session. Accessing ``entry.item`` materialises the XNAT resource in the
    container cache; ``DicomSeries.contents`` then yields local file paths.
    """

    for (resource_path, order_key), entry in list(data_row.entries_dict.items()):
        if entry.datatype != DicomSeries:
            continue
        if entry.is_derivative:
            continue
        yield resource_path, order_key, entry.item


def dicom_paths(series: DicomSeries) -> list[Path]:
    """Return local paths for a materialised FrameTree DICOM series."""

    return [Path(path) for path in series.contents]


def xnat_connection_from_environment() -> tuple[str, str, str]:
    """Return the Container Service XNAT connection values.

    XNAT Container Service injects ``XNAT_HOST``, ``XNAT_USER`` and
    ``XNAT_PASS`` into launched containers. The user/password values are a
    temporary alias token, not long-lived account credentials.
    """

    missing = [
        name
        for name in ("XNAT_HOST", "XNAT_USER", "XNAT_PASS")
        if not os.environ.get(name)
    ]
    if missing:
        raise XnatProjectResourceError(
            "Missing Container Service environment variable(s): "
            + ", ".join(missing)
        )

    return (
        os.environ["XNAT_HOST"].rstrip("/"),
        os.environ["XNAT_USER"],
        os.environ["XNAT_PASS"],
    )


def download_project_resource_file(
    *,
    project_id: str,
    resource_label: str,
    filename: str,
    destination: Path,
    timeout_seconds: float = 60.0,
) -> Path:
    """Download a JSON template from an XNAT project resource.

    Uses the documented XNAT project-resource endpoint::

        GET /data/projects/{project-id}/resources/{resource-label}/files/{filename}

    Path components are URL-escaped. The response is streamed to a temporary
    file and atomically renamed only after a complete successful download.
    """

    if not project_id.strip():
        raise ValueError("project_id must not be empty")
    if not resource_label.strip():
        raise ValueError("resource_label must not be empty")
    if not filename.strip():
        raise ValueError("filename must not be empty")

    host, username, password = xnat_connection_from_environment()
    endpoint = (
        f"{host}/data/projects/{quote(project_id, safe='')}"
        f"/resources/{quote(resource_label, safe='')}"
        f"/files/{quote(filename, safe='')}"
    )

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination.with_suffix(destination.suffix + ".partial")

    try:
        with requests.get(
            endpoint,
            auth=(username, password),
            stream=True,
            timeout=timeout_seconds,
            headers={"Accept": "application/json"},
        ) as response:
            response.raise_for_status()
            with partial_path.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output_file.write(chunk)
        partial_path.replace(destination)
    except requests.RequestException as error:
        partial_path.unlink(missing_ok=True)
        raise XnatProjectResourceError(
            "Could not download ProtocolQC template from XNAT project "
            f"resource '{resource_label}/{filename}' in project "
            f"'{project_id}': {error}"
        ) from error

    return destination


def write_session_report(
    data_row: DataRow,
    report_path: Path,
    resource_path: str = "ProtocolQC@protocol-qc",
) -> None:
    """Upload a JSON report as a derived XNAT session entry via FrameTree."""

    existing_entries = {
        key[0]: entry for key, entry in list(data_row.entries_dict.items())
    }
    if resource_path in existing_entries:
        report_entry = existing_entries[resource_path]
    else:
        report_entry = data_row.create_entry(resource_path, datatype=File)

    report_entry.item = File(report_path)
