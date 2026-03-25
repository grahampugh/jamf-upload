#!/usr/local/autopkg/python
"""Test script for JamfSchemaRegistry — Phase 1 validation."""

import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "JamfUploaderProcessors",
        "JamfUploaderLib",
    ),
)

from JamfSchemaRegistry import (  # pylint: disable=import-error, wrong-import-position
    JamfSchemaRegistry,
    JPAPI_ALIAS_TABLE,
    JPAPI_KEY_OVERRIDES,
    YAML_AVAILABLE,
)

print(f"Import OK, YAML_AVAILABLE={YAML_AVAILABLE}")

# Quick smoke test with empty data
reg = JamfSchemaRegistry("https://example.jamfcloud.com", "/tmp/test_schema_cache")
print(f"Registry created: {reg.jamf_url}")

# Test Classic schema parsing with minimal data
classic_data = {
    "basePath": "/JSSResource/",
    "paths": {
        "/categories": {
            "get": {
                "tags": ["categories"],
                "operationId": "findCategories",
                "responses": {"200": {}},
            },
        },
        "/categories/id/{id}": {
            "get": {"tags": ["categories"], "responses": {"200": {}}},
            "post": {"tags": ["categories"], "responses": {"200": {}}},
            "put": {"tags": ["categories"], "responses": {"200": {}}},
            "delete": {"tags": ["categories"], "responses": {"200": {}}},
        },
        "/categories/name/{name}": {
            "get": {"tags": ["categories"], "responses": {"200": {}}},
        },
        "/policies": {
            "get": {"tags": ["policies"], "responses": {"200": {}}},
        },
        "/policies/id/{id}": {
            "get": {"tags": ["policies"], "responses": {"200": {}}},
            "post": {"tags": ["policies"], "responses": {"200": {}}},
            "put": {"tags": ["policies"], "responses": {"200": {}}},
            "delete": {"tags": ["policies"], "responses": {"200": {}}},
        },
        "/policies/name/{name}": {
            "get": {"tags": ["policies"], "responses": {"200": {}}},
        },
        "/computergroups": {
            "get": {"tags": ["computergroups"], "responses": {"200": {}}},
        },
        "/computergroups/id/{id}": {
            "get": {"tags": ["computergroups"], "responses": {"200": {}}},
            "post": {"tags": ["computergroups"], "responses": {"200": {}}},
            "put": {"tags": ["computergroups"], "responses": {"200": {}}},
            "delete": {"tags": ["computergroups"], "responses": {"200": {}}},
        },
        "/computergroups/name/{name}": {
            "get": {"tags": ["computergroups"], "responses": {"200": {}}},
        },
        "/computers/id/{id}": {
            "get": {
                "tags": ["computers"],
                "deprecated": True,
                "x-deprecation-date": "2025-02-11",
                "responses": {"200": {}},
            },
            "delete": {
                "tags": ["computers"],
                "deprecated": True,
                "x-deprecation-date": "2025-02-11",
                "responses": {"200": {}},
            },
        },
    },
}
resources = reg._parse_classic_schema(classic_data)
print(f"Classic parsed: {len(resources)} resources")
for name, info in sorted(resources.items()):
    print(
        f"  {name}: methods={sorted(info['methods'])}, deprecated={info['deprecated']}, has_id={info['has_id_path']}, has_name={info['has_name_path']}"
    )

assert "categories" in resources
assert "policies" in resources
assert "computergroups" in resources
assert "computers" in resources
assert resources["computers"]["deprecated"] is True
assert resources["computers"]["deprecation_date"] == "2025-02-11"
assert resources["categories"]["has_name_path"] is True
assert resources["categories"]["has_id_path"] is True
print("  Classic parsing: PASS")

