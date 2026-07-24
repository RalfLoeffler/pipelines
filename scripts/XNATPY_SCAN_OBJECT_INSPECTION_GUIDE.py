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
#
# ```powershell
# mamba activate ais-pipelines
# python -m pip install xnat jupyterlab
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

for project_id, project_obj in xnat_connection.projects.items():
    print(
        f"ID={project_id!r}, "
        f"name={getattr(project_obj, 'name', None)!r}, "
        f"secondary_id={getattr(project_obj, 'secondary_id', None)!r}"
    )


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
