# %% [markdown]
# # XNATpy Scan Object Inspection Guide
#
# This self-contained notebook demonstrates how to inspect XNAT scan objects with **XNATpy**.
#
# It covers:
#
# - connecting to XNAT;
# - selecting a project, subject, session, and scan;
# - inspecting scan properties, methods, resources, files, and custom fields;
# - retrieving DICOM metadata with `dicom_dump()`;
# - inspecting underlying REST data;
# - using a reusable object-inspection helper;
# - ProtocolQC-focused checks;
# - safe connection cleanup.
#
# The notebook is suitable for a local `xnat4tests` instance and can also be adapted to other XNAT servers.
#

# %% [markdown]
# ## 1. Prerequisites
#
# Activate the AIS development environment and install the required packages if needed.
# Note that there are two mamba installations/env places, one that is started with powershell and one with miniforge
#
# ```powershell
# mamba activate ais-pipelines
# python -m pip install xnat jupyterlab
# ```
#
# once env is active, start ```docker desktop``` and then:
# ```powershell
# xnat4tests start --with-data dummydicom
# $env:XNAT_HOST = "http://localhost:8080"
# $env:XNAT_USER = "admin"
# $env:XNAT_PASS = "admin"
# Start-Process "http://localhost:8080"
# python -m jupyter lab
# ```
#
# to stop: 
# ```powershell
# xnat4tests stop   
# ```
#
# Typical local `xnat4tests` settings are:
#
# - URL: `http://localhost:8080`
# - Username: `admin`
# - Password: `admin`
#
# Use the actual port shown by Docker when your instance runs on another port.
#

# %%
import inspect
import os
from getpass import getpass
from pprint import pprint
from typing import Any

import xnat

print("XNATpy imported successfully.")


# %% [markdown]
# ## 2. Configure the connection
#
# The notebook first reads:
#
# - `XNAT_HOST`
# - `XNAT_USER`
# - `XNAT_PASS`
#
# When no password is present, it prompts securely.
#

# %%
XNAT_URL = os.environ.get("XNAT_HOST", "http://localhost:8080").rstrip("/")
XNAT_USER = os.environ.get("XNAT_USER", "admin")
XNAT_PASS = os.environ.get("XNAT_PASS")

if not XNAT_PASS:
    XNAT_PASS = getpass(f"Password for {XNAT_USER}@{XNAT_URL}: ")

print(f"XNAT URL: {XNAT_URL}")
print(f"XNAT user: {XNAT_USER}")


# %% [markdown]
# ## 3. Connect with XNATpy
#
# XNATpy handles authentication, session cookies, and generated XNAT objects.
#

# %%
xnat_connection = xnat.connect(
    XNAT_URL,
    user=XNAT_USER,
    password=XNAT_PASS,
)

print("Connected to XNAT.")


# %% [markdown]
# ## 4. List projects
#
# Project IDs may differ from names displayed in the XNAT interface.
#

# %%
project_ids = list(xnat_connection.projects.keys())

if not project_ids:
    raise RuntimeError("No projects are visible to the current XNAT user.")

# # !r means format as repr instead of string 
for project_id, project_obj in xnat_connection.projects.items():
    print(
        f"ID={project_id!r}, "
        f"name={getattr(project_obj, 'name', None)!r}, "
        f"secondary_id={getattr(project_obj, 'secondary_id', None)!r}"
    )


# %%
# get the first value/key pair:
first_project_id, first_project_obj = list(xnat_connection.projects.items())[0]
# below only other definitions are used
project_obj = first_project_obj
project_id = first_project_id


# %%
print(type(first_project_obj))

import inspect

# print(dir(first_project_obj))
for attr in dir(first_project_obj):
    print(attr)

# from pprint import pprint

# pprint(first_project_obj.__dict__)


# %%
for attr in dir(project_obj):
    if not attr.startswith("_"):
        try:
            value = getattr(first_project_obj, attr)
            print(f"{attr} = {value!r}")
        except Exception as e:
            print(f"{attr} = <ERROR: {e}>")

# %%
import inspect
from pprint import pprint

print("=" * 80)
print("OBJECT TYPE")
print("=" * 80)
print(type(project_obj))

print("\n" + "=" * 80)
print("RAW INSTANCE DATA (__dict__)")
print("=" * 80)

try:
    pprint(project_obj.__dict__)
except Exception as e:
    print(f"Could not read __dict__: {e}")

print("\n" + "=" * 80)
print("ATTRIBUTE INSPECTION")
print("=" * 80)

for attr in sorted(dir(project_obj)):
    if attr.startswith("_"):
        continue

    try:
        value = getattr(project_obj, attr)

        # Avoid printing huge collections
        value_repr = repr(value)
        if len(value_repr) > 200:
            value_repr = value_repr[:200] + "..."

        print(f"{attr}: {value_repr}")

    except Exception as e:
        print(f"{attr}: ERROR -> {type(e).__name__}: {e}")

        # Inspect the attribute without triggering lazy loading
        try:
            static_obj = inspect.getattr_static(project_obj, attr)
            print(f"    STATIC TYPE : {type(static_obj)}")
            print(f"    STATIC REPR : {static_obj!r}")
        except Exception as e2:
            print(f"    STATIC ERROR: {e2}")

print("\n" + "=" * 80)
print("PROPERTIES DEFINED ON CLASS")
print("=" * 80)

for name, obj in sorted(type(project_obj).__dict__.items()):
    if isinstance(obj, property):
        print(f"{name}:")
        print(f"    fget = {obj.fget}")
        print(f"    fset = {obj.fset}")
        print(f"    fdel = {obj.fdel}")

# %%
print(type(project_obj))

for name in ["data", "fulldata"]:
    if hasattr(project_obj, name):
        print(f"\n{name}:")
        pprint(getattr(project_obj, name))

# %%
from pprint import pprint

for section, value in project_obj.fulldata.items():
    print(f"\n=== {section} ===")
    pprint(value)

# %%
from pprint import pprint

pprint(project_obj.fulldata)

# %%
dir(project_obj)

# %%
pprint(project_obj.fulldata["children"])

# %%
# FInd potential children
for attr in sorted(dir(project_obj)):
    if attr.startswith("_"):
        continue

    try:
        value = getattr(project_obj, attr)

        if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
            print(attr, type(value))
    except Exception:
        pass

# %%
# known children
print("subjects:", type(project_obj.subjects))
print("experiments:", type(project_obj.experiments))
print("resources:", type(project_obj.resources))
print("files:", type(project_obj.files))

