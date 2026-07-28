# %% [markdown]
# # Create a ProtocolQC template from an XNAT reference session using XNATpy
#
# This notebook converts the Flywheel ProtocolQC template-generation workflow to XNAT and uses **XNATpy** for all XNAT access.
#
# It performs the following steps:
#
# 1. Connects to XNAT using `xnat.connect(...)`.
# 2. Selects a project, subject, and reference session through XNATpy objects.
# 3. Iterates over the session scans.
# 4. Downloads each scan's `DICOM` resource as a ZIP archive.
# 5. Extracts acquisition parameters using the shared ProtocolQC implementation in the `pipelines` repository.
# 6. Builds the numbered approved-protocol JSON structure used by ProtocolQC.
# 7. Saves the JSON locally for mandatory review.
# 8. Optionally creates or reuses a project-level `ProtocolQC` resource and uploads `protocol-template.json`.
# 9. Verifies the uploaded file through XNATpy.
#
# The notebook does not store credentials in the output JSON.

# %% [markdown]
# ## Important compatibility limitation
#
# This notebook currently uses the ProtocolQC scaffold functions `read_dicom_headers(...)` and `combine_dicom_parameters(...)`. It does **not yet reproduce all extraction performed by the supplied Flywheel `run.py`**, particularly:
#
# - enhanced MR functional groups;
# - full SOP Class handling;
# - derived-image filtering equivalent to the Flywheel implementation;
# - Siemens private tags and Phoenix protocol parsing;
# - phase-encoding polarity;
# - spectroscopy-specific fallbacks;
# - all calculated geometry fields;
# - complete multi-echo behaviour;
# - validated DICOM file-count multiplier semantics;
# - Phoenix ZIP report sequence-list checks.
#
# Do not treat a generated template as production-approved until all `NA` values, sequence variants, ordinal numbers, tolerances, and sequence attributes have been reviewed. The preferred long-term design is for both this notebook and the runtime XNAT pipeline to call the same complete, platform-independent DICOM extraction module.

# %%
# Optional installation commands. Run only when needed.
#
# # %pip install xnat pydicom
# # %pip install -e "D:/repos/pipelines"

# %%
from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import xnat as xnatpy

# Adjust this when running outside the editable ais-pipelines environment.
PIPELINES_REPO = Path(r"D:\repos\pipelines")
PIPELINES_SRC = PIPELINES_REPO / "src"

if PIPELINES_SRC.exists() and str(PIPELINES_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINES_SRC))

try:
    from australianimagingservice.quality_control.protocol_qc.dicom import (
        DICTIONARY_VERSION,
        combine_dicom_parameters,
        read_dicom_headers,
    )
except ImportError as error:
    raise ImportError(
        "Could not import ProtocolQC from the pipelines repository. "
        "Activate the ais-pipelines environment or update PIPELINES_REPO."
    ) from error

print(f"ProtocolQC dictionary version: {DICTIONARY_VERSION}")

# %% [markdown]
# ## Configuration
#
# Use the XNAT **project ID**, and a subject/session ID or label accepted by the corresponding XNATpy listing.
#
# Credentials are read from `XNAT_USER` and `XNAT_PASS`. When they are absent, the notebook prompts for them. The password prompt is hidden.

# %%
# XNAT connection and reference-session settings.
XNAT_URL = os.environ.get("XNAT_HOST", "http://localhost:8080").rstrip("/")
PROJECT_ID = "dummydicomproject"
SUBJECT_ID = "dummydicomsubject"
SESSION_ID = "dummydicomsession"

# Scan resource holding DICOM files.
DICOM_RESOURCE_LABEL = "DICOM"

# Destination project resource and filename.
OUTPUT_RESOURCE_LABEL = "ProtocolQC"
OUTPUT_FILENAME = "protocol-template.json"

# Local working/output location.
OUTPUT_DIRECTORY = Path.cwd() / "protocolqc-template-output"
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Upload remains disabled until the generated file has been reviewed.
UPLOAD_TO_XNAT = False
OVERWRITE_EXISTING_TEMPLATE = False

# Use False only for a known local/self-signed test system.
VERIFY_TLS_CERTIFICATE = True

