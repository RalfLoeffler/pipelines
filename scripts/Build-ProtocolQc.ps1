[CmdletBinding()]
param(
    [Parameter()]
    [string]$RepositoryRoot = "D:\repos\pipelines",

    [Parameter(Mandatory)]
    [string]$AuthorEmail,

    [Parameter()]
    [string]$Image = "ghcr.io/ralfloeffler/quality-control.protocol-qc:0.1.0-dev2"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$specPath = Join-Path $RepositoryRoot `
    "specs\ralfloeffler\quality-control\protocol-qc.yaml"
$buildDirectory = Join-Path $RepositoryRoot `
    "specs\ralfloeffler\quality-control\.build-protocol-qc"
$dockerfilePath = Join-Path $buildDirectory "Dockerfile"

if (-not (Test-Path $specPath -PathType Leaf)) {
    throw "ProtocolQC specification not found: $specPath"
}

$specContent = Get-Content $specPath -Raw
$specContent = $specContent.Replace(
    "ralf.loeffler@unsw.edu.au",
    $AuthorEmail
)
Set-Content $specPath $specContent -Encoding utf8

Set-Location $RepositoryRoot
Remove-Item $buildDirectory -Recurse -Force -ErrorAction SilentlyContinue

& pydra2app make xnat `
    $specPath `
    --registry ghcr.io `
    --loglevel info `
    --resources-dir (Join-Path $RepositoryRoot "resources") `
    --spec-root (Join-Path $RepositoryRoot "specs") `
    --dont-check-registry `
    --source-package $RepositoryRoot

if ($LASTEXITCODE -eq 0) {
    Write-Host "ProtocolQC image built successfully: $Image"
    exit 0
}

if (-not (Test-Path $dockerfilePath -PathType Leaf)) {
    throw "pydra2app failed and no generated Dockerfile was found."
}

Write-Warning "pydra2app build failed. Applying Windows Docker COPY path workaround."
$dockerfile = Get-Content $dockerfilePath -Raw
$patchedDockerfile = $dockerfile.Replace("python-packages\", "python-packages/")

if ($patchedDockerfile -eq $dockerfile) {
    throw "The expected Windows python-packages path was not found in Dockerfile."
}

Set-Content $dockerfilePath $patchedDockerfile -Encoding utf8

& docker build `
    --tag $Image `
    --file $dockerfilePath `
    $buildDirectory

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed after applying the Windows path workaround."
}

Write-Host "ProtocolQC image built successfully: $Image"
