# Proposal: Schema-Driven Endpoint Resolution for JamfUploader

## Problem Statement

JamfUploaderBase.py maintains six hand-written dictionaries totalling ~330 lines that map internal `object_type` strings to API details (API type, endpoint path, HTTP method, name/id keys, list keys). Every new Jamf Pro endpoint requires manual edits across multiple dicts. The generic processors (`JamfObjectReader`, `JamfObjectUploader`, `JamfObjectDeleter`) cannot handle an endpoint unless it has been explicitly added.

## Goal

Replace the manually maintained dictionaries with runtime lookups against the Jamf Pro API schemas, so that:

- New endpoints work automatically without code changes
- Existing `object_type` strings continue to work unchanged
- jamf-upload.sh continues to work and can be used to test previously unsupported endpoints
- No new dependencies or languages are introduced

## Available Schemas

| Schema | URL | Format | Spec Version | Covers |
|--------|-----|--------|-------------|--------|
| **JPAPI** (Jamf Pro API) | `{jamf_url}/api/schema` | JSON | OpenAPI 3.0.1 | All `api/v1–v4/` endpoints |
| **Classic API** | `{jamf_url}/classicapi/doc/swagger.yaml` | YAML | Swagger 2.0 | All `JSSResource/` endpoints |

**Not covered by any schema**: Platform API endpoints (`apigw.jamf.com` — baselines, benchmarks, blueprints, rules). These remain manually defined.

### What the schemas provide

| Feature | Classic (Swagger 2.0) | JPAPI (OpenAPI 3.0.1) |
|---------|----------------------|----------------------|
| Base path | `/JSSResource/` | `/api/` |
| Paths with HTTP methods | `/{resource}/id/{id}`, `/{resource}/name/{name}` | `/v1/{resource}/{id}` |
| Update method | Always PUT | PUT, PATCH, or POST depending on endpoint |
| Deprecation markers | `deprecated: true` + `x-deprecation-date` | `deprecated` flag |
| Pagination | None (full lists) | `page` / `page-size` query params |
| Object model definitions | `definitions` section | `components/schemas` section |
| Action endpoints | N/A | `x-action: true` flag |
| YAML parsing | Requires `yaml` module (verified available in AutoPkg Python) | N/A (JSON, stdlib only) |

### Key structural patterns

**Classic API** — every resource follows predictable URL patterns:

- List: `GET /{resource}`
- By ID: `GET/PUT/DELETE /{resource}/id/{id}`
- By name: `GET /{resource}/name/{name}`
- Create: `POST /{resource}/id/0`
- Subsets: `GET /{resource}/id/{id}/subset/{subset}`

**JPAPI** — more varied:

- List: `GET /v1/{resource}` (paginated)
- By ID: `GET/PUT/PATCH/DELETE /v1/{resource}/{id}`
- RSQL filtering: `?filter=name=="value"`
- Settings endpoints: `GET/PUT` with no `{id}` parameter
- Command endpoints: `POST` only, flagged with `x-action: true`

## Current Architecture (What Changes)

Six dictionaries in JamfUploaderBase.py:

| Method | Lines | Purpose | After Proposal |
|--------|-------|---------|---------------|
| `api_type()` (line 50) | ~100 entries | Maps `object_type` → `"classic"`, `"jpapi"`, or `"platform"` | **Auto**: which schema the path is found in; only ~7 Platform entries remain manual |
| `api_endpoints()` (line 151) | ~70 entries | Maps `object_type` → URL path | **Auto**: paths from both schemas; only Platform entries remain manual |
| `object_types()` (line 262) | ~15 entries | Maps `object_type` → Classic URL resource name | **Auto**: derived from Classic schema path prefixes |
| `object_list_types()` (line 283) | ~40 entries | Maps `object_type` → XML/JSON list key | **Mostly auto**: from Classic tags + JPAPI response schemas |
| `get_namekey()` (line 340) | ~13 entries | Maps `object_type` → name field | **Mostly auto**: Classic always `"name"`; JPAPI from schema |
| `get_idkey()` (line 363) | ~3 entries | Maps `object_type` → ID field | **Auto**: Classic always `"id"`; JPAPI from schema |