# Default tolerances retained from the Flywheel template-generation script.
TOLERANCE_FIELDS: dict[str, float] = {
    "TR": 10,
    "TE": 1,
    "TI": 1,
    "Flip_angle": 0.01,
    "Bandwidth": 10,
    "Slice_thickness": 0.01,
    "Slice_spacing": 0.01,
}


# %%
def require_setting(name: str, value: str) -> str:
    """Reject placeholder or empty configuration values."""

    if not value or value.startswith("REPLACE_WITH_"):
        raise ValueError(f"Set {name} before continuing")
    return value


require_setting("PROJECT_ID", PROJECT_ID)
require_setting("SUBJECT_ID", SUBJECT_ID)
require_setting("SESSION_ID", SESSION_ID)

XNAT_USER = os.environ.get("XNAT_USER") or input("XNAT username: ").strip()
XNAT_PASS = os.environ.get("XNAT_PASS") or getpass.getpass("XNAT password: ")

if not XNAT_USER or not XNAT_PASS:
    raise ValueError("XNAT username and password are required")

# Keep this connection open while running the notebook. The final cell closes it.
xnat_connection = xnatpy.connect(
    XNAT_URL,
    user=XNAT_USER,
    password=XNAT_PASS,
    verify=VERIFY_TLS_CERTIFICATE,
)

if PROJECT_ID not in xnat_connection.projects:
    raise ValueError(
        f"Project {PROJECT_ID!r} not found. "
        f"Available project IDs: {list(xnat_connection.projects.keys())}"
    )

project = xnat_connection.projects[PROJECT_ID]

if SUBJECT_ID not in project.subjects:
    raise ValueError(
        f"Subject {SUBJECT_ID!r} not found in project {PROJECT_ID!r}. "
        f"Available subjects: {list(project.subjects.keys())}"
    )

subject = project.subjects[SUBJECT_ID]

if SESSION_ID not in subject.experiments:
    raise ValueError(
        f"Session {SESSION_ID!r} not found under subject {SUBJECT_ID!r}. "
        f"Available sessions: {list(subject.experiments.keys())}"
    )

reference_session = subject.experiments[SESSION_ID]

print("Connected to XNAT")
print("Project:", project.id, getattr(project, "name", ""))
print("Subject:", subject.id, getattr(subject, "label", ""))
print("Session:", reference_session.id, getattr(reference_session, "label", ""))


# %% [markdown]
# ## XNATpy helper functions

# %%
def list_session_scans() -> list[Any]:
    """Return the XNATpy scan objects from the configured session."""

    return list(reference_session.scans.values())


def get_scan_dicom_resource(scan: Any) -> Any:
    """Return the configured DICOM resource from one XNAT scan."""

    if DICOM_RESOURCE_LABEL not in scan.resources:
        available = list(scan.resources.keys())
        raise KeyError(
            f"Scan {scan.id!r} has no resource {DICOM_RESOURCE_LABEL!r}. "
            f"Available resources: {available}"
        )
    return scan.resources[DICOM_RESOURCE_LABEL]


