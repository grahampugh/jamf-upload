# JamfUploader Development Guide

## Project Overview

JamfUploader is a collection of AutoPkg processors for uploading and managing objects in Jamf Pro. The processors can be used in AutoPkg recipes or standalone via the `jamf-upload.sh` wrapper script.

**Key capabilities:**

- Upload packages to JCDS, AWS CDP, or SMB file shares
- Manage categories, groups, profiles, scripts, policies, extension attributes, and more
- Support for both Classic API and modern Jamf Pro API
- OAuth 2.0 authentication (API Client credentials) and legacy username/password auth

## Architecture

### Processor Structure

All processors follow a two-file architecture pattern:

1. **Processor file** (`JamfUploaderProcessors/Jamf*Uploader.py`):
   - Thin wrapper that imports from the Base class
   - Defines `input_variables` and `output_variables` for AutoPkg
   - Minimal logic - delegates all work to the Base class

2. **Base class** (`JamfUploaderProcessors/JamfUploaderLib/Jamf*UploaderBase.py`):
   - Contains all the actual implementation logic
   - Inherits from `JamfUploaderBase` (the shared parent class)
   - Handles API interactions, XML/JSON templating, and business logic

**Why this split?** Separating off the base classes allows technical changes to be made without users having to reverify trust for the processor files in AutoPkg. The processor files are essentially "trusted" wrappers around the logic in the base classes.

### Inheritance Hierarchy

```
JamfUploaderBase (JamfUploaderLib/JamfUploaderBase.py)
├── Common methods for all processors (~60 methods, 2580 lines)
├── Authentication (bearer tokens, API clients, credentials)
├── HTTP operations (GET, POST, PUT, DELETE, file uploads)
├── XML/JSON template handling
└── Token management and validation

↓ inherits

Specific*UploaderBase (JamfUploaderLib/Jamf*UploaderBase.py)
└── Object-specific logic for packages, policies, scripts, etc.

↓ imported by

Specific*Uploader (JamfUploaderProcessors/Jamf*.py)
└── AutoPkg Processor wrapper with input/output variable definitions
```

### File Organization

- `JamfUploaderProcessors/` - AutoPkg processor files (thin wrappers)
- `JamfUploaderProcessors/JamfUploaderLib/` - Base classes with all logic
- `JamfUploaderProcessors/READMEs/` - Individual processor documentation
- `_Templates_Examples/` - XML/JSON templates for policies, profiles, groups
- `_tests/` - Test scripts and test recipes
- `Jamf_Helper_Recipes/` - Helper recipes for common operations

## Coding Conventions

### Authentication Flow

Processors support multiple authentication methods (in priority order):

1. `BEARER_TOKEN` - Pre-existing bearer token (validated before use)
2. `jamf_credentials_manager` - Uses JamfCredentialsManager library
3. `CLIENT_ID`/`CLIENT_SECRET` - OAuth 2.0 API client credentials (preferred)
4. `API_USERNAME`/`API_PASSWORD` - Legacy basic auth (deprecated on some endpoints)

Bearer tokens are cached in `/tmp/jamf_upload/` and validated before reuse.

### Template Substitution

Templates use `%VARIABLE_NAME%` placeholders for substitution:

- Policy templates use XML with keys like `%POLICY_NAME%`, `%CATEGORY%`, `%PKG_NAME%`
- Profile templates similarly use XML substitution
- The `substitute_assignable_keys()` method in `JamfUploaderBase` handles replacements

**Important:** Some keys are **not** substituted automatically if they represent user-editable content (e.g., script contents in Extension Attributes). Check `skip_script_key_substitution` usage.

### API Version Handling

The codebase uses both Classic API and Jamf Pro API (vX):

- **Classic API**: XML-based (e.g., `/JSSResource/policies`)
- **Jamf Pro API**: JSON-based, modern (e.g., `/api/v1/packages`)

Package upload specifically has multiple modes:

- `pkg_api_mode` - Uses v1 API (default on Jamf Pro 11.5+)
- `jcds2_mode` - JCDS2 upload with AWS S3
- `aws_cdp_mode` - AWS CDP (Cloud Distribution Point)
- Legacy `dbfileupload` and JCDS methods (deprecated)

When adding features, prefer the Pro API when available. Check `jamf_version` before using version-specific endpoints.

### Error Handling

- All API calls should check HTTP status codes
- Token expiry is handled with automatic refresh
- Upload failures retry with exponential backoff in some cases
- Use `self.output()` for AutoPkg-compatible logging

## Code Style

- **Line length:** 100 characters (enforced by flake8 and pylint)
- **Imports:** sys.path manipulation required for AutoPkg Base modules (ignore E402)
- **Shebang:** `#!/usr/local/autopkg/python` (AutoPkg's bundled Python)
- **License header:** Apache 2.0 on all Python files

## Testing

No formal unit tests exist yet.
Testing is done mainly using the script `_tests/test.sh`, which includes options to test many endpoints by calling `jamf-upload.sh`.

When making changes:

1. Add a test scenario to `_tests/test.sh` that exercises the new or modified functionality if necessary
1. Test with `jamf-upload.sh` script (standalone mode)
1. Test with AutoPkg recipe (processor mode)
1. Test multiple auth methods if touching authentication code

## Common Tasks

### Adding a New Processor

1. Create `JamfUploaderProcessors/Jamf[Object]Uploader.py` (thin wrapper)
2. Create `JamfUploaderProcessors/JamfUploaderLib/Jamf[Object]UploaderBase.py` (logic)
3. Add processor README in `JamfUploaderProcessors/READMEs/`
4. Add case to `jamf-upload.sh` for standalone usage
5. Update CHANGELOG.md

### Modifying Existing Processors

- Logic changes go in `JamfUploaderLib/*Base.py`, not the processor file
- Update input_variables in the processor file if adding new parameters
- Check if changes affect `jamf-upload.sh` argument parsing
- Update the processor's README if behavior changes

### Working with Templates

Templates live in `_Templates_Examples/`. To modify template handling:

- Check `prepare_*_template()` methods in the relevant Base class
- Understand which keys get substituted vs. preserved
- Test with both "replace" and "update" modes (most processors support both)
