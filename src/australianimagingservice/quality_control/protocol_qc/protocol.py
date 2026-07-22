"""Loading and validating approved ProtocolQC templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProtocolTemplateError(ValueError):
    """Raised when the approved protocol template is invalid."""


def resolve_protocol_template(path: str | Path) -> Path:
    """Resolve and validate the template path inside or outside the container.

    The generated image passes an absolute container path through the Pydra2App
    specification. A normal filesystem path is deliberately used here; the
    processing function should not assume that the repository's ``resources``
    directory is present at runtime.
    """

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Protocol template does not exist: {resolved}")
    return resolved


def load_protocol_template(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate an approved protocol JSON file."""

    template_path = resolve_protocol_template(path)
    with template_path.open(encoding="utf-8") as stream:
        template = json.load(stream)

    if not isinstance(template, dict):
        raise ProtocolTemplateError("Protocol template root must be a JSON object")

    metadata = template.get("Metadata")
    if not isinstance(metadata, dict):
        raise ProtocolTemplateError("Protocol template requires a Metadata object")

    dictionary_version = metadata.get("DictionaryVersion")
    if not isinstance(dictionary_version, str) or not dictionary_version:
        raise ProtocolTemplateError(
            "Metadata.DictionaryVersion must be a non-empty string"
        )

    sequence_list = metadata.get("SequenceList")
    if sequence_list is not None and not isinstance(sequence_list, list):
        raise ProtocolTemplateError("Metadata.SequenceList must be a list when present")

    return template
