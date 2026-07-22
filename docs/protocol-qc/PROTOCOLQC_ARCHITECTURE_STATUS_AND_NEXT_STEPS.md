# ProtocolQC Architecture, Status, and Next Steps

## Purpose

ProtocolQC is an XNAT quality-control pipeline for comparing MRI acquisition parameters extracted from DICOM data against an approved protocol template stored as a JSON file in an XNAT project-level resource.

The design is based on the existing Flywheel ProtocolQC gear, but replaces Flywheel-specific APIs, project attachments, session tags, Gear Toolkit paths, and Twilio notifications with XNAT- and FrameTree-compatible data access and reporting.

---

## Target Architecture

### High-level flow

```text
XNAT imaging session
        |
        v
FrameTree DataRow for selected session
        |
        +--> discover non-derivative DICOM series
        |       |
        |       v
        |   materialise local DICOM files
        |
        +--> determine XNAT project ID
        |
        +--> download approved protocol JSON from project resource
        |       |
        |       v
        |   /data/projects/{project-id}/resources/{resource-label}/files/{filename}
        |
        v
Extract acquisition parameters from DICOM
        |
        v
Compare acquired values with approved protocol template
        |
        +--> numeric comparison with tolerance
        +--> numeric-list comparison with tolerance
        +--> unordered string-list comparison
        +--> sequence attribute checks
        +--> expected DICOM file-count checks
        |
        v
Generate session-level ProtocolQC JSON report
        |
        +--> dry-run: log/report locally only
        |
        +--> non-dry-run: write derived report back to XNAT through FrameTree
```

### Runtime components

- XNAT session selected through the generated Container Service wrapper.
- Pydra2App-generated container command.
- FrameTree XNAT adapter for input discovery and derivative output creation.
- `pydicom` for DICOM parsing.
- Approved protocol template downloaded at runtime from an XNAT project resource.
- Generated container image published under the personal GHCR namespace:
  - `ghcr.io/ralfloeffler/quality-control.protocol-qc:<version>`

### Proposed source layout

```text
src/australianimagingservice/quality_control/protocol_qc/
├── __init__.py
├── workflow.py
├── xnat_io.py
├── protocol.py
├── dicom.py
├── comparison.py
├── models.py
├── report.py
└── tests/
    ├── test_comparison.py
    ├── test_protocol.py
    ├── test_dicom.py
    ├── test_xnat_io.py
    └── test_workflow.py

specs/ralfloeffler/quality-control/
└── protocol-qc.yaml

requirements/quality-control/
└── protocol-qc.txt

docs/protocol-qc/
└── README.md
```

---

## XNAT Resource Access

### Approved protocol JSON

The approved protocol template is not embedded in the container image.

Each XNAT project supplies its own JSON file in a project-level resource, with defaults:

```text
Resource label: ProtocolQC
Filename:       protocol-template.json
```

The pipeline downloads the file through the XNAT REST endpoint:

```text
/data/projects/{project-id}/resources/{resource-label}/files/{filename}
```

Runtime authentication uses the temporary Container Service environment variables:

```text
XNAT_HOST
XNAT_USER
XNAT_PASS
```

No permanent XNAT credentials should be stored in source code, the image, the YAML specification, or the protocol JSON.

### DICOM input access

The intended FrameTree access pattern is:

```python
for (_, _), entry in data_row.entries_dict.items():
    if entry.datatype != DicomSeries:
        continue
    if entry.is_derivative:
        continue

    dicom_series = entry.item
    dicom_paths = list(dicom_series.contents)
```

This should be validated against the actual XNAT hierarchy and resource naming used in the local sandbox.

### Report output

The intended output path uses a FrameTree derivative entry, conceptually:

```python
report_entry = data_row.create_entry(
    "ProtocolQC@protocol-qc",
    datatype=File,
)
report_entry.item = File(report_path)
```

The exact XNAT resource label, overwrite behaviour, and repeated-run behaviour still require integration testing.

---

## Protocol Template Contract

The initial XNAT implementation should retain the protocol dictionary structure used by the Flywheel gear.

Expected top-level sections include:

```text
Metadata
<sequence name>
```

Expected metadata fields include:

```text
DictionaryVersion
SequenceList
```

Each sequence may contain one or more approved protocol alternatives. Each alternative contains:

```text
Sequence_Attributes
Acquisition_Parameters
```

Each acquisition parameter definition contains:

```text
value
optional tolerance
```

The production JSON schema has not yet been formalised independently of the existing dictionaries.