def download_scan_dicom_zip(scan: Any, destination: Path) -> Path:
    """Download one scan's DICOM resource as a ZIP archive using XNATpy."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)

    resource = get_scan_dicom_resource(scan)
    resource.download(str(destination), verbose=True)

    if not destination.exists():
        raise RuntimeError(
            f"XNATpy did not create the expected archive for scan {scan.id}: "
            f"{destination}"
        )
    if not zipfile.is_zipfile(destination):
        raise RuntimeError(
            f"Downloaded resource for scan {scan.id} is not a ZIP archive: "
            f"{destination}"
        )
    return destination


def get_or_create_project_resource(label: str) -> Any:
    """Return an existing project resource or create it through XNATpy."""

    if label in project.resources:
        return project.resources[label]

    resource = project.create_resource(label)
    xnat_connection.clearcache()
    return resource


def upload_project_resource_file(
    local_path: Path,
    *,
    resource_label: str,
    filename: str,
    overwrite: bool = False,
) -> Any:
    """Upload one file to a project-level resource using XNATpy."""

    resource = get_or_create_project_resource(resource_label)
    resource.upload(
        str(local_path),
        filename,
        overwrite=overwrite,
        file_content="ProtocolQC protocol template",
        file_format="JSON",
    )
    xnat_connection.clearcache()
    print(
        f"Uploaded {local_path.name} to project resource "
        f"{PROJECT_ID}/{resource_label}/{filename}"
    )
    return project.resources[resource_label]


# %% [markdown]
# ## Inspect the reference session

# %%
scans = list_session_scans()
print(f"Found {len(scans)} scans in session {getattr(reference_session, 'label', SESSION_ID)}")

for scan in scans:
    print(
        f"scan={scan.id} | type={getattr(scan, 'type', '')} | "
        f"series_description={getattr(scan, 'series_description', '')} | "
        f"quality={getattr(scan, 'quality', '')} | "
        f"resources={list(scan.resources.keys())}"
    )

# %% [markdown]
# # Interlude 
# Playing around, real stuff goes on with **Build the protocol template**

# %%
scans[1].id

# %%
scan = scans[1]

# %%
print(scan)
print(type(scan))
print(scan.id)
print(scan.uri)

# %%
# [name for name in dir(scan) if not name.startswith("_")]
for name in sorted(dir(scan)):
    if not name.startswith("_"):
        print(name)

# %%
import inspect

print("Properties and values:")
for name in sorted(dir(scan)):
    if name.startswith("_"):
        continue

    try:
        value = getattr(scan, name)
    except Exception as exc:
        value = f"<error: {exc}>"

    if not callable(value):
        print(f"{name}: {value!r}")

print("\nMethods:")
for name in sorted(dir(scan)):
    if name.startswith("_"):
        continue

    try:
        value = getattr(scan, name)
    except Exception:
        continue

    if callable(value):
        print(name)

# %%
print("ID:", getattr(scan, "id", None))
print("Label:", getattr(scan, "label", None))
print("Type:", getattr(scan, "type", None))
print("Series description:", getattr(scan, "series_description", None))
print("Quality:", getattr(scan, "quality", None))
print("Frames:", getattr(scan, "frames", None))
print("Note:", getattr(scan, "note", None))
print("URI:", getattr(scan, "uri", None))
print("XNAT type:", getattr(scan, "xsi_type", None))

# %%
print("Resource keys:", list(scan.resources.keys()))

for resource_label, resource in scan.resources.items():
    print(
        f"Resource={resource_label!r}, "
        f"type={type(resource).__name__}, "
        f"uri={getattr(resource, 'uri', None)!r}"
    )

# %%
for resource_label, resource in scan.resources.items():
    print(f"\nResource: {resource_label}")

    for file_name, file_object in resource.files.items():
        print(
            f"  {file_name} | "
            f"size={getattr(file_object, 'size', None)} | "
            f"uri={getattr(file_object, 'uri', None)}"
        )

# %%
print(getattr(scan, "fields", None))
print(getattr(scan, "field", None))

# %%
scan_fields = getattr(scan, "fields", None)

if scan_fields is None:
    scan_fields = getattr(scan, "field", None)

if scan_fields is not None:
    for key in scan_fields:
        try:
            print(key, "=", scan_fields[key])
        except Exception as exc:
            print(key, "=", f"<error: {exc}>")

# %%
help(scan)

# %%
help(scan.download)
help(scan.dicom_dump)

# %%
import inspect

print(inspect.signature(scan.download))
print(inspect.signature(scan.dicom_dump))

# %%
dicom_metadata = scan.dicom_dump()
dicom_metadata

# %%
scan.dicom_dump(
    fields=[
        "SeriesDescription",
        "ProtocolName",
        "RepetitionTime",
        "EchoTime",
        "MagneticFieldStrength",
        "SliceThickness",
        "PixelSpacing",
    ]
)

# %%
scan.dicom_dump(fields="SeriesDescription")

# %%
print(getattr(scan, "data", None))

# %%
raw_scan = xnat_connection.get(
    scan.uri,
    query={"format": "json"},
)

print(raw_scan)


# %%

# %% [markdown]
# ## Build the protocol template
#
# The generated structure preserves the Flywheel template format:
#
# - `Metadata`;
# - one key per `series_description`;
# - one or more numbered approved protocol variants per sequence;
# - `Acquisition_Parameters` entries containing `value` and optional `tolerance`;
# - `Sequence_Attributes.Ordinal_Number`.
#
# Scans without a readable `DICOM` resource are recorded in `GenerationWarnings` and skipped.

# %%
def values_equal(left: Any, right: Any) -> bool:
    """Compare generated protocol dictionaries deterministically."""

    return json.dumps(left, sort_keys=True, default=str) == json.dumps(
        right, sort_keys=True, default=str
    )


def add_tolerances(sequence_dictionary: dict[str, Any]) -> dict[str, Any]:
    """Convert acquired parameter values into approved-template entries."""

    acquisition_parameters = sequence_dictionary["Acquisition_Parameters"]
    for field, field_value in list(acquisition_parameters.items()):
        wrapped: dict[str, Any] = {"value": field_value}
        if field in TOLERANCE_FIELDS:
            wrapped["tolerance"] = TOLERANCE_FIELDS[field]
        acquisition_parameters[field] = wrapped
    return sequence_dictionary


def build_protocol_template(
    scan_objects: list[Any],
) -> tuple[dict[str, Any], list[str]]:
    """Generate a ProtocolQC template from all DICOM scans in the session."""

    sequence_list: list[str] = []
    warnings: list[str] = []
    template: dict[str, Any] = {}
    sequence_number = 0

    metadata = {
        "SequenceNumber": 0,
        "DictionaryVersion": DICTIONARY_VERSION,
        "Comments": (
            "Generated from XNAT reference session "
            f"{PROJECT_ID}/{SUBJECT_ID}/{SESSION_ID}. Review all values, "
            "tolerances, sequence attributes, sequence order, and duplicate "
            "series descriptions before approving this template."
        ),
        "SequenceList": sequence_list,
        "Source": {
            "System": "XNAT",
            "ProjectID": PROJECT_ID,
            "SubjectID": str(subject.id),
            "SubjectLabel": str(getattr(subject, "label", SUBJECT_ID)),
            "SessionID": str(reference_session.id),
            "SessionLabel": str(getattr(reference_session, "label", SESSION_ID)),
            "GeneratedUTC": datetime.now(timezone.utc).isoformat(),
        },
    }
    template["Metadata"] = metadata

    with tempfile.TemporaryDirectory(prefix="protocolqc-template-") as temporary:
        temp_root = Path(temporary)

        for scan in scan_objects:
            scan_id = str(scan.id)
            scan_root = temp_root / f"scan-{scan_id}"
            archive = scan_root / "dicom.zip"
            extracted = scan_root / "dicom"

            print(f"Processing XNAT scan {scan_id}...")
            try:
                download_scan_dicom_zip(scan, archive)
                extracted.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(archive) as zip_file:
                    zip_file.extractall(extracted)

                candidate_paths = [
                    path for path in extracted.rglob("*") if path.is_file()
                ]
                if not candidate_paths:
                    raise RuntimeError("Downloaded DICOM archive was empty")

                # Some XNAT resource archives may contain non-DICOM files.
                readable_headers = []
                for path in candidate_paths:
                    try:
                        readable_headers.extend(read_dicom_headers([path]))
                    except RuntimeError:
                        continue

                if not readable_headers:
                    raise RuntimeError("No readable DICOM headers were found")

                sequence_dictionary = combine_dicom_parameters(readable_headers)
                sequence_dictionary = add_tolerances(sequence_dictionary)
                series_description = sequence_dictionary["Acquisition_Parameters"][
                    "series_description"
                ]["value"]

                if not series_description or series_description == "NA":
                    series_description = (
                        getattr(scan, "series_description", None)
                        or getattr(scan, "type", None)
                        or f"SCAN_{scan_id}"
                    )
                    sequence_dictionary["Acquisition_Parameters"][
                        "series_description"
                    ]["value"] = series_description

                if series_description not in template:
                    protocol_number = 1
                else:
                    existing = template[series_description]
                    duplicate = any(
                        values_equal(sequence_dictionary, variant)
                        for variant in existing.values()
                    )
                    if duplicate:
                        print(
                            f"Skipping duplicate protocol variant for "
                            f"{series_description}"
                        )
                        continue
                    protocol_number = max(int(number) for number in existing) + 1

                sequence_number += 1
                sequence_list.append(series_description)
                sequence_dictionary["Sequence_Attributes"][
                    "Ordinal_Number"
                ] = sequence_number
                sequence_dictionary["Sequence_Attributes"][
                    "XNAT_Scan_ID"
                ] = scan_id

                template.setdefault(series_description, {})[
                    protocol_number
                ] = sequence_dictionary
                print(
                    f"Added {series_description}, protocol variant "
                    f"{protocol_number}"
                )

            except Exception as error:
                message = f"Scan {scan_id} was skipped: {error}"
                warnings.append(message)
                print(f"WARNING: {message}")

    metadata["SequenceNumber"] = sequence_number
    metadata["SequenceList"] = sequence_list
    if warnings:
        metadata["GenerationWarnings"] = warnings

    return template, warnings


protocol_template, generation_warnings = build_protocol_template(scans)
print(
    f"Generated {protocol_template['Metadata']['SequenceNumber']} "
    "protocol entries"
)

# %% [markdown]
# ## Save and review the template

# %%
local_output = OUTPUT_DIRECTORY / OUTPUT_FILENAME
local_output.write_text(
    json.dumps(protocol_template, indent=4, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Saved template: {local_output}")
print(f"Warnings: {len(generation_warnings)}")

for name, value in protocol_template.items():
    if name == "Metadata":
        continue
    print(f"{name}: {len(value)} protocol variant(s)")

# %% [markdown]
# ### Mandatory manual review before upload
#
# Review the generated JSON and confirm at least:
#
# - `Metadata.DictionaryVersion`;
# - sequence count and `SequenceList`;
# - removal of scouts, localisers, derived images, and unwanted series;
# - duplicate sequence descriptions and numbered variants;
# - ordinal numbers;
# - tolerance values;
# - `Multi-Echo`;
# - `Echo_lines_multiplier`;
# - `Temporal_positions_multiplier`;
# - `Check_DICOM_File_Number`;
# - enhanced MR and spectroscopy extraction results;
# - Siemens private-tag values and phase-encoding polarity, once implemented;
# - every `NA` value.
#
# On Windows, open the output with:
#
# ```powershell
# & 'C:\Program Files\Notepad++\notepad++.exe' '<path-to-protocol-template.json>'
# ```

# %% [markdown]
# ## Upload the reviewed template to the XNAT project resource

# %%
UPLOAD_TO_XNAT=True

if UPLOAD_TO_XNAT:
    uploaded_resource = upload_project_resource_file(
        local_output,
        resource_label=OUTPUT_RESOURCE_LABEL,
        filename=OUTPUT_FILENAME,
        overwrite=OVERWRITE_EXISTING_TEMPLATE,
    )
else:
    print(
        "Upload disabled. Review the JSON, then set UPLOAD_TO_XNAT=True. "
        "Set OVERWRITE_EXISTING_TEMPLATE=True only when replacement is intended."
    )


# %% [markdown]
# ## Verify the uploaded project resource

# %%
def verify_uploaded_template() -> dict[str, Any]:
    """Verify and download the uploaded template through XNATpy."""

    xnat_connection.clearcache()
    if OUTPUT_RESOURCE_LABEL not in project.resources:
        raise FileNotFoundError(
            f"Project resource {OUTPUT_RESOURCE_LABEL!r} does not exist"
        )

    resource = project.resources[OUTPUT_RESOURCE_LABEL]
    if OUTPUT_FILENAME not in resource.files:
        raise FileNotFoundError(
            f"File {OUTPUT_FILENAME!r} does not exist in resource "
            f"{OUTPUT_RESOURCE_LABEL!r}. Available files: "
            f"{list(resource.files.keys())}"
        )

    remote_file = resource.files[OUTPUT_FILENAME]
    verify_path = OUTPUT_DIRECTORY / f"verified-{OUTPUT_FILENAME}"
    verify_path.unlink(missing_ok=True)
    remote_file.download(str(verify_path))

    uploaded = json.loads(verify_path.read_text(encoding="utf-8"))
    print(
        f"Verified project resource: "
        f"{OUTPUT_RESOURCE_LABEL}/{OUTPUT_FILENAME}"
    )
    print(f"Downloaded verification copy: {verify_path}")
    return uploaded


# Run after upload:
uploaded_template = verify_uploaded_template()

# %% [markdown]
# ## Close the XNAT connection
#
# Run this cell when finished. Re-run the connection cell before using XNAT again.

# %%
xnat_connection.disconnect()
print("XNAT connection closed")

# %%