# Test JPAPI schema parsing with minimal data
jpapi_data = {
    "paths": {
        "/v1/categories": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CategoriesSearchResults"
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Category"}
                        }
                    }
                }
            },
        },
        "/v1/categories/{id}": {
            "get": {"responses": {"200": {}}},
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Category"}
                        }
                    }
                }
            },
            "delete": {"responses": {"200": {}}},
        },
        "/v1/scripts": {
            "get": {"responses": {"200": {}}},
            "post": {},
        },
        "/v1/scripts/{id}": {
            "get": {},
            "put": {},
            "delete": {},
        },
        "/v3/computer-prestages": {
            "get": {"responses": {"200": {}}},
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/GetComputerPrestageV3"
                            }
                        }
                    }
                }
            },
        },
        "/v3/computer-prestages/{id}": {
            "get": {},
            "put": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/GetComputerPrestageV3"
                            }
                        }
                    }
                }
            },
            "delete": {},
        },
    },
    "components": {
        "schemas": {
            "Category": {
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "priority": {"type": "integer"},
                },
            },
            "CategoriesSearchResults": {
                "properties": {
                    "totalCount": {"type": "integer"},
                    "results": {"type": "array"},
                },
            },
            "GetComputerPrestageV3": {
                "properties": {
                    "id": {"type": "string"},
                    "displayName": {"type": "string"},
                },
            },
        },
    },
}
jp_resources = reg._parse_jpapi_schema(jpapi_data)
print(f"JPAPI parsed: {len(jp_resources)} resources")
for name, info in sorted(jp_resources.items()):
    print(
        f"  {name}: methods={sorted(info['methods'])}, endpoint={info['full_path']}, name_key={info['name_key']}, id_key={info['id_key']}"
    )

assert "v1/categories" in jp_resources
assert "v1/scripts" in jp_resources
assert "v3/computer-prestages" in jp_resources
assert jp_resources["v3/computer-prestages"]["name_key"] == "displayName"
assert jp_resources["v1/categories"]["name_key"] == "name"
print("  JPAPI parsing: PASS")

# Test resolve() with loaded data
reg._classic_resources = resources
reg._jpapi_resources = jp_resources

# Test 1: Classic alias lookup
result = reg.resolve("policy")
assert result is not None, "policy should resolve"
assert result["api_type"] == "classic"
assert result["endpoint"] == "JSSResource/policies"
print(f"  resolve('policy'): PASS -> {result['endpoint']}")

# Test 2: Classic alias for computer_group
result = reg.resolve("computer_group")
assert result is not None, "computer_group should resolve"
assert result["api_type"] == "classic"
assert result["endpoint"] == "JSSResource/computergroups"
print(f"  resolve('computer_group'): PASS -> {result['endpoint']}")

# Test 3: JPAPI lookup by normalised name
result = reg.resolve("category")
assert result is not None, "category should resolve"
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v1/categories"
print(f"  resolve('category'): PASS -> {result['endpoint']}")

# Test 4: JPAPI lookup for computer_prestage
result = reg.resolve("computer_prestage")
assert result is not None, "computer_prestage should resolve"
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v3/computer-prestages"
assert result["name_key"] == "displayName"
print(
    f"  resolve('computer_prestage'): PASS -> {result['endpoint']}, name_key={result['name_key']}"
)

# Test 5: JPAPI by literal path
result = reg.resolve("v1/scripts")
assert result is not None, "v1/scripts should resolve"
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v1/scripts"
print(f"  resolve('v1/scripts'): PASS -> {result['endpoint']}")

# Test 6: Direct Classic resource name
result = reg.resolve("categories")
assert result is not None, "categories should resolve"
assert result["api_type"] == "classic"
assert result["endpoint"] == "JSSResource/categories"
print(f"  resolve('categories'): PASS -> {result['endpoint']}")

# Test 7: Unknown type returns None
result = reg.resolve("nonexistent_thing")
assert result is None, "nonexistent_thing should not resolve"
print(f"  resolve('nonexistent_thing'): PASS -> None")

# Test 8: Deprecated endpoint
result = reg.resolve("computers")
assert result is not None
assert result["deprecated"] is True
assert result["deprecation_date"] == "2025-02-11"
print(
    f"  resolve('computers'): PASS -> deprecated={result['deprecated']}, date={result['deprecation_date']}"
)

# Test 9: get_classic_resources / get_jpapi_resources
assert len(reg.get_classic_resources()) == 4
assert len(reg.get_jpapi_resources()) == 3
print(f"  get_*_resources(): PASS")

