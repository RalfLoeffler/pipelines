# ProtocolQC XNAT Pipeline

## Purpose

ProtocolQC checks DICOM acquisition parameters from an XNAT imaging session
against a project-specific approved JSON protocol template.

## Protocol template location

The template is **not included in the container image**. Each XNAT project must
provide it as a project-level resource file.

Default location:

```text
Project resource label: ProtocolQC
Filename:               protocol-template.json
```

XNAT documents project resource files at:

```text
GET /data/projects/{project-id}/resources/{resource-label}/files/{filename}
```

The pipeline downloads that file at runtime using the temporary credentials
injected by XNAT Container Service:

```text
XNAT_HOST
XNAT_USER
XNAT_PASS
```

Do not place permanent XNAT credentials in the image, source code, YAML, or
project resource JSON.

## XNAT file access

- DICOM scan resources are accessed through the FrameTree `DataRow` and
  `entry.item` interfaces.
- The project-level JSON template is accessed through the documented XNAT REST
  project-resource endpoint because it is above the selected session row.
- The session-level output report is written through
  `data_row.create_entry(...)`, not through a hard-coded archive path.

## Uploading the template in XNAT

1. Open the target project.
2. Open the project resources/files interface.
3. Create a project resource named `ProtocolQC`.
4. Upload the approved JSON as `protocol-template.json`.
5. Confirm that the account launching the container can read the project file.

The resource label and filename can be overridden in the XNAT launch dialog.

## Build on Windows

The installed Pydra2App version may generate a Docker `COPY` source containing
Windows backslashes, for example:

```text
python-packages\australianimagingservice-....tar.gz
```

Docker requires `/` inside Dockerfile paths. Use the supplied wrapper, which
runs Pydra2App and automatically patches the generated Dockerfile if this known
Windows-only failure occurs.

Before running downloaded PowerShell scripts:

```powershell
Get-ChildItem .\scripts\*.ps1 | Unblock-File
```

Build:

```powershell
.\scripts\Build-ProtocolQc.ps1 `
    -RepositoryRoot D:\repos\pipelines `
    -AuthorEmail "YOUR_EMAIL_ADDRESS"
```

## First sandbox launch

Use:

```text
ProjectResourceLabel     ProtocolQC
ProtocolTemplateFilename protocol-template.json
OutputResource           ProtocolQC@protocol-qc
FailOnDeviation          false
DryRun                   true
```

## TODO

### Template contract

- Replace the example/test template with the approved production schema.
- Add JSON Schema validation.
- Define supported `DictionaryVersion` upgrade rules.
- Decide whether multiple templates per project are supported.
- Decide how scanner/model-specific alternatives are selected.

### DICOM extraction parity

- Port enhanced MR functional-group extraction from the Flywheel gear.
- Port Siemens private-tag extraction.
- Port Phoenix protocol and phase-encoding polarity extraction.
- Add MR spectroscopy handling.
- Validate multi-echo combination logic.
- Validate temporal-position and echo multipliers.
- Define behaviour for regular MR Image Storage versus Enhanced MR.

### XNAT integration

- Test project-resource download in `xnat4tests`.
- Confirm the project ID obtained from `data_row.frameset.id` for all launch
  contexts.
- Confirm alias-token permissions for project resources.
- Validate missing resource, missing file, 401, 403, and 404 messages.
- Validate report resource naming and overwrite/versioning behaviour.
- Decide whether a failed QC should also update XNAT metadata or create an
  assessor.

### Testing

- Add a synthetic enhanced-MR fixture.
- Add PASS and FAIL protocol templates.
- Add malformed JSON and unsupported dictionary-version tests.
- Add an integration test that uploads a project resource to `xnat4tests`.
- Confirm source DICOM is never modified.
- Confirm logs do not expose credentials or PHI.

### Build and release

- Report the Windows Dockerfile path bug upstream to Pydra2App.
- Replace the workaround when the upstream release is fixed.
- Pin runtime package versions before the first release.
- Add a GitHub Actions build for the personal GHCR namespace.