# %%
print(list(project_obj.subjects.keys()))
print(list(project_obj.experiments.keys()))
print(list(project_obj.resources.keys()))
# files get the files uploaded, e.g. the protocol template
print(list(project_obj.files.keys()))

# %%
for subject_id, subject_obj in project_obj.subjects.items():
    print(subject_id)

# %%
for attr in sorted(dir(project_obj)):
    if attr.startswith("_"):
        continue

    try:
        value = getattr(project_obj, attr)

        if isinstance(value, (dict, list, tuple)):
            print(f"{attr}: {type(value)} len={len(value)}")
    except Exception:
        pass

# %%

# %%

# %%

# %% [markdown]
# ## 5. Select a project
#
# The first visible project is selected by default. Replace `PROJECT_ID` as needed.
#

# %%
PROJECT_ID = project_ids[0]

if PROJECT_ID not in xnat_connection.projects:
    raise KeyError(
        f"Project {PROJECT_ID!r} is not available. "
        f"Available IDs: {project_ids}"
    )

project = xnat_connection.projects[PROJECT_ID]

print("Selected project")
print("ID:", getattr(project, "id", PROJECT_ID))
print("Name:", getattr(project, "name", None))
print("URI:", getattr(project, "uri", None))


# %% [markdown]
# ## 6. List and select a subject
#

# %%
subject_ids = list(project.subjects.keys())

if not subject_ids:
    raise RuntimeError(f"No subjects found in project {PROJECT_ID!r}.")

for subject_id, subject_obj in project.subjects.items():
    print(
        f"ID={subject_id!r}, "
        f"label={getattr(subject_obj, 'label', None)!r}, "
        f"URI={getattr(subject_obj, 'uri', None)!r}"
    )

SUBJECT_ID = subject_ids[0]
subject = project.subjects[SUBJECT_ID]

print("\nSelected subject:", SUBJECT_ID)


# %% [markdown]
# ## 7. List and select a session or experiment
#
# XNATpy normally exposes sessions through `subject.experiments`.
#

# %%
experiment_ids = list(subject.experiments.keys())

if not experiment_ids:
    raise RuntimeError(f"No experiments found for subject {SUBJECT_ID!r}.")

for experiment_id, experiment_obj in subject.experiments.items():
    print(
        f"ID={experiment_id!r}, "
        f"label={getattr(experiment_obj, 'label', None)!r}, "
        f"type={type(experiment_obj).__name__}, "
        f"URI={getattr(experiment_obj, 'uri', None)!r}"
    )

SESSION_ID = experiment_ids[0]
session = subject.experiments[SESSION_ID]

print("\nSelected session:", SESSION_ID)


# %% [markdown]
# ## 8. List and select a scan
#
# Scan IDs are often numeric strings such as `"1"`.
#

# %%
if not hasattr(session, "scans"):
    raise AttributeError("The selected session does not expose scans.")

scan_ids = list(session.scans.keys())

if not scan_ids:
    raise RuntimeError(f"No scans found in session {SESSION_ID!r}.")

for scan_id, scan_obj in session.scans.items():
    print(
        f"ID={scan_id!r}, "
        f"type={getattr(scan_obj, 'type', None)!r}, "
        f"series_description={getattr(scan_obj, 'series_description', None)!r}, "
        f"quality={getattr(scan_obj, 'quality', None)!r}"
    )

SCAN_ID = scan_ids[0]
scan = session.scans[SCAN_ID]

print("\nSelected scan:", SCAN_ID)
print("Python type:", type(scan))


# %% [markdown]
# ## 9. Common scan properties
#
# Not every XNAT version or scan class exposes every property. `getattr(..., None)` avoids unnecessary failures.
#

# %%
common_properties = (
    "id",
    "label",
    "type",
    "series_description",
    "quality",
    "frames",
    "note",
    "uri",
    "xsi_type",
)

for name in common_properties:
    try:
        value = getattr(scan, name)
    except Exception as exc:
        value = f"<error: {exc}>"
    print(f"{name}: {value!r}")


# %% [markdown]
# ## 10. List all public attributes and methods
#

# %%
public_names = sorted(
    name for name in dir(scan)
    if not name.startswith("_")
)

print(f"Public names: {len(public_names)}")
for name in public_names:
    print(name)


# %% [markdown]
# ## 11. Separate values from methods
#
# Some generated properties may perform REST requests when accessed. Errors are captured so inspection can continue.
#

# %% [markdown]
# ### Why safe formatting is required
#
# XNATpy collections are often **lazy listings**. Their `__str__()` and `__repr__()` methods may issue REST requests. Passing such objects directly to `pprint()` can therefore trigger unexpected queries.
#
# In this notebook, lazy XNATpy objects are represented by a short summary containing their class and URI rather than being automatically expanded. Enumerate a known collection explicitly only when you intend to query it.
#

# %%
def safe_xnat_value(value: Any) -> Any:
    """Return a representation that does not evaluate lazy XNATpy listings."""

    value_type = type(value)
    module_name = getattr(value_type, "__module__", "")
    class_name = getattr(value_type, "__name__", "")

    # XNATpy listing objects may perform REST calls from __str__ or __repr__.
    if module_name.startswith("xnat") and "Listing" in class_name:
        uri = getattr(value, "uri", None)
        return f"<{class_name} lazy XNAT listing; uri={uri!r}>"

    # Generated XNAT objects can also have expensive or network-backed repr().
    if module_name.startswith("xnat"):
        uri = getattr(value, "uri", None)
        object_id = getattr(value, "id", None)
        return (
            f"<{class_name} XNAT object; "
            f"id={object_id!r}; uri={uri!r}>"
        )

    # Preserve simple built-in values.
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return f"<{type(value).__name__} length={len(value)}>"

    if isinstance(value, dict):
        return f"<dict length={len(value)}>"

    # Avoid calling arbitrary repr() methods.
    return f"<{class_name or type(value).__name__}>"


print("Safe XNAT value formatter defined.")

# %%
public_values: dict[str, Any] = {}
public_methods: list[str] = []

for name in public_names:
    try:
        value = getattr(scan, name)
    except Exception as exc:
        public_values[name] = f"<error while reading attribute: {exc}>"
        continue

    if callable(value):
        public_methods.append(name)
    else:
        public_values[name] = safe_xnat_value(value)

print("Public values:")
for name, value in public_values.items():
    print(f"{name}: {value}")

print("\nPublic methods:")
for name in public_methods:
    print(name)


# %% [markdown]
# ## 12. Inspect method signatures
#