print("\n=== All Phase 1 tests passed! ===")

# ==================================================================
# Phase 2 tests: JPAPI alias table, key overrides, resolve via alias
# ==================================================================
print("\n--- Phase 2: JPAPI alias table & key overrides ---")

# Extend the synthetic JPAPI schema with more paths for alias testing
extra_jpapi_paths = {
    "/v1/api-integrations": {
        "get": {"responses": {"200": {}}},
        "post": {
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ApiIntegration"}
                    }
                }
            },
        },
    },
    "/v1/api-integrations/{id}": {
        "get": {},
        "put": {},
        "delete": {},
    },
    "/v1/sso/failover": {
        "get": {"responses": {"200": {}}},
    },
    "/v1/sso/failover/generate": {
        "post": {},
    },
    "/v3/check-in": {
        "get": {"responses": {"200": {}}},
        "put": {},
    },
    "/v2/computer-groups/smart-groups": {
        "get": {"responses": {"200": {}}},
        "post": {},
    },
    "/v2/computer-groups/smart-groups/{id}": {
        "get": {},
        "put": {},
        "delete": {},
    },
    "/v1/mobile-device-groups/smart-groups": {
        "get": {"responses": {"200": {}}},
        "post": {},
    },
    "/v1/managed-software-updates/plans": {
        "get": {"responses": {"200": {}}},
        "post": {},
    },
    "/v1/managed-software-updates/plans/{id}": {
        "get": {},
        "put": {},
    },
    "/v1/managed-software-updates/plans/{id}/events": {
        "get": {"responses": {"200": {}}},
    },
    "/v1/self-service/settings": {
        "get": {"responses": {"200": {}}},
        "put": {},
    },
    "/v2/smtp-server": {
        "get": {"responses": {"200": {}}},
        "put": {},
    },
}
extra_components = {
    "ApiIntegration": {
        "properties": {
            "id": {"type": "integer"},
            "displayName": {"type": "string"},
        },
    },
}

# Merge extra paths/components into JPAPI data and re-parse
jpapi_data["paths"].update(extra_jpapi_paths)
jpapi_data["components"]["schemas"].update(extra_components)
jp_resources = reg._parse_jpapi_schema(jpapi_data)
reg._jpapi_resources = jp_resources
print(f"Extended JPAPI parsed: {len(jp_resources)} resources")

# Test 10: JPAPI alias — api_client → v1/api-integrations
result = reg.resolve("api_client")
assert result is not None, "api_client should resolve via JPAPI alias"
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v1/api-integrations"
assert (
    result["name_key"] == "displayName"
), f"api_client name_key should be displayName, got {result['name_key']}"
print(
    f"  resolve('api_client'): PASS -> {result['endpoint']}, name_key={result['name_key']}"
)

# Test 11: JPAPI alias — failover → v1/sso/failover (nested path)
result = reg.resolve("failover")
assert result is not None, "failover should resolve via JPAPI alias"
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v1/sso/failover"
print(f"  resolve('failover'): PASS -> {result['endpoint']}")

# Test 12: JPAPI alias — check_in_settings → v3/check-in
result = reg.resolve("check_in_settings")
assert result is not None, "check_in_settings should resolve via JPAPI alias"
assert result["endpoint"] == "api/v3/check-in"
print(f"  resolve('check_in_settings'): PASS -> {result['endpoint']}")

# Test 13: JPAPI alias — smart_computer_group → v2/computer-groups/smart-groups
result = reg.resolve("smart_computer_group")
assert result is not None, "smart_computer_group should resolve via JPAPI alias"
assert result["endpoint"] == "api/v2/computer-groups/smart-groups"
print(f"  resolve('smart_computer_group'): PASS -> {result['endpoint']}")

# Test 14: JPAPI alias — managed_software_updates_plans → nested path
result = reg.resolve("managed_software_updates_plans")
assert result is not None, "managed_software_updates_plans should resolve"
assert result["endpoint"] == "api/v1/managed-software-updates/plans"
assert (
    result["name_key"] == "planUuid"
), f"name_key should be planUuid, got {result['name_key']}"
print(
    f"  resolve('managed_software_updates_plans'): PASS -> {result['endpoint']}, name_key={result['name_key']}"
)