---

## Functional Scope

### Initial supported behaviour

The first functional release should support:

- XNAT session-level execution.
- Per-project approved protocol JSON files.
- Enhanced MR DICOM processing.
- MR spectroscopy compatibility where relevant DICOM fields are absent.
- Zipped and uncompressed DICOM input handling.
- Sequence matching by `series_description`.
- Numeric comparison with absolute tolerance.
- Numeric-list comparison with absolute tolerance.
- Unordered string-list comparison.
- Multiple approved alternatives for one sequence.
- Multi-echo detection.
- Expected DICOM file-count checks.
- Missing and unexpected sequence reporting.
- One session-level JSON result.
- Dry-run operation.
- Optional nonzero exit status when deviations are detected.
- No modification of source DICOM.

### Deferred behaviour

The following Flywheel-specific features should not be included in the initial XNAT implementation:

- Flywheel Gear context and API calls.
- Flywheel project attachments.
- Flywheel acquisition and session IDs.
- Flywheel session tags.
- Flywheel template-satisfaction flags.
- Twilio SMS notifications.
- `/flywheel/v0/output` paths.

Potential future XNAT replacements include Event Service notifications, XNAT metadata fields, assessors, or external alerting, but these are not yet defined.

---

## Current Status

### Completed

- Personal fork and working branch established for the AIS pipelines repository.
- Local Python 3.11 Mamba environment configured.
- Pydra2App and XNAT extension validated locally.
- Local XNAT sandbox framework created using the AIS/XNAT testing approach.
- ProtocolQC package scaffold created.
- Personal Pydra2App specification namespace established under:
  - `specs/ralfloeffler/quality-control/protocol-qc.yaml`
- Target image namespace established under:
  - `ghcr.io/ralfloeffler/quality-control.protocol-qc`
- XNAT project-resource download approach defined.
- XNAT temporary credential environment variables identified.
- Initial FrameTree DICOM discovery and report-output patterns defined.
- Initial unit-test structure created.
- Windows PowerShell build workaround identified for generated Dockerfile paths.

### Partially implemented

- Protocol template loading from an XNAT project resource.
- FrameTree-based DICOM discovery.
- Session-level report generation.
- Comparison functions based on the Flywheel gear.
- DICOM extraction using stable public DICOM tags.
- Tests for XNAT environment variables and project-resource URL handling.

### Not yet completed

- Full port of enhanced MR functional-group parsing.
- Siemens private-tag parsing.
- Phoenix protocol parsing.
- Phase-encoding polarity extraction.
- Complete spectroscopy handling.
- Full multi-echo combination behaviour.
- DICOM file-count multiplier logic.
- Missing-sequence and unexpected-sequence reporting.
- Production report schema validation.
- XNAT sandbox end-to-end run.
- Repeated-run and overwrite behaviour.
- Production Kubernetes validation.

---

## Known Build Issue

On Windows, Pydra2App currently generates a Dockerfile `COPY` source path using backslashes, for example:

```text
python-packages\australianimagingservice-<version>.tar.gz
```

Docker expects forward slashes in the generated Dockerfile:

```text
python-packages/australianimagingservice-<version>.tar.gz
```

The current workaround is a PowerShell build wrapper that:

1. runs `pydra2app make xnat`;
2. locates the generated Dockerfile after failure;
3. replaces the affected backslashes with forward slashes;
4. reruns `docker build` using the generated build directory.

This should remain a local workaround until fixed upstream.

Before running downloaded PowerShell scripts:

```powershell
Get-ChildItem .\scripts\*.ps1 | Unblock-File
```

---

## Next Tests

### 1. Unit tests

Validate independently:

- numeric scalar comparisons;
- floating-point rounding behaviour;
- numeric list ordering and tolerance;
- string list ordering;
- missing acquisition fields;
- multiple approved alternatives;
- dictionary version validation;
- invalid JSON and missing metadata;
- URL encoding for project/resource/file names;
- missing XNAT credential variables;
- HTTP error handling for project-resource downloads.

### 2. Container build tests

Confirm:

- image builds with the Windows path workaround;
- Python 3.11 is used in the `pydra2app` environment;
- `pydicom`, FrameTree, and the ProtocolQC package import;
- generated XNAT command JSON exists;
- generated JSON references the personal GHCR image;
- no production protocol JSON is embedded in the image.

### 3. Local XNAT sandbox tests

Create a synthetic project containing:

```text
Project ID:      PROTOCOLQC_TEST
Resource label:  ProtocolQC
Template file:   protocol-template.json
```

