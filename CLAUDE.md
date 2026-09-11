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

- **`JamfUploaderProcessors/JamfFooUploader.py`** — thin wrapper that defines AutoPkg `input_variables` / `output_variables` and extends the base class. Contains no logic. This is the "trusted" file that AutoPkg users verify; logic changes here require users to re-verify trust.
- **`JamfUploaderProcessors/JamfUploaderLib/JamfFooUploaderBase.py`** — all implementation logic. Changes here do not require re-verification.

The base classes all extend `JamfUploaderBase` (`JamfUploaderLib/JamfUploaderBase.py`), which provides:

- Authentication: basic auth, OAuth bearer tokens, API client credentials, jamf-cli profile tokens
- HTTP communication via `curl` subprocess calls (not the `requests` library — it is not bundled in AutoPkg's Python)
- XML/JSON template substitution
- Jamf Pro version detection
- Schema registry integration

### Schema registry (`JamfSchemaRegistry.py`)

`JamfSchemaRegistry` dynamically discovers API endpoints by downloading and caching the Jamf Pro OpenAPI (JPAPI) and Classic API Swagger schemas at runtime. It maps `object_type` strings to endpoint metadata. `CLASSIC_ALIAS_TABLE` and `JPAPI_ALIAS_TABLE` map JamfUploader internal names to schema resource names when simple normalisation isn't sufficient.

### Two API families

- **Classic API** — XML-based, older endpoints (most object types). URLs like `/JSSResource/policies`.
- **Jamf Pro API (JPAPI)** — JSON-based, newer endpoints (packages v1/v3, prestages, etc.). URLs like `/api/v1/packages`. Prefer this when available; check `jamf_version` before using version-specific endpoints.

Many processors support both; version detection in `JamfUploaderBase` determines which to use.

### Package upload modes

`JamfPackageUploader` supports multiple distribution point backends:

- **JCDS2** — Jamf Cloud Distribution Service (AWS S3 multipart)
- **AWS CDP** — Customer-owned S3 bucket
- **SMB** — SMB/CIFS share
- **dbfileupload** — Legacy Classic API upload (deprecated)
- **v1/v3 packages API** — Newer REST endpoints (default on Jamf Pro 11.5+)

### Authentication flow

`JamfUploaderBase.auth()` resolves credentials in this priority order:

1. `BEARER_TOKEN` — pre-existing bearer token (validated before use)
2. `jamf_credentials_manager` — JamfCredentialsManager library
3. `CLIENT_ID` / `CLIENT_SECRET` — OAuth 2.0 API client credentials (preferred)
4. `API_USERNAME` / `API_PASSWORD` — legacy basic auth
5. `jamf_cli_profile` — reads config and obtains a token via `jamf-cli platform/pro auth token --profile <name>`

When `jamf_cli_profile` is set, the URL, region, and tenant ID are auto-detected from the profile config so they do not need to be supplied separately. Bearer tokens are cached in `/tmp/jamf_upload/` and validated before reuse.

### Template substitution

Templates use `%VARIABLE_NAME%` placeholders (uppercase, percent-delimited). The `substitute_assignable_keys()` method in `JamfUploaderBase` handles replacements. Some keys are intentionally skipped for user-editable content (e.g., script contents in Extension Attributes) — see `skip_script_key_substitution`. Most processors support both `replace` (overwrite) and `update` (merge/patch) modes.

## Tests

Test scripts and recipes live in `_tests/`. These are shell scripts that exercise the API against a real Jamf Pro server — there is no mock-based unit test suite. Key test scripts:

```sh
_tests/api_test_pkg.sh          # Test package upload (default mode)
_tests/api_test_pkg_jcds2.sh    # Test JCDS2 mode
_tests/api_test_pkg_aws_cdp.sh  # Test AWS CDP mode
_tests/test.sh -t <name>        # Run a named test scenario against a live server
```

Schema registry unit tests (no server required):

```sh
/usr/local/autopkg/python _tests/test_schema_registry.py
```

When modifying authentication or template code, test with both `jamf-upload.sh` (standalone) and an AutoPkg recipe, and exercise multiple auth methods.

## Adding a new processor

1. Create `JamfUploaderProcessors/JamfFooUploader.py` — thin wrapper only, with `input_variables`, `output_variables`, and a `main()` that calls the base class.
2. Create `JamfUploaderProcessors/JamfUploaderLib/JamfFooUploaderBase.py` — all logic here, extending `JamfUploaderBase`.
3. Add documentation as a new page in the [wiki](https://github.com/grahampugh/jamf-upload/wiki).
4. Add a case to `jamf-upload.sh` for standalone usage.
5. If the new object type needs schema resolution, add an entry to `CLASSIC_ALIAS_TABLE` or `JPAPI_ALIAS_TABLE` in `JamfSchemaRegistry.py`.
6. Update `CHANGELOG.md`.

Logic changes always go in `JamfUploaderLib/*Base.py`. Update `input_variables` in the processor file only when adding new parameters; check whether `jamf-upload.sh` argument parsing also needs updating.

## Key references

- Wiki: <https://github.com/grahampugh/jamf-upload/wiki>
- Processor input/output docs: [wiki](https://github.com/grahampugh/jamf-upload/wiki)
- Changelog: `JamfUploaderProcessors/CHANGELOG.md`
