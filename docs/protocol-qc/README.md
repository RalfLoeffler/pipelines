# ProtocolQC XNAT Pipeline Scaffold

## Purpose

ProtocolQC compares DICOM acquisition parameters in an XNAT imaging session
against an approved protocol template stored as a JSON resource in the built
container image.

The design is based on the supplied Flywheel ProtocolQC gear, but separates the
platform-independent QC logic from XNAT/FrameTree access. Flywheel APIs,
Twilio notifications, Flywheel tags, and `/flywheel/v0/output` are not part of
this scaffold.

## Layout

```text
src/australianimagingservice/quality_control/protocol_qc/
    comparison.py   Parameter comparison logic
    dicom.py        DICOM reading and extraction
    models.py       Structured report models
    protocol.py     JSON template loading and validation
    report.py       JSON serialisation
    workflow.py     Pydra2App/XNAT entry point
    xnat_io.py      FrameTree/XNAT file access and report upload

resources/protocol-qc-template/
    protocol-template.json

specs/ralfloeffler/quality-control/
    protocol-qc.yaml
```

## Packaged protocol resource

The build command supplies `./resources` as the Pydra2App resources root. The
specification maps the resource directory named `protocol-qc-template` into the
container at:

```text
/opt/protocol-qc-template
```

The task receives this absolute path by default:

```text
/opt/protocol-qc-template/protocol-template.json
```

The implementation deliberately reads the JSON with `pathlib.Path` and does
not calculate a path relative to the Python package or repository. This is
important because the source repository's directory layout is not guaranteed
to exist inside a generated image.

Before building a release image, replace the example file at:

```text
resources/protocol-qc-template/protocol-template.json
```

with the approved template and validate its `Metadata.DictionaryVersion`.

## XNAT-conform DICOM access

The pipeline receives a session-level `frametree.core.row.DataRow` from the
Pydra2App XNAT Container Service entry point.

`xnat_io.iter_source_dicom_series()` performs the XNAT access sequence:

1. Trigger FrameTree population through `data_row.entries_dict`.
2. Iterate all session entries.
3. Select entries whose datatype is `DicomSeries`.
4. Exclude derivative entries.
5. Access `entry.item`, which causes FrameTree/XNAT to materialise or download
   the resource into the container cache.
6. Read local paths through `DicomSeries.contents`.

The original XNAT files are treated as read-only. ProtocolQC does not modify
input DICOM files.

## XNAT-conform report output

The report is first written to a unique temporary directory. For a non-dry run,
`xnat_io.write_session_report()` creates or reuses a derived FrameTree entry and
assigns a `fileformats.generic.File` object to it. This lets the XNAT store
adapter upload the report rather than using the XNAT REST API directly.

Default derivative path:

```text
ProtocolQC@protocol-qc
```

The exact XNAT resource label and overwrite behaviour must be validated in the
local `xnat4tests` sandbox before production use.

## Build

From `D:\repos\pipelines`:

```powershell
pydra2app make xnat `
    .\specs\ralfloeffler\quality-control\protocol-qc.yaml `
    --registry ghcr.io `
    --loglevel info `
    --resources-dir .\resources `
    --spec-root .\specs `
    --dont-check-registry `
    --source-package .
```

Expected image:

```text
ghcr.io/ralfloeffler/quality-control.protocol-qc:0.1.0-dev1
```

On Windows, the installed Pydra2App version may generate backslashes in a
Dockerfile `COPY` path. Until fixed upstream, inspect and patch the generated
Dockerfile or build through WSL2.

## First sandbox launch

Use explicit safe values:

```text
DryRun = true
FailOnDeviation = false
OutputResource = ProtocolQC@protocol-qc
ProtocolTemplate = /opt/protocol-qc-template/protocol-template.json
```

## TODO: DICOM extraction parity

- Port enhanced-MR Shared Functional Groups extraction from the Flywheel gear.
- Port Siemens private-header extraction.
- Port Phoenix protocol parsing.
- Port phase-encoding polarity extraction from in-plane rotation.
- Port MR spectroscopy handling.
- Port calculated FOV, resolution, and slice-gap fields.
- Define behaviour for standard single-frame MR Image Storage.
- Replace broad exception handling with explicit tag and format checks.
- Add synthetic enhanced-MR, spectroscopy, and Phoenix fixtures.

## TODO: comparison parity

- Port Multi-Echo comparison.
- Port `Temporal_positions_multiplier` logic.
- Port `Echo_lines_multiplier` logic.
- Port expected DICOM file-count checks.
- Preserve the rule that any matching approved candidate means the sequence
  passes.
- Define whether unexpected acquired sequences are warnings or failures.
- Define whether missing expected sequences are warnings or failures.
- Add schema validation for candidate protocols and acquisition parameters.

## TODO: sequence matching

- Confirm whether `SeriesDescription` remains the primary key.
- Add configurable normalisation for whitespace, case, and scanner suffixes.
- Decide whether `ProtocolName` is a fallback.
- Decide how duplicate sequence descriptions are represented.
- Define ordering and ordinal checks if the approved template requires them.

## TODO: XNAT integration

- Validate `DataRow.frequency_id("subject")` for the AIS medimage hierarchy.
- Validate that every original scan DICOM resource appears as a `DicomSeries`.
- Validate the report resource label generated by `ProtocolQC@protocol-qc`.
- Decide whether to overwrite, version, or reject an existing report.
- Decide whether PASS/FAIL should also be written to XNAT fields or assessor
  objects.
- Add an XNAT command-history-friendly summary to stdout.
- Add `xnat4tests` integration tests using synthetic DICOM only.
- Test sessions containing derived DICOM resources and confirm they are skipped.

## TODO: output and governance

- Finalise the JSON report schema and version it.
- Include source image version, Git commit, template checksum, and run timestamp.
- Avoid patient-identifying values in report and logs.
- Define exit-code policy for QC deviations versus processing failures.
- Define notification handling outside the processing task.
- Document template approval, versioning, and release procedure.

## Initial acceptance criteria

- The packaged JSON template is readable at the configured container path.
- Original XNAT DICOM entries are discovered without modification.
- Each original DICOM series is represented in the session report.
- Numeric, numeric-list, and string-list comparisons are unit tested.
- `DryRun=true` produces a complete report in stdout and no XNAT write.
- `DryRun=false` uploads exactly one session-level JSON report.
- No clinical identifiers are written to logs or reports.