# Test 15: JPAPI alias with template variable — plans events
result = reg.resolve("managed_software_updates_plans_events")
assert result is not None, "managed_software_updates_plans_events should resolve"
assert "managed-software-updates/plans/" in result["endpoint"]
assert result["endpoint"].endswith("/events")
assert result["name_key"] == "id", f"name_key should be id, got {result['name_key']}"
print(
    f"  resolve('managed_software_updates_plans_events'): PASS -> {result['endpoint']}"
)

# Test 16: JPAPI alias — self_service_settings → nested path
result = reg.resolve("self_service_settings")
assert result is not None, "self_service_settings should resolve"
assert result["endpoint"] == "api/v1/self-service/settings"
print(f"  resolve('self_service_settings'): PASS -> {result['endpoint']}")

# Test 17: JPAPI alias — smtp_server_settings → v2/smtp-server
result = reg.resolve("smtp_server_settings")
assert result is not None, "smtp_server_settings should resolve"
assert result["endpoint"] == "api/v2/smtp-server"
print(f"  resolve('smtp_server_settings'): PASS -> {result['endpoint']}")

# Test 18: Key override — computer_prestage uses displayName (from Phase 1 data)
result = reg.resolve("computer_prestage")
assert result is not None
assert (
    result["name_key"] == "displayName"
), f"computer_prestage name_key should be displayName, got {result['name_key']}"
print(
    f"  resolve('computer_prestage') key override: PASS -> name_key={result['name_key']}"
)

# Test 19: Key override — smart_mobile_device_group uses groupName/groupId
result = reg.resolve("smart_mobile_device_group")
assert result is not None
assert (
    result["name_key"] == "groupName"
), f"name_key should be groupName, got {result['name_key']}"
assert (
    result["id_key"] == "groupId"
), f"id_key should be groupId, got {result['id_key']}"
print(
    f"  resolve('smart_mobile_device_group') key override: PASS -> name_key={result['name_key']}, id_key={result['id_key']}"
)

# Test 20: Auto-resolve still works for non-aliased JPAPI types
result = reg.resolve("script")
assert result is not None
assert result["api_type"] == "jpapi"
assert result["endpoint"] == "api/v1/scripts"
print(f"  resolve('script') auto-resolve: PASS -> {result['endpoint']}")

# Test 21: Classic alias still takes precedence for Classic types
result = reg.resolve("policy")
assert result is not None
assert result["api_type"] == "classic"
assert result["endpoint"] == "JSSResource/policies"
print(f"  resolve('policy') Classic precedence: PASS -> {result['endpoint']}")

# Test 22: Verify JPAPI_ALIAS_TABLE has all expected entries
expected_alias_count = 56
actual_alias_count = len(JPAPI_ALIAS_TABLE)
assert actual_alias_count == expected_alias_count, (
    f"JPAPI_ALIAS_TABLE should have {expected_alias_count} entries, "
    f"got {actual_alias_count}"
)
print(f"  JPAPI_ALIAS_TABLE count: PASS ({actual_alias_count} entries)")

# Test 23: Verify JPAPI_KEY_OVERRIDES has expected entries
expected_override_count = 12
actual_override_count = len(JPAPI_KEY_OVERRIDES)
assert actual_override_count == expected_override_count, (
    f"JPAPI_KEY_OVERRIDES should have {expected_override_count} entries, "
    f"got {actual_override_count}"
)
print(f"  JPAPI_KEY_OVERRIDES count: PASS ({actual_override_count} entries)")

print("\n=== All Phase 2 tests passed! ===")

# ==================================================================
# Phase 3 tests: Integration with JamfUploaderBase
# ==================================================================
print("\n--- Phase 3: JamfUploaderBase integration ---")

# We can't import JamfUploaderBase directly (it depends on autopkglib),
# but we can verify:
# 1. The import statement works syntactically
# 2. The schemas_loaded property works correctly
# 3. The registry fallback pattern works as expected