# %%
for method_name in public_methods:
    try:
        method = getattr(scan, method_name)
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = "(signature unavailable)"
    except Exception as exc:
        signature = f"(error: {exc})"

    print(f"{method_name}{signature}")


# %% [markdown]
# ## 13. Display generated help
#
# Uncomment one call at a time because help output can be large.
#

# %%
# help(scan)
# help(scan.download)
# help(scan.dicom_dump)


# %% [markdown]
# ## 14. Inspect scan resources
#
# A typical MRI scan has a resource labelled `DICOM`, but resource labels can vary.
#

# %%
if not hasattr(scan, "resources"):
    raise AttributeError("The selected scan does not expose resources.")

resource_labels = list(scan.resources.keys())
print("Resource labels:", resource_labels)

for resource_label, resource in scan.resources.items():
    print(
        f"Resource={resource_label!r}, "
        f"type={type(resource).__name__}, "
        f"URI={getattr(resource, 'uri', None)!r}"
    )


# %% [markdown]
# ## 15. Inspect files in each resource
#

# %%
for resource_label, resource in scan.resources.items():
    print(f"\nResource: {resource_label}")
    try:
        file_items = resource.files.items()
    except Exception as exc:
        print(f"  Could not list files: {exc}")
        continue

    count = 0
    for file_name, file_obj in file_items:
        count += 1
        print(
            f"  {file_name!r} | "
            f"size={getattr(file_obj, 'size', None)!r} | "
            f"format={getattr(file_obj, 'format', None)!r} | "
            f"content={getattr(file_obj, 'content', None)!r} | "
            f"URI={getattr(file_obj, 'uri', None)!r}"
        )
    print("  Total files:", count)


# %% [markdown]
# ## 16. Inspect custom fields
#
# Generated classes may expose custom variables through `fields` or `field`.
#

# %%
scan_fields = getattr(scan, "fields", None)
if scan_fields is None:
    scan_fields = getattr(scan, "field", None)

if scan_fields is None:
    print("No custom field interface is exposed.")
else:
    try:
        field_names = list(scan_fields)
    except Exception as exc:
        print(f"Could not enumerate custom fields: {exc}")
        field_names = []

    for field_name in field_names:
        try:
            field_value = scan_fields[field_name]
        except Exception as exc:
            field_value = f"<error: {exc}>"
        print(f"{field_name}: {field_value!r}")


# %% [markdown]
# ## 17. Retrieve a complete DICOM metadata dump
#
# `dicom_dump()` is useful for exploration. ProtocolQC production extraction should still use the shared `pydicom` implementation.
#

# %%
if not hasattr(scan, "dicom_dump"):
    print("This scan object does not expose dicom_dump().")
else:
    try:
        dicom_metadata = scan.dicom_dump()
        pprint(dicom_metadata)
    except Exception as exc:
        print(f"dicom_dump() failed: {exc}")


# %% [markdown]
# ## 18. Request selected DICOM fields
#

# %%
selected_dicom_fields = [
    "SeriesDescription",
    "ProtocolName",
    "RepetitionTime",
    "EchoTime",
    "MagneticFieldStrength",
    "SliceThickness",
    "PixelSpacing",
]

if hasattr(scan, "dicom_dump"):
    try:
        selected_metadata = scan.dicom_dump(fields=selected_dicom_fields)
        pprint(selected_metadata)
    except Exception as exc:
        print(f"Selected-field DICOM dump failed: {exc}")


# %% [markdown]
# ## 19. Request one DICOM field
#

# %%
if hasattr(scan, "dicom_dump"):
    try:
        pprint(scan.dicom_dump(fields="SeriesDescription"))
    except Exception as exc:
        print(f"Single-field DICOM dump failed: {exc}")


# %% [markdown]
# ## 20. Inspect generated object data
#
# Some XNATpy versions expose a public `data` property.
#

# %%
if hasattr(scan, "data"):
    try:
        pprint(scan.data)
    except Exception as exc:
        print(f"Could not read scan.data: {exc}")
else:
    print("No public data property is exposed.")


# %% [markdown]
# ## 21. Generic REST inspection through XNATpy
#
# This is useful when an endpoint is not wrapped by a convenient object method.
#

# %%
scan_uri = getattr(scan, "uri", None)

if not scan_uri:
    print("The scan has no exposed URI.")
else:
    try:
        raw_response = xnat_connection.get(
            scan_uri,
            query={"format": "json"},
        )
        print("Response type:", type(raw_response))
        pprint(raw_response)
    except Exception as exc:
        print(f"Generic REST request failed: {exc}")


# %% [markdown]
# ## 22. Reusable inspection helper
#
# This helper works with projects, subjects, sessions, scans, resources, and files.
#

# %%
def inspect_xnat_object(obj: Any) -> None:
    """Inspect an XNATpy object without expanding lazy listings.

    This helper deliberately avoids calling getattr() for every name returned by
    dir(). Generated XNATpy properties may trigger REST requests merely by being
    accessed. Instead, it reads a curated set of common properties and uses
    inspect.getattr_static() to discover methods and descriptors safely.
    """

    print("=" * 80)
    print("Object summary")
    print("=" * 80)
    print(safe_xnat_value(obj))

    print("\nPython type")
    print("-" * 80)
    print(type(obj))

    print("\nCurated properties")
    print("-" * 80)

    common_names = (
        "id",
        "label",
        "name",
        "uri",
        "xsi_type",
        "type",
        "series_description",
        "quality",
        "frames",
        "note",
        "size",
        "format",
        "content",
    )

    for name in common_names:
        try:
            value = getattr(obj, name)
        except AttributeError:
            continue
        except Exception as exc:
            print(f"{name}: <error while reading property: {exc}>")
            continue

        print(f"{name}: {safe_xnat_value(value)}")

    print("\nStatically discovered public names")
    print("-" * 80)

    method_names = []
    descriptor_names = []
    other_names = []

    for name in sorted(dir(obj)):
        if name.startswith("_"):
            continue

        try:
            static_value = inspect.getattr_static(obj, name)
        except Exception as exc:
            other_names.append(f"{name} <static inspection error: {exc}>")
            continue

        if callable(static_value):
            method_names.append(name)
        elif isinstance(static_value, property):
            descriptor_names.append(name)
        else:
            other_names.append(name)

    print("Methods:")
    for name in method_names:
        print(f"  {name}")

    print("\nProperties/descriptors not automatically evaluated:")
    for name in descriptor_names:
        print(f"  {name}")

    print("\nOther public names not automatically evaluated:")
    for name in other_names:
        print(f"  {name}")

    print("\nKnown collection handles")
    print("-" * 80)

    for collection_name in (
        "projects",
        "subjects",
        "experiments",
        "scans",
        "resources",
        "files",
    ):
        try:
            static_value = inspect.getattr_static(obj, collection_name)
        except AttributeError:
            continue
        except Exception as exc:
            print(f"{collection_name}: <static inspection error: {exc}>")
            continue

        # Report that a collection exists without evaluating it.
        print(
            f"{collection_name}: present as "
            f"{type(static_value).__name__}; not enumerated automatically"
        )



