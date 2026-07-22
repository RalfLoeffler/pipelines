import json

import pytest

from australianimagingservice.quality_control.protocol_qc.protocol import (
    ProtocolTemplateError,
    load_protocol_template,
)


def test_load_protocol_template(tmp_path):
    template_path = tmp_path / "template.json"
    template_path.write_text(
        json.dumps(
            {
                "Metadata": {
                    "DictionaryVersion": "1.1.2",
                    "SequenceList": [],
                }
            }
        ),
        encoding="utf-8",
    )
    assert load_protocol_template(template_path)["Metadata"]["DictionaryVersion"] == "1.1.2"


def test_missing_metadata_is_rejected(tmp_path):
    template_path = tmp_path / "template.json"
    template_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ProtocolTemplateError):
        load_protocol_template(template_path)