# Test 24: schemas_loaded is False before load_schemas()
fresh_reg = JamfSchemaRegistry("https://test.jamfcloud.com", "/tmp/test_phase3")
assert not fresh_reg.schemas_loaded, "schemas_loaded should be False before loading"
print("  schemas_loaded (before load): PASS -> False")


# Test 25: schemas_loaded is True after load_schemas()
def fake_fetch(url):
    """Return empty schema data for testing."""
    if "swagger.yaml" in url:
        return (200, '{"paths": {}, "basePath": "/JSSResource/"}')
    return (200, '{"paths": {}}')


fresh_reg.load_schemas(fake_fetch)
assert fresh_reg.schemas_loaded, "schemas_loaded should be True after loading"
print("  schemas_loaded (after load): PASS -> True")

# Test 26: Verify the JamfSchemaRegistry import line exists in JamfUploaderBase
base_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "JamfUploaderProcessors",
    "JamfUploaderLib",
    "JamfUploaderBase.py",
)
with open(base_path, "r") as f:
    base_source = f.read()

assert (
    "from JamfSchemaRegistry import" in base_source
    and "JamfSchemaRegistry" in base_source
), "JamfUploaderBase should import JamfSchemaRegistry"
print("  JamfSchemaRegistry import in Base: PASS")

# Test 27: Verify _get_registry method exists
assert "def _get_registry(self, jamf_url):" in base_source
print("  _get_registry method exists: PASS")

# Test 28: Verify _ensure_registry_loaded method exists
assert "def _ensure_registry_loaded(self, jamf_url):" in base_source
print("  _ensure_registry_loaded method exists: PASS")

# Test 29: Verify api_type has registry fallback
assert "registry = self._ensure_registry_loaded(jamf_url)" in base_source
assert 'return resolved["api_type"]' in base_source
print("  api_type registry fallback: PASS")

# Test 30: Verify api_endpoints has registry fallback
assert 'return resolved["endpoint"]' in base_source
print("  api_endpoints registry fallback: PASS")

# Test 31: Verify object_list_types has registry fallback
assert 'return resolved.get("list_key", object_type)' in base_source
print("  object_list_types registry fallback: PASS")

# Test 32: Verify get_namekey has registry fallback
assert 'return resolved.get("name_key", "name")' in base_source
print("  get_namekey registry fallback: PASS")

# Test 33: Verify get_idkey has registry fallback
assert 'return resolved.get("id_key", "id")' in base_source
print("  get_idkey registry fallback: PASS")

# Test 34: Verify deprecation warning in api_type
assert "deprecated endpoint" in base_source
print("  deprecation warning in api_type: PASS")

# Test 35: Verify registry uses schemas_loaded property (not private members)
# Count occurrences of schemas_loaded in JamfUploaderBase
assert (
    "registry.schemas_loaded" in base_source
), "JamfUploaderBase should use schemas_loaded property"
print("  schemas_loaded property used in Base: PASS")

# Test 36: Simulate the registry fallback pattern for a novel object_type
# This tests what would happen when api_type/api_endpoints fall through
# to the registry for a type not in any hardcoded dict
sim_reg = JamfSchemaRegistry("https://sim.jamfcloud.com", "/tmp/test_phase3_sim")
sim_reg._classic_resources = {}
sim_reg._jpapi_resources = {
    "v1/departments": {
        "full_path": "api/v1/departments",
        "methods": {"get", "post", "put", "delete"},
        "deprecated": False,
        "deprecation_date": "",
        "has_id_param": True,
        "name_key": "name",
        "id_key": "id",
        "is_action": False,
    },
}

# Simulating what the Base fallback would do: resolve an unknown type
resolved = sim_reg.resolve("department")
assert resolved is not None, "department should resolve via JPAPI auto-resolution"
assert resolved["api_type"] == "jpapi"
assert resolved["endpoint"] == "api/v1/departments"
assert resolved["name_key"] == "name"
print(f"  Simulated Base fallback for 'department': PASS -> {resolved['endpoint']}")

# Simulating what happens with a completely novel type from the schema
resolved = sim_reg.resolve("v1/departments")
assert resolved is not None, "v1/departments should resolve by literal path"
assert resolved["endpoint"] == "api/v1/departments"
print(f"  Simulated Base fallback for 'v1/departments': PASS -> {resolved['endpoint']}")