# %% [markdown]
# ## 23. Run the safe helper on the selected scan
#
# This helper now performs only curated property reads and static class inspection. It does not automatically evaluate all generated XNATpy properties or enumerate lazy collections.
#

# %%
inspect_xnat_object(scan)


# %% [markdown]
# ## 24. Inspect related objects safely
#
# The session and one explicitly selected scan resource are inspected without traversing `resource.files`. Automatic file enumeration is avoided because some XNATpy versions expect a `ResultSet` response from an endpoint that this XNAT instance returns in a different JSON structure.
#

# %%
# Inspect the parent session using curated/static inspection.
inspect_xnat_object(session)

# Inspect one explicitly selected resource without enumerating its file listing.
if resource_labels:
    selected_resource_label = resource_labels[0]

    try:
        selected_resource = scan.resources[selected_resource_label]
    except Exception as exc:
        print(
            f"Could not retrieve resource {selected_resource_label!r}: {exc}"
        )
    else:
        print(f"\nSelected resource: {selected_resource_label!r}")
        inspect_xnat_object(selected_resource)

        print(
            "\nThe resource.files collection is intentionally not enumerated here. "
            "In this XNAT/XNATpy combination, evaluating that lazy listing can "
            "query a /file endpoint whose response is not in ResultSet format."
        )
else:
    print("The selected scan has no resource labels to inspect.")


# %% [markdown]
# ### Accessing files without triggering the problematic listing
#
# For ProtocolQC work, prefer downloading the complete DICOM resource through the resource object rather than introspecting every file object. Inspect the signature first:
#

# %%
if resource_labels:
    selected_resource = scan.resources[resource_labels[0]]

    download_method = getattr(selected_resource, "download", None)
    if download_method is None:
        print("The selected resource does not expose download().")
    else:
        try:
            print("download signature:", inspect.signature(download_method))
        except (TypeError, ValueError):
            print("download() exists, but its signature is unavailable.")

# Example only; uncomment and provide a destination after reviewing the signature.
# selected_resource.download(r"D:\\temp\\xnat-scan-resource")


# %% [markdown]
# ## 25. ProtocolQC-focused checks
#
# These checks establish whether the scan and its DICOM resource expose the information needed for further ProtocolQC development.
#

# %%
protocol_qc_summary = {
    "scan_id": getattr(scan, "id", None),
    "scan_type": getattr(scan, "type", None),
    "series_description": getattr(scan, "series_description", None),
    "quality": getattr(scan, "quality", None),
    "resource_labels": list(scan.resources.keys())
    if hasattr(scan, "resources")
    else [],
}

pprint(protocol_qc_summary)

dicom_candidates = [
    label
    for label in protocol_qc_summary["resource_labels"]
    if label.upper() == "DICOM"
]

if dicom_candidates:
    print("DICOM resource found:", dicom_candidates[0])
else:
    print("No resource labelled exactly 'DICOM' was found.")

if hasattr(scan, "dicom_dump"):
    try:
        protocol_qc_metadata = scan.dicom_dump(
            fields=[
                "SeriesDescription",
                "ProtocolName",
                "RepetitionTime",
                "EchoTime",
            ]
        )
        pprint(protocol_qc_metadata)
    except Exception as exc:
        print(f"Could not retrieve ProtocolQC metadata fields: {exc}")


# %% [markdown]
# ## 26. ProtocolQC interpretation note
#
# `scan.dicom_dump()` is useful for discovery, but it should not be the authoritative extraction route for ProtocolQC.
#
# The same shared `pydicom` extraction implementation should be used for:
#
# 1. generating an approved template from a reference session; and
# 2. validating subsequent acquisitions.
#
# This avoids differences between template generation and QC execution, especially for enhanced MR functional groups and Siemens private tags.
#

# %% [markdown]
# ## 27. Close the connection
#

# %%
xnat_connection.disconnect()
print("XNAT connection closed.")


# %% [markdown]
# ## Troubleshooting
#
# ### No projects are listed
#
# Confirm the URL, port, credentials, and project permissions.
#
# ### No scans are exposed
#
# The selected experiment may not be an MR session, or it may contain no scans.
#
# ### No `DICOM` resource exists
#
# Inspect `scan.resources.keys()` because resource labels can vary.
#
# ### `dicom_dump()` fails
#
# The method may not be supported for that object or server version. Download the DICOM resource and inspect it with `pydicom`.
#
# ### Jupyter cannot reach local XNAT
#
# Check the mapped port:
#
# ```powershell
# docker ps --format "table {{.Names}}\t{{.Ports}}"
# ```
#
# Then launch Jupyter with the matching host:
#
# ```powershell
# $env:XNAT_HOST = "http://localhost:8081"
# $env:XNAT_USER = "admin"
# $env:XNAT_PASS = "admin"
# python -m jupyter lab
# ```
#

# %% [markdown]
# # Additional pydicom examples
#
# The following sections show how to move from XNATpy object inspection to direct DICOM inspection with `pydicom`.
#
# These examples are especially relevant for ProtocolQC because the production extractor should interpret the original DICOM files directly rather than relying only on XNAT's indexed metadata.
#
# The examples cover:
#
# - downloading a scan resource;
# - locating DICOM files in folders or ZIP archives;
# - reading headers without pixel data;
# - accessing DICOM elements safely;
# - inspecting public and private tags;
# - traversing enhanced-MR functional groups;
# - comparing values across a series;
# - identifying derived images;
# - checking SOP Class UIDs;
# - extracting selected metadata into a table;
# - exporting metadata to JSON.
#

# %% [markdown]
# ## Install pydicom if required
#
# ```powershell
# mamba activate ais-pipelines
# python -m pip install pydicom pandas
# ```
#

# %%
from collections import Counter, defaultdict
from pathlib import Path
import json
import tempfile
import zipfile

import pandas as pd
import pydicom
from pydicom.dataset import Dataset
from pydicom.errors import InvalidDicomError