**Net reduction**: ~330 lines of manually maintained dicts → ~20–30 lines (Platform API overrides + a small alias table).

## Implementation Plan

### Phase 1: JamfSchemaRegistry

Create a new file `JamfUploaderProcessors/JamfUploaderLib/JamfSchemaRegistry.py` (~250–350 lines) using only stdlib + `yaml` (already bundled with AutoPkg Python).

**Responsibilities:**

1. Download and cache both schemas per Jamf Pro instance
2. Parse Classic Swagger 2.0 YAML and JPAPI OpenAPI 3.0.1 JSON
3. Provide a unified `resolve(object_type)` query method
4. Log deprecation warnings when a resolved endpoint is marked deprecated

**Caching strategy:**

- Schemas cached as files in the per-instance temp directory (already used by JamfUploaderBase for tokens)
- TTL of 24 hours — schema re-fetched only if cache file is older than 24h
- Cache keyed by Jamf Pro URL (one cache per server)
- Schema download uses the existing `curl()` method via a callback, avoiding any new HTTP dependencies

**YAML parsing:** `import yaml` — verified available in AutoPkg's Python at python3.

**Classic schema parsing sketch:**

```python
def _parse_classic_schema(self, schema):
    """Extract resource metadata from Swagger 2.0 Classic API schema."""
    resources = {}
    for path, methods in schema.get("paths", {}).items():
        parts = path.strip("/").split("/")
        resource_name = parts[0]
        if resource_name not in resources:
            resources[resource_name] = {
                "api_type": "classic",
                "paths": {},
                "deprecated": False,
                "methods": set(),
            }
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete"):
                resources[resource_name]["methods"].add(method)
                if details.get("deprecated"):
                    resources[resource_name]["deprecated"] = True
                    resources[resource_name]["deprecation_date"] = (
                        details.get("x-deprecation-date", "")
                    )
        # Classify path patterns for later use
        if "/id/{id}" in path and "/subset/" not in path:
            resources[resource_name]["paths"]["by_id"] = path
        elif "/name/{name}" in path:
            resources[resource_name]["paths"]["by_name"] = path
        elif path == f"/{resource_name}":
            resources[resource_name]["paths"]["list"] = path
    return resources
```

**JPAPI schema parsing sketch:**

```python
def _parse_jpapi_schema(self, schema):
    """Extract resource metadata from OpenAPI 3.0.1 JPAPI schema."""
    resources = {}
    for path, methods in schema.get("paths", {}).items():
        # Normalise: /v1/categories/{id} → resource key "categories"
        # Extract HTTP methods, pagination params, x-action flags
        # Map request body $ref → components/schemas → name/id field names
        ...
    return resources
```

**Unified resolution method:**

```python
def resolve(self, object_type):
    """Resolve an object_type to its full endpoint metadata.
    
    Resolution order:
    1. Manual overrides (Platform API — no schema available)
    2. Alias table (maps object_type names to schema resource names)
    3. Classic schema lookup
    4. JPAPI schema lookup
    5. Treat object_type as a literal path (e.g., "v1/departments")
    
    Returns: dict with api_type, endpoint, methods, name_key, id_key, 
             deprecated, list_key
    """
```

### Phase 2: Alias Table for Object Type Names

The registry needs to map JamfUploader's internal `object_type` strings (e.g., `"computer_group"`, `"os_x_configuration_profile"`) to schema resource names (e.g., `"computergroups"`, `"osxconfigurationprofiles"`). Three strategies, applied in order:

1. **Small alias table** (~20 entries) for names that can't be derived programmatically — kept as a dict in the registry, much smaller than the current 100+ entries
2. **Normalisation**: strip underscores, lowercase, try plural — `"computer_group"` → `"computergroups"`
3. **Direct resource name**: accept schema resource names directly as `object_type` values (e.g., `"computergroups"`, `"v1/categories"`)

### Phase 3: Integrate Registry into JamfUploaderBase

Modify the existing six methods in JamfUploaderBase.py to use the registry as a fallback:

