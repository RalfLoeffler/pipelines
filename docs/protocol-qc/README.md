# ProtocolQC Framework

## Status

Framework only. Protocol comparison and XNAT output behaviour are not implemented.
The task raises `NotImplementedError` deliberately so an unfinished pipeline cannot
be mistaken for a successful quality-control result.

## Repository locations

- Python entry point:
  `src/australianimagingservice/quality_control/protocol_qc/workflow.py`
- Public import:
  `australianimagingservice.quality_control.protocol_qc:protocol_qc`
- Pydra2App/XNAT specification:
  `specs/australian-imaging-service/quality-control/protocol-qc.yaml`
- Pipeline-specific requirements:
  `requirements/quality-control/protocol-qc.txt`
- Tests:
  `src/australianimagingservice/quality_control/protocol_qc/tests/`

## Decisions still required

1. Protocol source and format, for example JSON, YAML, XML, or an XNAT resource.
2. Sequence matching rules, including naming aliases and optional sequences.
3. Parameters to compare, such as TR, TE, TI, flip angle, voxel size, acceleration,
   orientation, acquisition time, and number of averages.
4. Absolute and relative tolerance rules per parameter.
5. Handling of missing, duplicated, and unexpected series.
6. Report schema and pass/warn/fail severity model.
7. XNAT output destination, for example a session resource or assessor.
8. Whether failure should affect the container exit code.
9. PHI handling and logging restrictions.
10. Synthetic test fixtures and acceptance criteria.

## Install the framework into the pipelines clone

From `D:\repos\pipelines`, copy the framework files into the same relative paths,
or run the included PowerShell installer from the extracted framework directory.

```powershell
.\scripts\Install-ProtocolQcFramework.ps1 `
    -PipelinesRepository D:\repos\pipelines
```

## Validate imports and tests

```powershell
Set-Location D:\repos\pipelines
mamba activate ais-pipelines

python -c "from australianimagingservice.quality_control.protocol_qc import protocol_qc; print(protocol_qc)"
python -m pytest .\src\australianimagingservice\quality_control\protocol_qc\tests -v
python -m black --check .\src\australianimagingservice\quality_control\protocol_qc
python -m flake8 .\src\australianimagingservice\quality_control\protocol_qc
```

## Build the development image

```powershell
pydra2app make xnat `
    .\specs\australian-imaging-service\quality-control\protocol-qc.yaml `
    --registry ghcr.io `
    --loglevel info `
    --resources-dir .\resources `
    --spec-root .\specs `
    --dont-check-registry `
    --source-package .
```

The expected image name is:

```text
ghcr.io/australian-imaging-service/quality-control.protocol-qc:0.1.0-dev1
```

Do not enable the generated command in a production project. Until implementation,
a launch is expected to fail with `NotImplementedError`.

## CI integration

The upstream release workflow builds only specifications listed in its matrix. Add
`quality-control/protocol-qc` to the matrix only after local build validation and
once the cost and intended CI trigger have been reviewed.
