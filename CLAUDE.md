# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**jamf-upload** is a toolkit for interacting with the Jamf Pro API (macOS/iOS device management). It has two main components:

1. **AutoPkg Processors** (`JamfUploaderProcessors/`) — 43+ Python processors extending AutoPkg
2. **Standalone shell script** (`jamf-upload.sh`) — direct API interaction without AutoPkg

Identical copies of the processors are hosted in `autopkg/grahampugh-recipes`. PRs should only be made to this repo (`grahampugh/jamf-upload`).

## Python Environment

All processor files use AutoPkg's Python distribution with shebang `#!/usr/local/autopkg/python`. Do not use the system Python or a venv for running processors — they depend on `autopkglib` which lives in AutoPkg's distribution.

For linting/development tools, a `.venv` is available:

```sh
source .venv/bin/activate
flake8 JamfUploaderProcessors/          # max line length: 100 (configured in setup.cfg)
pylint JamfUploaderProcessors/          # config in .pylintrc
```

## Architecture

### Processor pattern (thin wrapper + base class)

Every processor follows this split:

- **`JamfUploaderProcessors/JamfFooUploader.py`** — thin wrapper that defines AutoPkg `input_variables` / `output_variables` and extends the base class. Contains no logic.
- **`JamfUploaderProcessors/JamfUploaderLib/JamfFooUploaderBase.py`** — contains all implementation logic.

The base classes all extend `JamfUploaderBase` (`JamfUploaderLib/JamfUploaderBase.py`), which provides:

- Authentication: basic auth, OAuth bearer tokens, API client credentials
- HTTP communication via `curl` subprocess calls (not the `requests` library directly, because this is not included in the autopkg python distribution)
- XML/JSON template substitution
- Jamf Pro version detection
- Schema registry integration

### Schema registry (`JamfSchemaRegistry.py`)

`JamfSchemaRegistry` dynamically discovers API endpoints by downloading and caching the Jamf Pro OpenAPI (JPAPI) and Classic API Swagger schemas at runtime. It maps `object_type` strings to endpoint metadata. `CLASSIC_ALIAS_TABLE` and `JPAPI_ALIAS_TABLE` map JamfUploader internal names to schema resource names when simple normalisation isn't sufficient.

### Two API families

- **Classic API** — XML-based, older endpoints (most object types)
- **Jamf Pro API (JPAPI)** — JSON-based, newer endpoints (packages v1/v3, prestages, etc.)

Many processors support both; version detection in `JamfUploaderBase` determines which to use.

### Package upload modes

`JamfPackageUploader` supports multiple distribution point backends:

- **JCDS2** — Jamf Cloud Distribution Service (AWS S3 multipart)
- **AWS CDP** — Customer-owned S3 bucket
- **SMB** — SMB/CIFS share
- **dbfileupload** — Legacy Classic API upload
- **v1/v3 packages API** — Newer REST endpoints

## Tests

Test scripts and recipes live in `_tests/`. These are mostly shell scripts that exercise the API against a real Jamf Pro server — there is no mock-based unit test suite. Key test scripts:

```sh
_tests/api_test_pkg.sh          # Test package upload (default mode)
_tests/api_test_pkg_jcds2.sh    # Test JCDS2 mode
_tests/api_test_pkg_aws_cdp.sh  # Test AWS CDP mode
_tests/test_schema_registry.py  # Schema registry unit tests (runnable with autopkg python)
```

To run the schema registry tests:

```sh
/usr/local/autopkg/python _tests/test_schema_registry.py
```

The file `_tests/test.py` contains many preset tests that can be run by selecting a test with the `-t` parameter.

## Adding a new processor

1. Create `JamfUploaderProcessors/JamfFooUploader.py` — thin wrapper only, with `input_variables`, `output_variables`, and a `main()` that calls the base class.
2. Create `JamfUploaderProcessors/JamfUploaderLib/JamfFooUploaderBase.py` — all logic here, extending `JamfUploaderBase`.
3. Add documentation in `JamfUploaderProcessors/READMEs/`.
4. If the new object type needs schema resolution, add an entry to `CLASSIC_ALIAS_TABLE` or `JPAPI_ALIAS_TABLE` in `JamfSchemaRegistry.py`.

## Key references

- Wiki: <https://github.com/grahampugh/jamf-upload/wiki>
- Processor input/output docs: `JamfUploaderProcessors/READMEs/`
- Changelog: `JamfUploaderProcessors/CHANGELOG.md`