```python
def api_type(self, object_type):
    # 1. Check manual Platform overrides (unchanged)
    if object_type in ("baseline", "benchmark", "blueprint", ...):
        return "platform"
    # 2. Ask the schema registry
    resolved = self._registry.resolve(object_type)
    if resolved:
        return resolved["api_type"]
    raise ProcessorError(f"ERROR: Unknown object type {object_type}")
```

The same pattern applies to `api_endpoints()`, `object_types()`, `object_list_types()`, `get_namekey()`, and `get_idkey()`. The existing hardcoded values remain as a first-check fast path for known types, with registry lookup as fallback for anything not explicitly listed.

**Registry initialisation**: lazily on first use, after `jamf_url` is known (during `execute()`). A single `_registry` instance is stored on the processor instance.

### Phase 4: Automatic HTTP Method Selection

Add a `determine_request_method()` helper to JamfUploaderBase.py, replacing the hardcoded if/elif chain in `JamfObjectUploaderBase.upload_object()`:

```python
def determine_request_method(self, object_type, object_id=None):
    resolved = self._registry.resolve(object_type)
    if not resolved:
        # Fallback to existing hardcoded logic
        return "PUT" if object_id else "POST"
    
    if resolved["api_type"] == "classic":
        return "PUT" if object_id else "POST"
    
    if resolved["api_type"] == "jpapi":
        methods = resolved["methods"]
        if object_id:
            return "PATCH" if "patch" in methods else "PUT"
        return "POST"
    
    # Platform: case-by-case (unchanged)
    ...
```

### Phase 5: New `JamfSchemaLister` Processor

Create a new lightweight processor `JamfSchemaLister` that queries the cached schemas and outputs a list of all discoverable endpoint types. This has two uses:

1. From jamf-upload.sh as `.jamf-upload.sh list-types --url ... --user ... --pass ...`
2. From AutoPkg recipes (unlikely but possible)

**Input variables:**

- `JSS_URL` (required)
- `API_USERNAME` / `API_PASSWORD` or `CLIENT_ID` / `CLIENT_SECRET`
- `api_filter` — optional, one of `"classic"`, `"jpapi"`, `"all"` (default `"all"`)
- `show_deprecated` — optional boolean (default `False`)

**Output:** prints a table of discoverable endpoints:

```
Classic API endpoints (from /classicapi/doc/swagger.yaml):
  accounts              GET POST PUT DELETE
  activationcode        GET PUT
  buildings             GET POST PUT DELETE
  categories            GET POST PUT DELETE
  ...
  computers             GET POST PUT DELETE  [DEPRECATED 2025-02-11]

JPAPI endpoints (from /api/schema):
  v1/categories         GET POST PUT DELETE
  v1/scripts            GET POST PUT DELETE
  v1/computer-prestages GET POST PUT DELETE
  v3/sso                GET PUT
  ...
```

**Shell script integration** — add a new subcommand to jamf-upload.sh:

```bash
elif [[ $object == "list-types" || $object == "listtypes" ]]; then
    processor="JamfSchemaLister"
```

Plus a `--show-deprecated` flag and `--api-filter` argument.

**Files to create:**

- `JamfUploaderProcessors/JamfUploaderLib/JamfSchemaListerBase.py`
- `JamfUploaderProcessors/JamfSchemaLister.py`

### Phase 6: Specific Processors Remain Unchanged

The existing ~40 specific processor files (`JamfCategoryUploader`, `JamfPolicyUploader`, `JamfScriptUploader`, etc.) require **no changes**. They:

- Build data structures from their own parameters (not from generic templates)
- Have custom workflow logic (icon uploads, scope preservation, category resolution)
- Already call into `JamfUploaderBase` methods that will transparently gain schema-backed resolution

These processors remain as convenience wrappers. Users who want maximum flexibility use `JamfObjectUploader` / `JamfObjectReader` — which now handle any schema-discoverable endpoint automatically.

## jamf-upload.sh Compatibility

### No changes required for existing functionality

jamf-upload.sh is a pure I/O wrapper (1756 lines of bash). It:

1. Maps the first CLI argument → processor name
2. Builds a plist from CLI flags using `plutil`
3. Pipes the plist via stdin → Python processor → captures output

