"""Tests for XNAT project-resource access."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from australianimagingservice.quality_control.protocol_qc.xnat_io import (
    XnatProjectResourceError,
    download_project_resource_file,
    xnat_connection_from_environment,
)


def test_xnat_connection_requires_container_service_environment(monkeypatch):
    for variable in ("XNAT_HOST", "XNAT_USER", "XNAT_PASS"):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(XnatProjectResourceError, match="XNAT_HOST"):
        xnat_connection_from_environment()


def test_download_project_resource_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XNAT_HOST", "https://xnat.example")
    monkeypatch.setenv("XNAT_USER", "alias-user")
    monkeypatch.setenv("XNAT_PASS", "alias-password")

    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.iter_content.return_value = [b'{"Metadata": {}}']
    response.raise_for_status.return_value = None

    destination = tmp_path / "protocol-template.json"
    with patch(
        "australianimagingservice.quality_control.protocol_qc.xnat_io.requests.get",
        return_value=response,
    ) as get_request:
        result = download_project_resource_file(
            project_id="TEST PROJECT",
            resource_label="Protocol QC",
            filename="protocol template.json",
            destination=destination,
        )

    assert result == destination
    assert destination.read_bytes() == b'{"Metadata": {}}'
    requested_url = get_request.call_args.args[0]
    assert requested_url.endswith(
        "/data/projects/TEST%20PROJECT/resources/Protocol%20QC/"
        "files/protocol%20template.json"
    )