print("pydicom version:", pydicom.__version__)


# %% [markdown]
# ## Download the selected scan resource
#
# This example looks for a scan resource labelled `DICOM` and downloads it into a temporary directory.
#
# XNATpy resource download behaviour can vary slightly by version. The code therefore prints the resulting path and then handles either a directory or ZIP archive.
#

# %%
download_root = Path(tempfile.mkdtemp(prefix="xnat-pydicom-"))
print("Download root:", download_root)

print("Available scan resource keys:", list(scan.resources.keys()))

dicom_resource = None
dicom_resource_key = None

for resource_key in scan.resources.keys():
    try:
        resource_obj = scan.resources[resource_key]
    except Exception as exc:
        print(f"Could not access resource {resource_key!r}: {exc}")
        continue

    resource_label = getattr(resource_obj, "label", None)
    resource_format = getattr(resource_obj, "format", None)
    resource_content = getattr(resource_obj, "content", None)
    resource_uri = getattr(resource_obj, "uri", None)

    print(
        f"key={resource_key!r}, "
        f"label={resource_label!r}, "
        f"format={resource_format!r}, "
        f"content={resource_content!r}, "
        f"uri={resource_uri!r}"
    )

    is_dicom = any(
        str(value).upper() == "DICOM"
        for value in (
            resource_label,
            resource_format,
            resource_content,
        )
        if value is not None
    )

    if is_dicom:
        dicom_resource = resource_obj
        dicom_resource_key = resource_key
        break

if dicom_resource is None:
    raise RuntimeError(
        "No DICOM resource could be identified from the resource metadata. "
        f"Available resource keys: {list(scan.resources.keys())}"
    )

print("\nSelected DICOM resource")
print("Key:", dicom_resource_key)
print("Label:", getattr(dicom_resource, "label", None))
print("Format:", getattr(dicom_resource, "format", None))
print("Content:", getattr(dicom_resource, "content", None))
print("URI:", getattr(dicom_resource, "uri", None))

# %% [markdown]
# ## Locate downloaded DICOM files
#
# The resource may be downloaded as:
#
# - individual files in a directory;
# - a nested directory tree;
# - a ZIP archive.
#
# This helper searches all three cases.
#

# %%
from pathlib import Path
import zipfile

download_root = Path(download_root)
download_root.mkdir(parents=True, exist_ok=True)

print("Downloading resource to:", download_root)

try:
    download_result = dicom_resource.download_dir(
        str(download_root)
    )
    print("download_dir() returned:", download_result)
except Exception as exc:
    print("download_dir() failed:", exc)
    download_result = None

print("\nContents after download:")
downloaded_files = [
    path
    for path in download_root.rglob("*")
    if path.is_file()
]

for path in downloaded_files[:20]:
    print("-", path)

print("Total downloaded files:", len(downloaded_files))

# %%
from pathlib import Path

dicom_dir = Path(download_result)

print("DICOM directory:", dicom_dir)
print("Exists:", dicom_dir.exists())
print("Is directory:", dicom_dir.is_dir())

# %%
dicom_paths = sorted(dicom_dir.glob("*.dcm"))

print("DICOM files found:", len(dicom_paths))

for path in dicom_paths[:10]:
    print("-", path)

if not dicom_paths:
    raise RuntimeError(f"No DICOM files found in {dicom_dir}")

# %%
import pydicom

first_header = pydicom.dcmread(
    dicom_paths[0],
    stop_before_pixels=True,
)

print(first_header)

# %%
fields = [
    "SeriesDescription",
    "ProtocolName",
    "Modality",
    "Manufacturer",
    "ManufacturersModelName",
    "MagneticFieldStrength",
    "RepetitionTime",
    "EchoTime",
    "InversionTime",
    "FlipAngle",
    "EchoTrainLength",
    "PixelBandwidth",
    "SliceThickness",
    "SpacingBetweenSlices",
    "PixelSpacing",
    "Rows",
    "Columns",
    "ImageType",
]

for field in fields:
    print(f"{field}: {getattr(first_header, field, 'NA')!r}")

# %% [markdown]
# ## Read all headers

# %%
headers = []

for path in dicom_paths:
    try:
        header = pydicom.dcmread(
            path,
            stop_before_pixels=True,
        )
        headers.append((path, header))
    except Exception as exc:
        print(f"Could not read {path.name}: {exc}")

print("Readable DICOM files:", len(headers))

# %% [markdown]
# ## Check whether values vary across the series

# %%
from collections import Counter


def normalise_value(value):
    if value is None:
        return "NA"

    if isinstance(value, str):
        return value

    try:
        return tuple(str(item) for item in value)
    except TypeError:
        return str(value)


fields_to_check = [
    "SeriesDescription",
    "ProtocolName",
    "RepetitionTime",
    "EchoTime",
    "InversionTime",
    "FlipAngle",
    "SliceThickness",
    "PixelSpacing",
    "Rows",
    "Columns",
    "ImageType",
]

for field in fields_to_check:
    counts = Counter(
        normalise_value(getattr(header, field, "NA"))
        for _, header in headers
    )

    print(f"\n{field}:")
    for value, count in counts.items():
        print(f"  {value!r}: {count}")

# %% [markdown]
# ## Check for enhanced

# %%
print(
    "Shared Functional Groups:",
    (0x5200, 0x9229) in first_header,
)

print(
    "Per-frame Functional Groups:",
    (0x5200, 0x9230) in first_header,
)

# %% [markdown]
# ## Inspect private Siemens tags

# %%
private_elements = [
    element
    for element in first_header.iterall()
    if element.tag.is_private
]

print("Private tags found:", len(private_elements))

for element in private_elements[:50]:
    value_text = repr(element.value)

    if len(value_text) > 120:
        value_text = value_text[:117] + "..."

    print(
        f"{element.tag} | "
        f"{element.name} | "
        f"VR={element.VR} | "
        f"{value_text}"
    )

# %% [markdown]
# ## Build a quick metadata table

# %%
import pandas as pd

rows = []

for path, header in headers:
    rows.append(
        {
            "file": path.name,
            "InstanceNumber": getattr(
                header,
                "InstanceNumber",
                "NA",
            ),
            "SeriesDescription": getattr(
                header,
                "SeriesDescription",
                "NA",
            ),
            "ProtocolName": getattr(
                header,
                "ProtocolName",
                "NA",
            ),
            "TR": getattr(
                header,
                "RepetitionTime",
                "NA",
            ),
            "TE": getattr(
                header,
                "EchoTime",
                "NA",
            ),
            "TI": getattr(
                header,
                "InversionTime",
                "NA",
            ),
            "FlipAngle": getattr(
                header,
                "FlipAngle",
                "NA",
            ),
            "Rows": getattr(
                header,
                "Rows",
                "NA",
            ),
            "Columns": getattr(
                header,
                "Columns",
                "NA",
            ),
        }
    )