print("\n=== All Phase 3 tests passed! ===")

# ==================================================================
# Phase 4 tests: determine_request_method logic
# ==================================================================
print("\n--- Phase 4: HTTP method selection ---")

# We can't call determine_request_method directly (requires autopkglib),
# but we can verify:
# 1. The method exists in JamfUploaderBase.py
# 2. JamfObjectUploaderBase now uses it
# 3. The schema-based method resolution logic works correctly

# Test 37: determine_request_method exists in JamfUploaderBase
assert "def determine_request_method(self, object_type, object_id=None):" in base_source
print("  determine_request_method method exists: PASS")

# Test 38: JamfObjectUploaderBase uses determine_request_method
uploader_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "JamfUploaderProcessors",
    "JamfUploaderLib",
    "JamfObjectUploaderBase.py",
)
with open(uploader_path, "r") as f:
    uploader_source = f.read()

assert "self.determine_request_method(object_type, object_id)" in uploader_source
print("  JamfObjectUploaderBase uses determine_request_method: PASS")

# Test 39: Old hardcoded volume_purchasing_location check removed
assert (
    'object_type == "volume_purchasing_location"' not in uploader_source
), "volume_purchasing_location should no longer be hardcoded"
print("  volume_purchasing_location hardcoding removed: PASS")

# Test 40: Old hardcoded computer_inventory_collection_settings check removed
assert (
    'object_type == "computer_inventory_collection_settings"' not in uploader_source
), "computer_inventory_collection_settings should no longer be hardcoded"
print("  computer_inventory_collection_settings hardcoding removed: PASS")

# Test 41: Special cases are preserved
assert 'object_type == "jamf_protect_register_settings"' in uploader_source
assert 'object_type == "cloud_distribution_point"' in uploader_source
assert '"blueprint_deploy_command"' in uploader_source
print("  Special cases preserved: PASS")


# Test 42-47: Simulate determine_request_method logic with schema data
# Create a mini function that mirrors determine_request_method logic
def sim_determine_method(resolved, object_type, object_id=None):
    """Simulate determine_request_method using resolved schema data."""
    if resolved:
        methods = resolved.get("methods", set())
        api = resolved["api_type"]
        if api == "classic":
            return "PUT" if object_id else "POST"
        if api in ("jpapi", "platform"):
            if object_id or "_settings" in object_type:
                if "patch" in methods:
                    return "PATCH"
                if "put" in methods:
                    return "PUT"
            return "POST"
    # Fallback
    if object_id or "_settings" in object_type:
        return "PUT"
    return "POST"


# Test 42: Classic with ID → PUT
classic_resolved = {
    "api_type": "classic",
    "methods": {"get", "post", "put", "delete"},
}
assert sim_determine_method(classic_resolved, "policy", object_id=42) == "PUT"
print("  Classic + object_id → PUT: PASS")

# Test 43: Classic without ID → POST
assert sim_determine_method(classic_resolved, "policy", object_id=None) == "POST"
print("  Classic + no ID → POST: PASS")

# Test 44: JPAPI with PATCH available + object_id → PATCH
jpapi_patch_resolved = {
    "api_type": "jpapi",
    "methods": {"get", "post", "put", "patch", "delete"},
}
assert (
    sim_determine_method(
        jpapi_patch_resolved, "volume_purchasing_location", object_id=5
    )
    == "PATCH"
)
print("  JPAPI + PATCH available + ID → PATCH: PASS")

# Test 45: JPAPI _settings with PATCH → PATCH
jpapi_settings_resolved = {
    "api_type": "jpapi",
    "methods": {"get", "patch"},
}
assert sim_determine_method(jpapi_settings_resolved, "check_in_settings") == "PATCH"
print("  JPAPI _settings + PATCH → PATCH: PASS")

# Test 46: JPAPI _settings with only PUT → PUT
jpapi_put_only = {
    "api_type": "jpapi",
    "methods": {"get", "put"},
}
assert sim_determine_method(jpapi_put_only, "sso_settings") == "PUT"
print("  JPAPI _settings + only PUT → PUT: PASS")

