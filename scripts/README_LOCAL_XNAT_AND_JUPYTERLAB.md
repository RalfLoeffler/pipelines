# Local XNAT and JupyterLab Startup Guide

This guide describes how to start the local `xnat4tests` XNAT instance and run JupyterLab from the `ais-pipelines` Mamba environment on Windows.

## Prerequisites

- Docker Desktop installed and running
- Mamba environment named `ais-pipelines`
- `xnat4tests` installed in that environment
- JupyterLab installed in that environment
- AIS pipelines repository at:

```text
D:\repos\pipelines
```

## 1. Start Docker Desktop

Start Docker Desktop and wait until the Docker engine is running.

Verify it from PowerShell:

```powershell
docker version
```

You should see both a client and a server section.

## 2. Activate the AIS pipelines environment

Open PowerShell and run:

```powershell
mamba activate ais-pipelines
```

Verify the main commands:

```powershell
python --version
xnat4tests --help
docker version
```

If JupyterLab or the XNAT Python client is missing:

```powershell
python -m pip install jupyterlab xnat
```

If `xnat4tests` is missing:

```powershell
python -m pip install xnat4tests
```

## 3. Start the local XNAT instance

Start an empty XNAT test instance:

```powershell
xnat4tests start
```

The default local XNAT URL is normally:

```text
http://localhost:8080
```

Default credentials are normally:

```text
Username: admin
Password: admin
```

Open XNAT in the browser:

```powershell
Start-Process "http://localhost:8080"
```

Inspect the running containers:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 4. Optional: start XNAT with sample data

Instead of starting an empty instance, start it with the bundled dummy DICOM dataset:

```powershell
xnat4tests start --with-data dummydicom
```

Alternatively, add the sample data after XNAT is already running:

```powershell
xnat4tests add-data dummydicom
```

Do not run both unless you deliberately want to reload the sample data.

## 5. Confirm XNAT is reachable

Use the browser login as the primary functional test.

You can also test the endpoint from PowerShell:

```powershell
Invoke-WebRequest `
    -Uri "http://localhost:8080/data/JSESSION" `
    -Method Get `
    -UseBasicParsing
```


## 6. Use another port when port 8080 is already in use

If another service already uses port `8080`, create a separate `xnat4tests` configuration and assign a different port, for example `8081`.

First activate the environment:

```powershell
mamba activate ais-pipelines
```

Define paths for the default and alternate configurations:

```powershell
$DefaultConfig = "$HOME\.xnat4tests\configs\default.yaml"
$AltConfig = "$HOME\.xnat4tests\configs\port-8081.yaml"
```

Copy the default configuration:

```powershell
Copy-Item $DefaultConfig $AltConfig
```

Open the copied configuration in Notepad++:

```powershell
& 'C:\Program Files\Notepad++\notepad++.exe' $AltConfig
```

Change:

```yaml
xnat_port: 8080
```

to:

```yaml
xnat_port: 8081
```

If you intend to run more than one `xnat4tests` instance at the same time, also assign a unique container name and XNAT root directory. The exact property names must match those already present in your generated configuration. For example:

```yaml
xnat_port: 8081
docker_container: xnat4tests-8081
xnat_root_dir: C:\Users\YOUR_USERNAME\.xnat4tests\xnat_root\port-8081
```

Before starting the instance, confirm that the new port is unused:

```powershell
Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue
```

No output normally means that no active TCP listener is using the port.

Start XNAT with the alternate configuration:

```powershell
xnat4tests --config $AltConfig start
```

Open it in the browser:

```powershell
Start-Process "http://localhost:8081"
```

Inspect the active containers and published ports:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

For JupyterLab, use the alternate XNAT URL:

```powershell
mamba activate ais-pipelines
Set-Location D:\repos\pipelines

$env:XNAT_HOST = "http://localhost:8081"
$env:XNAT_USER = "admin"
$env:XNAT_PASS = "admin"

python -m jupyter lab
```

Stop the alternate instance using the same configuration:

```powershell
xnat4tests --config $AltConfig stop
```

Restart it with:

```powershell
xnat4tests --config $AltConfig restart
```

Keep using the same alternate configuration for all lifecycle commands so that `xnat4tests` manages the correct instance.

## 7. Start JupyterLab

Open a second PowerShell window.

Activate the environment and switch to the repository:

```powershell
mamba activate ais-pipelines
Set-Location D:\repos\pipelines
```

Set the XNAT connection variables for the current PowerShell session:

```powershell
$env:XNAT_HOST = "http://localhost:8080"
$env:XNAT_USER = "admin"
$env:XNAT_PASS = "admin"
```

Start JupyterLab:

```powershell
python -m jupyter lab
```

JupyterLab should open automatically. If it does not, copy the URL printed in the terminal, usually similar to:

```text
http://localhost:8888/lab?token=...
```

Keep this PowerShell window open while using JupyterLab.

## 8. Open the ProtocolQC notebook

Open:

```text
PROTOCOLQC_CREATE_TEMPLATE_FROM_XNAT_WITH_LIMITATIONS.ipynb
```

The notebook can read the connection values from:

```python
import os

XNAT_URL = os.environ["XNAT_HOST"]
XNAT_USER = os.environ["XNAT_USER"]
XNAT_PASS = os.environ["XNAT_PASS"]
```

## Complete startup sequence

### PowerShell window 1: XNAT

```powershell
mamba activate ais-pipelines

docker version

xnat4tests start

Start-Process "http://localhost:8080"

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### PowerShell window 1 with sample data

```powershell
mamba activate ais-pipelines

docker version

xnat4tests start --with-data dummydicom

Start-Process "http://localhost:8080"

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### PowerShell window 2: JupyterLab

```powershell
mamba activate ais-pipelines

Set-Location D:\repos\pipelines

$env:XNAT_HOST = "http://localhost:8080"
$env:XNAT_USER = "admin"
$env:XNAT_PASS = "admin"

python -m jupyter lab
```

## Stop JupyterLab

In the JupyterLab PowerShell window, press:

```text
Ctrl+C
```

Confirm shutdown if prompted.

## Stop XNAT

In a PowerShell window:

```powershell
mamba activate ais-pipelines
xnat4tests stop
```

Restart later with:

```powershell
mamba activate ais-pipelines
xnat4tests restart
```

## Recommended daily workflow

Start XNAT:

```powershell
mamba activate ais-pipelines
xnat4tests start
```

Start JupyterLab in another PowerShell window:

```powershell
mamba activate ais-pipelines
Set-Location D:\repos\pipelines

$env:XNAT_HOST = "http://localhost:8080"
$env:XNAT_USER = "admin"
$env:XNAT_PASS = "admin"

python -m jupyter lab
```

Stop XNAT when finished:

```powershell
mamba activate ais-pipelines
xnat4tests stop
```

## Notes

- The environment variables shown here are temporary and only apply to the PowerShell process in which they are set.
- Do not commit real production XNAT credentials to source control or notebooks.
- The local `admin` / `admin` credentials are suitable only for the local test instance.
- JupyterLab runs outside XNAT and connects through the XNAT REST API.