metadata_df = pd.DataFrame(rows)
metadata_df.head()

# %% [markdown]
# ## Sort numerically by instance number
#
# Your filenames sort lexically, so ```100.dcm``` appears before ```11.dcm```. For DICOM analysis, sort by ```InstanceNumber``` instead:

# %%
headers_sorted = sorted(
    headers,
    key=lambda item: int(
        getattr(item[1], "InstanceNumber", 0)
    ),
)

for path, header in headers_sorted[:10]:
    print(
        path.name,
        getattr(header, "InstanceNumber", "NA"),
    )

# %%
# The key correction for the notebook is:

dicom_dir = Path(download_result)
dicom_paths = sorted(dicom_dir.glob("*.dcm"))

# rather than searching only the original download_root.

# %%

# %%
'''
Should be markdown, not working
## Read one DICOM header without pixel data

For metadata extraction, use `stop_before_pixels=True`. This avoids loading large pixel arrays and is normally much faster.

`force=True` can help with non-standard files, but it should be used cautiously because it can also interpret non-DICOM files as DICOM-like datasets.
'''

# %%
'''
def read_dicom_header(path: Path) -> Dataset | None:
    try:
        return pydicom.dcmread(
            path,
            stop_before_pixels=True,
            force=False,
        )
    except InvalidDicomError:
        try:
            return pydicom.dcmread(
                path,
                stop_before_pixels=True,
                force=True,
            )
        except Exception as exc:
            print(f"Could not read {path}: {exc}")
            return None
    except Exception as exc:
        print(f"Could not read {path}: {exc}")
        return None


first_header = read_dicom_header(dicom_paths[0])

if first_header is None:
    raise RuntimeError("The first candidate file could not be read as DICOM.")

print(first_header)
'''

# %% [markdown]
# ## Inspect common DICOM attributes safely
#
# DICOM keywords can be accessed as attributes, but not every dataset contains every field. `getattr(dataset, keyword, default)` is therefore preferable to direct attribute access during exploration.
#

# %%
common_dicom_keywords = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SOPInstanceUID",
    "Modality",
    "Manufacturer",
    "ManufacturersModelName",
    "StationName",
    "SeriesNumber",
    "SeriesDescription",
    "ProtocolName",
    "ScanningSequence",
    "SequenceVariant",
    "MRAcquisitionType",
    "MagneticFieldStrength",
    "RepetitionTime",
    "EchoTime",
    "InversionTime",
    "FlipAngle",
    "EchoTrainLength",
    "PixelBandwidth",
    "SliceThickness",
    "SpacingBetweenSlices",
    "PixelSpacing",
    "Rows",
    "Columns",
    "NumberOfFrames",
    "NumberOfTemporalPositions",
    "ImageType",
]

for keyword in common_dicom_keywords:
    print(f"{keyword}: {getattr(first_header, keyword, 'NA')!r}")


# %% [markdown]
# ## Access tags by numeric DICOM tag
#
# Numeric tags are useful when:
#
# - no keyword is defined;
# - a private tag is being inspected;
# - exact tag handling is required.
#
# For example, `(0008,103E)` is Series Description.
#

# %%
series_description_tag = (0x0008, 0x103E)

if series_description_tag in first_header:
    element = first_header[series_description_tag]
    print("Element:", element)
    print("VR:", element.VR)
    print("Value:", element.value)
else:
    print("Series Description tag is not present.")


# %% [markdown]
# ## Safe helper for reading tags
#
# The helper below supports either a DICOM keyword or numeric tag and returns a fallback when the element is absent.
#

# %%
def get_dicom_value(
    dataset: Dataset,
    key,
    default="NA",
):
    try:
        if isinstance(key, str):
            return getattr(dataset, key, default)

        if key in dataset:
            return dataset[key].value

        return default
    except Exception:
        return default


print("SeriesDescription:", get_dicom_value(first_header, "SeriesDescription"))
print("ProtocolName:", get_dicom_value(first_header, (0x0018, 0x1030)))


# %% [markdown]
# ## Inspect all top-level DICOM elements
#
# This displays each element's tag, keyword, VR, and a shortened representation of its value.
#

# %%
for element in first_header:
    value_text = repr(element.value)

    if len(value_text) > 120:
        value_text = value_text[:117] + "..."

    print(
        f"{element.tag} | "
        f"{element.keyword or '<no keyword>'} | "
        f"VR={element.VR} | "
        f"{value_text}"
    )


# %% [markdown]
# ## Identify private tags
#
# Private tags have an odd group number. Siemens-specific ProtocolQC extraction relies on several private tags, so this is a useful discovery step.
#

# %%
private_elements = [
    element
    for element in first_header.iterall()
    if element.tag.is_private
]

print("Private elements:", len(private_elements))

for element in private_elements[:100]:
    value_text = repr(element.value)

    if len(value_text) > 120:
        value_text = value_text[:117] + "..."

    print(
        f"{element.tag} | "
        f"{element.name} | "
        f"VR={element.VR} | "
        f"{value_text}"
    )


# %% [markdown]
# ## Inspect specific Siemens private tags
#
# The previous Flywheel ProtocolQC implementation used private Siemens content including tags in group `0x0021`.
#
# These tags may not exist in every dataset and may differ between classic and enhanced MR objects.
#

# %%
siemens_private_tags = {
    "Siemens header container": (0x0021, 0x10FE),
    "Phoenix protocol": (0x0021, 0x1019),
    "Sequence": (0x0021, 0x105A),
    "Sequence options": (0x0021, 0x105B),
}

for label, tag in siemens_private_tags.items():
    value = get_dicom_value(first_header, tag)
    print(f"{label} {tag}: {value!r}")


# %% [markdown]
# ## Check SOP Class UID
#
# ProtocolQC needs to distinguish standard MR images, enhanced MR images, MR spectroscopy, and other object types.
#

# %%
sop_class_uid = None

if hasattr(first_header, "file_meta"):
    sop_class_uid = getattr(first_header.file_meta, "MediaStorageSOPClassUID", None)

print("Media Storage SOP Class UID:", sop_class_uid)
print("Dataset SOP Class UID:", getattr(first_header, "SOPClassUID", None))