# Test 47: JPAPI without ID, no _settings → POST
assert sim_determine_method(jpapi_patch_resolved, "category", object_id=None) == "POST"
print("  JPAPI + no ID → POST: PASS")

# Test 48: No schema data, with ID → fallback PUT
assert sim_determine_method(None, "unknown_type", object_id=10) == "PUT"
print("  No schema + ID → fallback PUT: PASS")

# Test 49: No schema data, no ID → fallback POST
assert sim_determine_method(None, "unknown_type") == "POST"
print("  No schema + no ID → fallback POST: PASS")

# Test 50: Real registry resolution — volume_purchasing_location schema says PATCH
# This verifies the actual registry would pick PATCH for this endpoint
vpl_reg = JamfSchemaRegistry("https://vpl.jamfcloud.com", "/tmp/test_vpl")
vpl_reg._classic_resources = {}
vpl_reg._jpapi_resources = {
    "v1/volume-purchasing-locations": {
        "full_path": "api/v1/volume-purchasing-locations",
        "methods": {"get", "post", "patch", "delete"},
        "deprecated": False,
        "deprecation_date": "",
        "has_id_param": True,
        "name_key": "name",
        "id_key": "id",
        "is_action": False,
    },
}
resolved = vpl_reg.resolve("volume_purchasing_location")
assert resolved is not None
method = sim_determine_method(resolved, "volume_purchasing_location", object_id=7)
assert method == "PATCH", f"volume_purchasing_location should use PATCH, got {method}"
print(f"  volume_purchasing_location via registry → PATCH: PASS")

# Test 51: Blueprint with ID — schema says PATCH is available
bp_reg = JamfSchemaRegistry("https://bp.jamfcloud.com", "/tmp/test_bp")
bp_reg._classic_resources = {}
bp_reg._jpapi_resources = {
    "v1/blueprints": {
        "full_path": "api/blueprints/v1/blueprints",
        "methods": {"get", "post", "patch", "delete"},
        "deprecated": False,
        "deprecation_date": "",
        "has_id_param": True,
        "name_key": "name",
        "id_key": "id",
        "is_action": False,
    },
}
# Note: blueprint is a Platform type in the hardcoded dict but would resolve
# via schema if available. In practice the hardcoded dict will catch it first.
# This just tests the schema-based logic in isolation.
bp_resolved = {
    "api_type": "platform",
    "methods": {"get", "post", "patch", "delete"},
}
method = sim_determine_method(bp_resolved, "blueprint", object_id=99)
assert method == "PATCH", f"blueprint with ID should use PATCH, got {method}"
print(f"  blueprint + ID via schema → PATCH: PASS")

print("\n=== All Phase 4 tests passed! ===")

# ==================================================================
# Phase 5 tests: JamfSchemaLister processor
# ==================================================================
print("\n--- Phase 5: JamfSchemaLister processor ---")

# Test 52: JamfSchemaLister.py exists
lister_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "JamfUploaderProcessors",
    "JamfSchemaLister.py",
)
assert os.path.exists(lister_path), "JamfSchemaLister.py should exist"
print("  JamfSchemaLister.py exists: PASS")

# Test 53: JamfSchemaListerBase.py exists
lister_base_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "JamfUploaderProcessors",
    "JamfUploaderLib",
    "JamfSchemaListerBase.py",
)
assert os.path.exists(lister_base_path), "JamfSchemaListerBase.py should exist"
print("  JamfSchemaListerBase.py exists: PASS")

# Test 54: JamfSchemaLister imports JamfSchemaListerBase
with open(lister_path, "r") as f:
    lister_source = f.read()
assert "JamfSchemaListerBase" in lister_source
assert "class JamfSchemaLister" in lister_source
print("  JamfSchemaLister imports JamfSchemaListerBase: PASS")

# Test 55: JamfSchemaListerBase has execute method
with open(lister_base_path, "r") as f:
    lister_base_source = f.read()
assert "def execute(self):" in lister_base_source
assert 'api_filter = self.env.get("api_filter"' in lister_base_source
assert (
    'show_deprecated = self.to_bool(self.env.get("show_deprecated"'
    in lister_base_source
)
print("  JamfSchemaListerBase has execute with api_filter/show_deprecated: PASS")