Upload synthetic DICOM data and validate:

- project ID resolution from the selected session;
- access to `XNAT_HOST`, `XNAT_USER`, and `XNAT_PASS`;
- download of the project protocol JSON;
- discovery of all expected DICOM series;
- exclusion of derivative resources;
- dry-run completion;
- correct sequence matching;
- correct PASS and FAIL reports;
- no source DICOM modification;
- report write-back to the expected XNAT resource;
- repeated-run behaviour.

### 4. Compatibility tests against the Flywheel gear

For the same synthetic DICOM and protocol JSON, compare:

- extracted acquisition values;
- sequence matching;
- numeric tolerance outcomes;
- multi-echo results;
- file-count checks;
- final PASS/FAIL state;
- detailed parameter report.

Any intentional differences must be documented.

### 5. Kubernetes integration tests

After local XNAT validation:

- push the development image to personal GHCR;
- configure image pull access if the package is private;
- import the generated command JSON into development XNAT;
- test temporary XNAT credential injection;
- test network access from the job to XNAT;
- validate storage and FrameTree behaviour;
- review logs for PHI exposure;
- verify resource limits and failure handling.

---

## TODOs

### Architecture and data contract

- [ ] Formalise the protocol-template JSON schema.
- [ ] Decide how protocol-template versions are managed.
- [ ] Define whether one project may contain multiple protocol templates.
- [ ] Define template selection rules when multiple files exist.
- [ ] Define sequence-name normalisation and alias handling.
- [ ] Define missing, unexpected, duplicated, and optional sequence behaviour.
- [ ] Define PASS, WARNING, FAIL, and ABORT semantics.
- [ ] Decide whether output should remain a session resource or become an assessor.

### DICOM extraction

- [ ] Port enhanced MR functional-group extraction.
- [ ] Port Siemens private-tag handling.
- [ ] Port Phoenix protocol extraction.
- [ ] Port phase-encoding polarity logic.
- [ ] Port spectroscopy-specific fallbacks.
- [ ] Port multi-echo combination behaviour.
- [ ] Port temporal-position and echo-line multipliers.
- [ ] Handle derived images consistently.
- [ ] Define support for regular non-enhanced MR DICOM.
- [ ] Add structured warnings instead of broad exception suppression.

### Comparison engine

- [ ] Replace integer PASS/FAIL conventions with typed results internally.
- [ ] Preserve output compatibility with existing protocol dictionaries.
- [ ] Validate list lengths before numeric-list comparison.
- [ ] Define behaviour for `NA`, null, missing, and malformed values.
- [ ] Define tolerance units and numeric coercion rules.
- [ ] Add regression tests for existing Flywheel behaviour.

### XNAT integration

- [ ] Validate project ID derivation from `DataRow`.
- [ ] Validate DICOM resource discovery against real XNAT sessions.
- [ ] Validate temporary Container Service credentials.
- [ ] Validate project-resource download permissions.
- [ ] Validate report resource creation.
- [ ] Define overwrite/versioning behaviour.
- [ ] Define cleanup behaviour for failed jobs.
- [ ] Define whether ProtocolQC should update XNAT metadata or labels.
- [ ] Define Event Service automation only after manual execution is stable.

### Testing and documentation

- [ ] Add synthetic enhanced MR DICOM fixtures.
- [ ] Add spectroscopy fixtures.
- [ ] Add multi-echo fixtures.
- [ ] Add passing and failing protocol templates.
- [ ] Add malformed-template fixtures.
- [ ] Add local XNAT integration tests.
- [ ] Add expected report fixtures.
- [ ] Document all intentional deviations from the Flywheel gear.
- [ ] Record tested XNAT, Container Service, Pydra2App, and FrameTree versions.
- [ ] Add release and rollback instructions.

---

## Immediate Next Actions

1. Install the latest ProtocolQC project-resource update into the pipelines fork.
2. Confirm the YAML author entry contains both `name` and `email`.
3. Run unit tests for the scaffold.
4. Build the personal development image using the Windows build wrapper.
5. Verify that the image does not contain an embedded production protocol JSON.
6. Upload a synthetic protocol template to the local XNAT test project resource.
7. Run ProtocolQC in dry-run mode in the local XNAT sandbox.
8. Compare the generated report against the Flywheel gear for the same test data.
9. Implement the remaining enhanced MR and Siemens-specific extraction logic incrementally.
10. Commit source, tests, and documentation together on the ProtocolQC feature branch.