known_sop_classes = {
    "1.2.840.10008.5.1.4.1.1.4": "MR Image Storage",
    "1.2.840.10008.5.1.4.1.1.4.1": "Enhanced MR Image Storage",
    "1.2.840.10008.5.1.4.1.1.4.2": "MR Spectroscopy Storage",
    "1.2.840.10008.5.1.4.1.1.88.22": "Enhanced SR Storage",
}

print("Recognised SOP class:", known_sop_classes.get(str(sop_class_uid), "Other/unknown"))


# %% [markdown]
# ## Detect derived images
#
# Derived images should generally not be used as authoritative ProtocolQC inputs.
#
# `ImageType` may be a multi-value DICOM object or a string, so convert it into a list of strings before checking.
#

# %%
def image_type_values(dataset: Dataset) -> list[str]:
    value = getattr(dataset, "ImageType", [])

    if isinstance(value, str):
        return [part.strip() for part in value.split("\\")]

    try:
        return [str(part) for part in value]
    except TypeError:
        return [str(value)]


image_types = image_type_values(first_header)
is_derived = any(value.upper() == "DERIVED" for value in image_types)

print("ImageType values:", image_types)
print("Derived image:", is_derived)


# %% [markdown]
# ## Inspect enhanced-MR functional groups
#
# Enhanced MR stores many acquisition parameters inside:
#
# - Shared Functional Groups Sequence `(5200,9229)`;
# - Per-frame Functional Groups Sequence `(5200,9230)`.
#
# The following example safely explores the shared functional groups.
#

# %%
shared_fg_tag = (0x5200, 0x9229)
per_frame_fg_tag = (0x5200, 0x9230)

if shared_fg_tag in first_header:
    shared_groups = first_header[shared_fg_tag].value
    print("Shared functional group items:", len(shared_groups))

    shared_item = shared_groups[0]
    print("Shared functional group top-level elements:")

    for element in shared_item:
        print(
            f"{element.tag} | "
            f"{element.keyword or element.name} | "
            f"VR={element.VR}"
        )
else:
    print("No Shared Functional Groups Sequence found.")

if per_frame_fg_tag in first_header:
    per_frame_groups = first_header[per_frame_fg_tag].value
    print("Per-frame functional group items:", len(per_frame_groups))
else:
    print("No Per-frame Functional Groups Sequence found.")


# %% [markdown]
# ## Extract selected enhanced-MR values
#
# This example accesses the same kinds of nested sequences used by the earlier Flywheel ProtocolQC extractor.
#
# It deliberately uses safe helper functions because not all MR objects contain every nested sequence.
#

# %%
def first_sequence_item(dataset: Dataset, tag):
    try:
        if tag not in dataset:
            return None

        sequence = dataset[tag].value

        if not sequence:
            return None

        return sequence[0]
    except Exception:
        return None


def nested_value(dataset: Dataset | None, keyword: str, default="NA"):
    if dataset is None:
        return default

    try:
        return getattr(dataset, keyword, default)
    except Exception:
        return default


enhanced_values = {}

if shared_fg_tag in first_header:
    shared_item = first_header[shared_fg_tag].value[0]

    mr_timing = first_sequence_item(shared_item, (0x0018, 0x9112))
    mr_modifier = first_sequence_item(shared_item, (0x0018, 0x9115))
    mr_receive_coil = first_sequence_item(shared_item, (0x0018, 0x9042))
    mr_geometry = first_sequence_item(shared_item, (0x0018, 0x9125))
    mr_image_modifier = first_sequence_item(shared_item, (0x0018, 0x9006))

    enhanced_values.update(
        {
            "RepetitionTime": nested_value(mr_timing, "RepetitionTime"),
            "FlipAngle": nested_value(mr_timing, "FlipAngle"),
            "EchoTrainLength": nested_value(mr_timing, "EchoTrainLength"),
            "InversionTimes": nested_value(mr_modifier, "InversionTimes"),
            "ReceiveCoilName": nested_value(mr_receive_coil, "ReceiveCoilName"),
            "PercentPhaseFieldOfView": nested_value(
                mr_geometry,
                "PercentPhaseFieldOfView",
            ),
            "InPlanePhaseEncodingDirection": nested_value(
                mr_geometry,
                "InPlanePhaseEncodingDirection",
            ),
            "FrequencyEncodingSteps": nested_value(
                mr_geometry,
                "MRAcquisitionFrequencyEncodingSteps",
            ),
            "PhaseEncodingSteps": nested_value(
                mr_geometry,
                "MRAcquisitionPhaseEncodingStepsInPlane",
            ),
            "PixelBandwidth": nested_value(
                mr_image_modifier,
                "PixelBandwidth",
            ),
        }
    )

pprint(enhanced_values)


# %% [markdown]
# ## Inspect per-frame echo time and pixel measures
#
# For enhanced MR, effective echo time and pixel measures can reside in per-frame functional group items.
#

# %%
per_frame_values = {}

if per_frame_fg_tag in first_header:
    first_frame = first_header[per_frame_fg_tag].value[0]

    mr_echo = first_sequence_item(first_frame, (0x0018, 0x9114))
    pixel_measures = first_sequence_item(first_frame, (0x0028, 0x9110))

    per_frame_values = {
        "EffectiveEchoTime": nested_value(
            mr_echo,
            "EffectiveEchoTime",
        ),
        "SliceThickness": nested_value(
            pixel_measures,
            "SliceThickness",
        ),
        "PixelSpacing": nested_value(
            pixel_measures,
            "PixelSpacing",
        ),
    }

pprint(per_frame_values)


# %% [markdown]
# ## Read all headers in the series
#
# The following cell reads every candidate DICOM file without pixel data and skips unreadable files.
#

# %%
headers: list[tuple[Path, Dataset]] = []

for path in dicom_paths:
    header = read_dicom_header(path)

    if header is not None:
        headers.append((path, header))

print("Readable DICOM headers:", len(headers))


# %% [markdown]
# ## Summarise values across the series
#
# A ProtocolQC extractor must determine whether values are constant or vary across files.
#
# This example counts unique values for selected fields.
#

# %%
def normalise_for_counting(value):
    if value is None:
        return "NA"

    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)

    try:
        return tuple(str(item) for item in value)
    except TypeError:
        return str(value)


series_fields = [
    "SeriesDescription",
    "ProtocolName",
    "RepetitionTime",
    "EchoTime",
    "FlipAngle",
    "SliceThickness",
    "PixelSpacing",
    "Rows",
    "Columns",
    "ImageType",
]