All intelligence lives in the Python processors. The schema resolution happens entirely inside `JamfUploaderBase` methods, which are called from the same `execute()` flow regardless of whether the processor was invoked from AutoPkg or from jamf-upload.sh.

**Backward compatibility is guaranteed** because:

- All existing `--type` values (e.g., `policy`, `category`, `computer_prestage`) match existing hardcoded dicts which remain as the first-check fast path
- The schema registry is only consulted as a fallback for unknown types
- The `--key X=Y` escape hatch already allows overriding any processor variable

### New endpoint testing via jamf-upload.sh (works immediately)

After implementation, users can test previously unsupported endpoints with zero code changes:

```bash
# Read a JPAPI endpoint that's in the schema but not in current dicts
./jamf-upload.sh read --type sso_settings --all --url https://example.jamfcloud.com ...

# Use a literal JPAPI path as the type (new capability)
./jamf-upload.sh read --type v1/departments --all --url ...

# Upload to a Classic endpoint not in current dicts
./jamf-upload.sh obj --type jsonwebtokenconfigurations \
    --name "My JWT" --template jwt.xml --replace --url ...

# Use Classic resource names directly  
./jamf-upload.sh read --type peripheraltypes --all --url ...

# List all available types from the server
./jamf-upload.sh list-types --url https://example.jamfcloud.com --user admin --pass secret
```

### Changes to jamf-upload.sh

Only two additions, both additive:

1. **New `list-types` subcommand** (~4 lines in the object→processor mapping section)
2. **New `--show-deprecated` and `--api-filter` flags** (~10 lines in the argument parsing section)

## Deprecation Awareness

Both schemas include deprecation markers. The registry will:

- Log a warning via `self.output()` when a processor targets a deprecated endpoint
- Include the deprecation date when available (`x-deprecation-date` in Classic, `deprecated` flag in JPAPI)
- Classic swagger summaries often include the replacement endpoint (e.g., `"(Deprecated). Please transition use to Jamf Pro API endpoint /v2/patch-software-title-configurations"`)

## Dependencies

**None new.** All parsing uses:

- `json` (stdlib) — for JPAPI schema
- `yaml` (PyYAML, bundled with AutoPkg Python — verified available) — for Classic schema
- `os`, `time`, `re` (stdlib) — for caching and normalisation

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Schema not available (network error, auth issue) | Graceful fallback to existing hardcoded dicts; schema lookup is optional enhancement, not a hard dependency |
| Schema format changes in future Jamf Pro versions | OpenAPI 3.x and Swagger 2.0 are stable standards; field-level changes are additive |
| PyYAML not available | Check `import yaml` at startup; if unavailable, skip Classic schema and fall back to hardcoded dict |
| Performance: schema download on every run | 24h file-based cache; schema only fetched once per day per server |
| Alias table doesn't cover all current object_type names | Alias table is a strict superset — any miss falls back to existing dicts, which remain unchanged |
| Platform API endpoints have no schema | Manual overrides retained for all ~7 Platform types; no change from today |

## Implementation Order

| Phase | Effort | Dependencies | Files Modified/Created |
|-------|--------|-------------|----------------------|
| **1. JamfSchemaRegistry** | Medium | None | Create `JamfSchemaRegistry.py` |
| **2. Alias table** | Small | Phase 1 | Within `JamfSchemaRegistry.py` |
| **3. Integrate into Base** | Medium | Phase 1+2 | Modify JamfUploaderBase.py |
| **4. HTTP method selection** | Small | Phase 3 | Modify JamfUploaderBase.py + `JamfObjectUploaderBase.py` |
| **5. JamfSchemaLister** | Small | Phase 1 | Create `JamfSchemaListerBase.py` + `JamfSchemaLister.py`; modify jamf-upload.sh |
| **6. Specific processors** | None | N/A | No changes needed |

Phases 1–3 are the core. Phase 4 is a refinement. Phase 5 is an ergonomic enhancement. Phase 6 confirms no action.

Completed: *Write consolidated proposal* (1/1)

The proposal above consolidates all three discussion threads into a single document: the original 5-phase schema-driven design, the Classic API Swagger schema extension, and the jamf-upload.sh compatibility analysis with the new `JamfSchemaLister` processor.