# Test 56: JamfSchemaLister has correct input_variables
assert '"api_filter"' in lister_source
assert '"show_deprecated"' in lister_source
assert '"JSS_URL"' in lister_source
print("  JamfSchemaLister input_variables: PASS")

# Test 57: JamfSchemaLister has output_variables
assert '"schema_lister_output"' in lister_source
assert '"jamfschemalister_summary_result"' in lister_source
print("  JamfSchemaLister output_variables: PASS")

# Test 58: jamf-upload.sh has list-types subcommand
shell_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "jamf-upload.sh",
)
with open(shell_path, "r") as f:
    shell_source = f.read()
assert 'object == "list-types"' in shell_source
assert 'object == "listtypes"' in shell_source
assert 'processor="JamfSchemaLister"' in shell_source
print("  jamf-upload.sh list-types subcommand: PASS")

# Test 59: jamf-upload.sh has --api-filter flag
assert "--api-filter" in shell_source
assert "api_filter" in shell_source
print("  jamf-upload.sh --api-filter flag: PASS")

# Test 60: jamf-upload.sh has --show-deprecated flag
assert "--show-deprecated" in shell_source
assert "show_deprecated" in shell_source
print("  jamf-upload.sh --show-deprecated flag: PASS")

# Test 61: jamf-upload.sh usage section mentions list-types
assert "list-types" in shell_source
print("  jamf-upload.sh usage mentions list-types: PASS")

# Test 62: Simulate the lister output formatting
# This tests the output logic without needing autopkglib
sim_classic = {
    "categories": {
        "methods": {"get", "post", "put", "delete"},
        "deprecated": False,
        "deprecation_date": "",
    },
    "computers": {
        "methods": {"get", "delete"},
        "deprecated": True,
        "deprecation_date": "2025-02-11",
    },
    "policies": {
        "methods": {"get", "post", "put", "delete"},
        "deprecated": False,
        "deprecation_date": "",
    },
}
sim_jpapi = {
    "v1/categories": {
        "full_path": "api/v1/categories",
        "methods": {"get", "post", "put", "delete"},
        "deprecated": False,
        "deprecation_date": "",
    },
    "v1/scripts": {
        "full_path": "api/v1/scripts",
        "methods": {"get", "post", "put", "delete"},
        "deprecated": False,
        "deprecation_date": "",
    },
}

# Simulate the formatting logic from JamfSchemaListerBase
lines = []
lines.append("")
lines.append("Classic API endpoints (from /classicapi/doc/swagger.yaml):")
for name in sorted(sim_classic):
    info = sim_classic[name]
    show_deprecated_sim = True
    if info.get("deprecated") and not show_deprecated_sim:
        continue
    methods_str = " ".join(m.upper() for m in sorted(info["methods"]))
    dep_marker = ""
    if info.get("deprecated"):
        dep_date = info.get("deprecation_date", "")
        dep_marker = f"  [DEPRECATED {dep_date}]" if dep_date else "  [DEPRECATED]"
    lines.append(f"  {name:<40s} {methods_str}{dep_marker}")

lines.append("")
lines.append("JPAPI endpoints (from /api/schema):")
for name in sorted(sim_jpapi):
    info = sim_jpapi[name]
    methods_str = " ".join(m.upper() for m in sorted(info["methods"]))
    lines.append(f"  {name:<40s} {methods_str}")

output = "\n".join(lines)
assert "categories" in output
assert "DEPRECATED 2025-02-11" in output
assert "v1/scripts" in output
print("  Simulated lister output formatting: PASS")

# Test 63: show_deprecated=False filters deprecated endpoints
lines_filtered = []
for name in sorted(sim_classic):
    info = sim_classic[name]
    if info.get("deprecated") and not False:  # show_deprecated=False
        continue
    lines_filtered.append(name)
assert "computers" not in lines_filtered
assert "categories" in lines_filtered
assert "policies" in lines_filtered
print("  show_deprecated=False filters deprecated: PASS")

print("\n=== All Phase 5 tests passed! ===")