series_value_counts = {}

for keyword in series_fields:
    counter = Counter()

    for _, header in headers:
        value = getattr(header, keyword, "NA")
        counter[normalise_for_counting(value)] += 1

    series_value_counts[keyword] = counter

for keyword, counter in series_value_counts.items():
    print(f"\n{keyword}:")
    for value, count in counter.items():
        print(f"  {value!r}: {count}")


# %% [markdown]
# ## Find varying fields across the series
#
# This is a simplified discovery tool for multi-echo or multi-condition series.
#
# It should not replace the production `combined_dicom_dicts()` logic, but it helps identify fields that vary.
#

# %%
candidate_keywords = [
    "EchoTime",
    "EffectiveEchoTime",
    "InversionTime",
    "FlipAngle",
    "TemporalPositionIdentifier",
    "EchoNumbers",
    "AcquisitionNumber",
    "InstanceNumber",
]

varying_fields = {}

for keyword in candidate_keywords:
    values = []

    for _, header in headers:
        value = getattr(header, keyword, None)

        if value is not None:
            values.append(normalise_for_counting(value))

    unique_values = sorted(set(values), key=str)

    if len(unique_values) > 1:
        varying_fields[keyword] = unique_values

pprint(varying_fields)


# %% [markdown]
# ## Build a metadata table
#
# This creates a compact table containing one row per DICOM file.
#
# For large resources, consider limiting the number of rows during exploration.
#

# %%
rows = []

for path, header in headers:
    rows.append(
        {
            "file": str(path),
            "SOPInstanceUID": getattr(header, "SOPInstanceUID", "NA"),
            "SeriesInstanceUID": getattr(header, "SeriesInstanceUID", "NA"),
            "InstanceNumber": getattr(header, "InstanceNumber", "NA"),
            "SeriesDescription": getattr(header, "SeriesDescription", "NA"),
            "ProtocolName": getattr(header, "ProtocolName", "NA"),
            "TR": getattr(header, "RepetitionTime", "NA"),
            "TE": getattr(header, "EchoTime", "NA"),
            "TI": getattr(header, "InversionTime", "NA"),
            "FlipAngle": getattr(header, "FlipAngle", "NA"),
            "Rows": getattr(header, "Rows", "NA"),
            "Columns": getattr(header, "Columns", "NA"),
            "ImageType": "\\".join(image_type_values(header)),
        }
    )

metadata_df = pd.DataFrame(rows)
metadata_df.head()


# %% [markdown]
# ## Export selected metadata to CSV
#

# %%
csv_path = download_root / "dicom_metadata_summary.csv"
metadata_df.to_csv(csv_path, index=False)

print("Saved:", csv_path)


# %% [markdown]
# ## Export one DICOM dataset to JSON-compatible data
#
# `Dataset.to_json_dict()` produces a DICOM-tag-oriented JSON representation.
#
# This differs from the ProtocolQC template structure, but is useful for diagnostics and archival inspection.
#

# %%
dicom_json_path = download_root / "first_dicom_header.json"

with dicom_json_path.open("w", encoding="utf-8") as stream:
    json.dump(
        first_header.to_json_dict(),
        stream,
        indent=2,
        default=str,
    )

print("Saved:", dicom_json_path)


# %% [markdown]
# ## Create a compact ProtocolQC-style acquisition dictionary
#
# This example demonstrates the expected shape only. It is intentionally incomplete and should not replace the full shared extractor.
#
# The production implementation should port the complete enhanced-MR and Siemens-specific logic from the earlier Flywheel `run.py`.
#

# %%
compact_protocol_qc_dict = {
    "Sequence_Attributes": {
        "Multi-Echo": False,
        "Echo_lines_multiplier": False,
        "Temporal_positions_multiplier": False,
        "Check_DICOM_File_Number": True,
        "Comment": (
            "Exploratory dictionary generated from the pydicom examples. "
            "Not approved for production QC."
        ),
    },
    "Acquisition_Parameters": {
        "series_description": getattr(
            first_header,
            "SeriesDescription",
            "NA",
        ),
        "Protocol": getattr(
            first_header,
            "ProtocolName",
            "NA",
        ),
        "Field_strength": getattr(
            first_header,
            "MagneticFieldStrength",
            "NA",
        ),
        "TR": enhanced_values.get(
            "RepetitionTime",
            getattr(first_header, "RepetitionTime", "NA"),
        ),
        "TE": per_frame_values.get(
            "EffectiveEchoTime",
            getattr(first_header, "EchoTime", "NA"),
        ),
        "TI": enhanced_values.get(
            "InversionTimes",
            getattr(first_header, "InversionTime", "NA"),
        ),
        "Flip_angle": enhanced_values.get(
            "FlipAngle",
            getattr(first_header, "FlipAngle", "NA"),
        ),
        "Bandwidth": enhanced_values.get(
            "PixelBandwidth",
            getattr(first_header, "PixelBandwidth", "NA"),
        ),
        "Slice_thickness": per_frame_values.get(
            "SliceThickness",
            getattr(first_header, "SliceThickness", "NA"),
        ),
        "Pix_spacing_row": (
            per_frame_values.get("PixelSpacing", ["NA", "NA"])[0]
            if isinstance(
                per_frame_values.get("PixelSpacing"),
                (list, tuple),
            )
            else "NA"
        ),
        "Pix_spacing_col": (
            per_frame_values.get("PixelSpacing", ["NA", "NA"])[1]
            if isinstance(
                per_frame_values.get("PixelSpacing"),
                (list, tuple),
            )
            and len(per_frame_values.get("PixelSpacing", [])) > 1
            else "NA"
        ),
        "Rows": getattr(first_header, "Rows", "NA"),
        "Columns": getattr(first_header, "Columns", "NA"),
        "Number_slices": getattr(first_header, "NumberOfFrames", "NA"),
    },
}

pprint(compact_protocol_qc_dict)


# %% [markdown]
# ## Recommended next implementation step
#
# The notebook now provides useful `pydicom` exploration examples, but ProtocolQC should not duplicate extraction logic across notebooks.
#
# The recommended design remains:
#
# 1. port the full Flywheel `return_dicom_dict()` and `combined_dicom_dicts()` behaviour into a platform-independent module;
# 2. remove Flywheel tags, messaging, and API side effects;
# 3. use that shared module from both the XNAT template-generation notebook and the runtime QC pipeline;
# 4. regression-test the XNAT output against JSON generated by the original Flywheel implementation.
#
