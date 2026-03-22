#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
JamfSchemaRegistry — runtime API schema discovery for JamfUploader.

Downloads and caches the Jamf Pro OpenAPI 3.0 schema (JPAPI) and the
Classic API Swagger 2.0 schema, then provides a unified `resolve()`
method that maps an object_type string to its endpoint metadata.

Copyright 2026 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
import re
import time

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ---------------------------------------------------------------------------
# Alias table: maps JamfUploader internal object_type names to the
# resource name used in the Classic API swagger schema.
# Only entries that cannot be derived by simple normalisation are listed.
# ---------------------------------------------------------------------------
CLASSIC_ALIAS_TABLE = {
    "account": "accounts",
    "account_user": "accounts",
    "account_group": "accounts",
    "activation_code_settings": "activationcode",
    "advanced_computer_search": "advancedcomputersearches",
    "advanced_mobile_device_search": "advancedmobiledevicesearches",
    "computer_group": "computergroups",
    "configuration_profile": "mobiledeviceconfigurationprofiles",
    "distribution_point": "distributionpoints",
    "dock_item": "dockitems",
    "ldap_server": "ldapservers",
    "logflush": "logflush",
    "mac_application": "macapplications",
    "mobile_device_application": "mobiledeviceapplications",
    "mobile_device_extension_attribute": "mobiledeviceextensionattributes",
    "mobile_device_group": "mobiledevicegroups",
    "network_segment": "networksegments",
    "os_x_configuration_profile": "osxconfigurationprofiles",
    "package": "packages",
    "patch_policy": "patchpolicies",
    "patch_software_title": "patchsoftwaretitles",
    "policy": "policies",
    "policy_icon": "fileuploads",
    "restricted_software": "restrictedsoftware",
}

# Object list key overrides for Classic API objects whose XML/JSON list
# wrapper name doesn't match the simple tag name.
CLASSIC_LIST_KEY_OVERRIDES = {
    "accounts": "accounts",
    "activationcode": "activation_code",
    "advancedcomputersearches": "advanced_computer_searches",
    "advancedmobiledevicesearches": "advanced_mobile_device_searches",
    "computergroups": "computer_groups",
    "mobiledeviceconfigurationprofiles": "configuration_profiles",
    "distributionpoints": "distribution_points",
    "dockitems": "dock_items",
    "ldapservers": "ldap_servers",
    "macapplications": "mac_applications",
    "mobiledeviceapplications": "mobile_device_applications",
    "mobiledeviceextensionattributes": "mobile_device_extension_attributes",
    "mobiledevicegroups": "mobile_device_groups",
    "networksegments": "network_segments",
    "osxconfigurationprofiles": "os_x_configuration_profiles",
    "patchpolicies": "patch_policies",
    "patchsoftwaretitles": "patch_software_titles",
    "restrictedsoftware": "restricted_software",
}

# ---------------------------------------------------------------------------
# JPAPI alias table: maps JamfUploader internal object_type names to the
# base_path key used in the parsed JPAPI schema (version/resource form).
# Every known JPAPI object_type is listed here so that api_type() can
# resolve types offline (before authentication).
# ---------------------------------------------------------------------------
JPAPI_ALIAS_TABLE = {
    "api_client": "v1/api-integrations",
    "api_role": "v1/api-roles",
    "app_installers_deployment": "v1/app-installers/deployments",
    "app_installers_title": "v1/app-installers/titles",
    "app_installers_t_and_c_settings": "v1/app-installers/terms-and-conditions",
    "app_installers_accept_t_and_c_command": (
        "v1/app-installers/terms-and-conditions/accept"
    ),
    "category": "v1/categories",
    "check_in_settings": "v3/check-in",
    "cloud_distribution_point": "v1/cloud-distribution-point",
    "cloud_ldap": "v2/cloud-ldaps",
    "computer": "preview/computers",
    "computer_extension_attribute": "v1/computer-extension-attributes",
    "computer_group_v1": "v1/computer-groups",
    "computer_inventory_collection_settings": (
        "v1/computer-inventory-collection-settings"
    ),
    "computer_prestage": "v3/computer-prestages",
    "device_communication_settings": "v1/device-communication-settings",
    "enrollment_customization": "v2/enrollment-customizations",
    "enrollment_settings": "v4/enrollment",
    "failover": "v1/sso/failover",
    "failover_generate_command": "v1/sso/failover/generate",
    "group": "v1/groups",
    "icon": "v1/icon",
    "impact_alert_notification_settings": "v1/impact-alert-notification-settings",
    "jamf_pro_version_settings": "v1/jamf-pro-version",
    "jamf_protect_plans_sync_command": "v1/jamf-protect/plans/sync",
    "jamf_protect_register_settings": "v1/jamf-protect/register",
    "jamf_protect_settings": "v1/jamf-protect",
    "jcds": "v1/jcds",
    "laps_settings": "v2/local-admin-password/settings",
    "managed_software_updates_available_updates": (
        "v1/managed-software-updates/available-updates"
    ),
    "managed_software_updates_feature_toggle_settings": (
        "v1/managed-software-updates/plans/feature-toggle"
    ),
    "managed_software_updates_plans": "v1/managed-software-updates/plans",
    "managed_software_updates_plans_events": (
        "v1/managed-software-updates/plans/{id}/events"
    ),
    "managed_software_updates_plans_group_settings": (
        "v1/managed-software-updates/plans/group"
    ),
    "managed_software_updates_update_statuses": (
        "v1/managed-software-updates/update-statuses"
    ),
    "mobile_device": "v2/mobile-devices",
    "mobile_device_extension_attribute_v1": "v1/mobile-device-extension-attributes",
    "mobile_device_group_v1": "v1/mobile-device-groups",
    "mobile_device_prestage": "v1/mobile-device-prestages",
    "oauth": "v1/oauth/token",
    "package_v1": "v1/packages",
    "policy_properties_settings": "v1/policy-properties",
    "script": "v1/scripts",
    "self_service_settings": "v1/self-service/settings",
    "self_service_plus_settings": "v1/self-service-plus/settings",
    "smart_computer_group": "v2/computer-groups/smart-groups",
    "smart_computer_group_membership": "v2/computer-groups/smart-group-membership",
    "smart_mobile_device_group": "v1/mobile-device-groups/smart-groups",
    "smart_mobile_device_group_membership": (
        "v1/mobile-device-groups/smart-group-membership"
    ),
    "smtp_server_settings": "v2/smtp-server",
    "sso_cert_command": "v2/sso/cert",
    "sso_settings": "v3/sso",
    "static_computer_group": "v2/computer-groups/static-groups",
    "static_mobile_device_group": "v1/mobile-device-groups/static-groups",
    "token": "v1/auth/token",
    "volume_purchasing_location": "v1/volume-purchasing-locations",
}

# ---------------------------------------------------------------------------
# JPAPI key overrides: name_key / id_key for JPAPI object types whose
# schema-introspected keys may differ from the default "name" / "id".
# These act as a safety net when schema extraction doesn't detect the
# correct field names.
# ---------------------------------------------------------------------------
JPAPI_KEY_OVERRIDES = {
    "api_client": {"name_key": "displayName"},
    "api_role": {"name_key": "displayName"},
    "app_installers_title": {"name_key": "titleName"},
    "computer_prestage": {"name_key": "displayName"},
    "enrollment_customization": {"name_key": "displayName"},
    "group": {"name_key": "groupName", "id_key": "groupPlatformId"},
    "managed_software_updates_available_updates": {
        "name_key": "availableUpdates",
    },
    "managed_software_updates_plans": {"name_key": "planUuid"},
    "managed_software_updates_plans_events": {"name_key": "id"},
    "mobile_device_prestage": {"name_key": "displayName"},
    "smart_mobile_device_group": {
        "name_key": "groupName",
        "id_key": "groupId",
    },
    "static_mobile_device_group": {
        "name_key": "groupName",
        "id_key": "groupId",
    },
}

# Cache TTL in seconds (24 hours)
SCHEMA_CACHE_TTL = 86400


class JamfSchemaRegistry:
    """Fetches, caches and queries Jamf Pro API schemas.

    Args:
        jamf_url:  The base Jamf Pro URL (e.g. https://example.jamfcloud.com).
        cache_dir: Directory for schema cache files.
        log_fn:    Optional callable(msg, verbose_level) for logging.
    """

    def __init__(self, jamf_url, cache_dir, log_fn=None):
        self.jamf_url = jamf_url.rstrip("/")
        self.cache_dir = cache_dir
        self._log = log_fn or (lambda msg, **kw: None)
        self._classic_resources = None  # populated on first use
        self._jpapi_resources = None  # populated on first use

    @property
    def schemas_loaded(self):
        """Return True if schemas have been loaded (or at least attempted)."""
        return self._classic_resources is not None and self._jpapi_resources is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, object_type):
        """Resolve an object_type to endpoint metadata.

        Returns a dict with keys:
            api_type       "classic" or "jpapi"
            endpoint       The URL path (e.g. "JSSResource/policies" or
                           "api/v1/categories")
            methods        set of HTTP methods (e.g. {"get","post","put","delete"})
            name_key       Field name for the object's name (e.g. "name")
            id_key         Field name for the object's ID (e.g. "id")
            list_key       Key for the list wrapper in responses
            deprecated     bool
            deprecation_date  str or ""

        Returns None if the object_type cannot be resolved.
        """
        self._ensure_loaded()

        # --- 1. Try Classic alias table (explicit Classic types) ---
        classic_key = CLASSIC_ALIAS_TABLE.get(object_type)
        if classic_key and classic_key in self._classic_resources:
            return self._build_classic_result(classic_key, object_type)

        # --- 2. Try JPAPI alias table (explicit JPAPI types) ---
        jpapi_alias_key = JPAPI_ALIAS_TABLE.get(object_type)
        if jpapi_alias_key:
            match = self._find_jpapi_by_alias(jpapi_alias_key)
            if match:
                return self._build_jpapi_result(
                    match, self._jpapi_resources[match], object_type
                )

        # --- 3. Direct Classic resource name (e.g. "policies") ---
        if object_type in self._classic_resources:
            return self._build_classic_result(object_type, object_type)

        # --- 4. Try JPAPI auto-resolution for non-aliased types ---
        jpapi_hit = self._find_jpapi_resource(object_type)
        if jpapi_hit:
            return jpapi_hit

        # --- 5. Treat object_type as a literal path fragment ---
        if "/" in object_type:
            # e.g. "v1/departments" → look up "api/v1/departments" in JPAPI
            literal = self._find_jpapi_by_path(object_type)
            if literal:
                return literal
            # or "JSSResource/..." for Classic
            if object_type.startswith("JSSResource/"):
                resource = object_type.split("/")[1]
                if resource in self._classic_resources:
                    return self._build_classic_result(resource, object_type)

        # --- 6. Fall back to Classic normalisation ---
        normalised = self._normalise_to_classic(object_type)
        if normalised and normalised in self._classic_resources:
            return self._build_classic_result(normalised, object_type)

        return None

    def get_classic_resources(self):
        """Return the parsed Classic API resource dict (for listing)."""
        self._ensure_loaded()
        return dict(self._classic_resources) if self._classic_resources else {}

    def get_jpapi_resources(self):
        """Return the parsed JPAPI resource dict (for listing)."""
        self._ensure_loaded()
        return dict(self._jpapi_resources) if self._jpapi_resources else {}

    # ------------------------------------------------------------------
    # Schema loading and caching
    # ------------------------------------------------------------------

    def load_schemas(self, fetch_fn):
        """Download (or load from cache) both API schemas.

        Args:
            fetch_fn: callable(url) -> (status_code, data)
                      where data is the parsed response body (str or dict).
                      This is provided by the caller so we don't depend on
                      any particular HTTP library.
        """
        self._classic_resources = {}
        self._jpapi_resources = {}

        # --- JPAPI schema (JSON) ---
        jpapi_cache = os.path.join(self.cache_dir, "jpapi_schema.json")
        jpapi_data = self._load_cached(jpapi_cache)
        if jpapi_data is None:
            self._log("Fetching JPAPI schema from server...", verbose_level=2)
            status, data = fetch_fn(f"{self.jamf_url}/api/schema")
            if status and status < 400 and data:
                jpapi_data = data if isinstance(data, dict) else self._try_json(data)
                if jpapi_data:
                    self._save_cache(jpapi_cache, json.dumps(jpapi_data))
            else:
                self._log(
                    f"WARNING: Could not fetch JPAPI schema (HTTP {status})",
                    verbose_level=1,
                )

        if jpapi_data:
            self._jpapi_resources = self._parse_jpapi_schema(jpapi_data)
            self._log(
                f"JPAPI schema loaded: {len(self._jpapi_resources)} resources",
                verbose_level=2,
            )

        # --- Classic schema (YAML) ---
        if not YAML_AVAILABLE:
            self._log(
                "WARNING: PyYAML not available — Classic schema discovery disabled",
                verbose_level=1,
            )
        else:
            classic_cache = os.path.join(self.cache_dir, "classic_schema.yaml")
            classic_raw = self._load_cached(classic_cache)
            if classic_raw is None:
                self._log("Fetching Classic API schema from server...", verbose_level=2)
                status, data = fetch_fn(f"{self.jamf_url}/classicapi/doc/swagger.yaml")
                if status and status < 400 and data:
                    if isinstance(data, dict):
                        # Already parsed (unlikely for YAML endpoint)
                        classic_raw = data
                        self._save_cache(
                            classic_cache, yaml.dump(data, default_flow_style=False)
                        )
                    elif isinstance(data, (str, bytes)):
                        raw_str = (
                            data.decode("utf-8") if isinstance(data, bytes) else data
                        )
                        self._save_cache(classic_cache, raw_str)
                        classic_raw = raw_str
                    else:
                        self._log(
                            f"WARNING: Unexpected Classic schema data type: "
                            f"{type(data)}",
                            verbose_level=1,
                        )
                else:
                    self._log(
                        f"WARNING: Could not fetch Classic schema (HTTP {status})",
                        verbose_level=1,
                    )

            if classic_raw is not None:
                if isinstance(classic_raw, str):
                    classic_data = yaml.safe_load(classic_raw)
                else:
                    classic_data = classic_raw
                if classic_data:
                    self._classic_resources = self._parse_classic_schema(classic_data)
                    self._log(
                        f"Classic schema loaded: "
                        f"{len(self._classic_resources)} resources",
                        verbose_level=2,
                    )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cached(self, path):
        """Return cached file contents if fresh, else None."""
        if os.path.exists(path):
            age = time.time() - os.path.getmtime(path)
            if age < SCHEMA_CACHE_TTL:
                self._log(
                    f"Using cached schema: {path} (age: {int(age)}s)", verbose_level=3
                )
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
                # For the JPAPI JSON cache, parse it
                if path.endswith(".json"):
                    return self._try_json(raw)
                return raw
            else:
                self._log(
                    f"Schema cache expired: {path} (age: {int(age)}s)", verbose_level=2
                )
        return None

    def _save_cache(self, path, content):
        """Write content to a cache file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._log(f"Schema cached to: {path}", verbose_level=3)

    @staticmethod
    def _try_json(raw):
        """Try to parse a string as JSON, return None on failure."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Classic API (Swagger 2.0) parsing
    # ------------------------------------------------------------------

    def _parse_classic_schema(self, schema):
        """Parse a Swagger 2.0 Classic API schema into resource metadata."""
        resources = {}

        for path, methods in schema.get("paths", {}).items():
            parts = path.strip("/").split("/")
            if not parts or not parts[0]:
                continue
            resource_name = parts[0]

            if resource_name not in resources:
                resources[resource_name] = {
                    "methods": set(),
                    "deprecated": False,
                    "deprecation_date": "",
                    "has_name_path": False,
                    "has_id_path": False,
                }

            for method, details in methods.items():
                if method not in ("get", "post", "put", "delete"):
                    continue
                resources[resource_name]["methods"].add(method)
                if details.get("deprecated"):
                    resources[resource_name]["deprecated"] = True
                    dep_date = details.get("x-deprecation-date", "")
                    if dep_date:
                        resources[resource_name]["deprecation_date"] = str(dep_date)

            # Track path patterns
            if "/id/{id}" in path and "/subset/" not in path:
                resources[resource_name]["has_id_path"] = True
            if "/name/{name}" in path:
                resources[resource_name]["has_name_path"] = True

        return resources

    # ------------------------------------------------------------------
    # JPAPI (OpenAPI 3.0) parsing
    # ------------------------------------------------------------------

    def _parse_jpapi_schema(self, schema):
        """Parse an OpenAPI 3.0 JPAPI schema into resource metadata."""
        resources = {}

        for path, methods in schema.get("paths", {}).items():
            # Normalise the path: strip leading /
            clean = path.lstrip("/")
            # Derive a resource key from the path
            # e.g. "v1/categories" or "v1/categories/{id}"
            # Strip trailing /{id} or /{uuid} etc.
            base_path = re.sub(r"/\{[^}]+\}$", "", clean)
            if not base_path:
                continue

            if base_path not in resources:
                resources[base_path] = {
                    "full_path": f"api/{base_path}",
                    "methods": set(),
                    "deprecated": False,
                    "deprecation_date": "",
                    "has_id_param": False,
                    "name_key": "name",
                    "id_key": "id",
                    "is_action": False,
                }

            for method, details in methods.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                resources[base_path]["methods"].add(method)
                if details.get("deprecated"):
                    resources[base_path]["deprecated"] = True

                # Check for x-action flag
                if details.get("x-action"):
                    resources[base_path]["is_action"] = True

            # If the path has an {id} parameter, note it
            if re.search(r"/\{[^}]+\}$", clean):
                resources[base_path]["has_id_param"] = True

            # Try to extract name/id keys from request body schema
            self._extract_jpapi_keys(schema, methods, resources[base_path])

        return resources

    def _extract_jpapi_keys(self, root_schema, methods, resource):
        """Try to find name_key and id_key from JPAPI request/response schemas."""
        # Look at PUT or POST request body for field names
        for method in ("put", "post", "patch", "get"):
            details = methods.get(method, {})

            # Check response schema for GET
            if method == "get":
                responses = details.get("responses", {})
                ok_resp = responses.get("200", {})
                content = ok_resp.get("content", {})
                json_ct = content.get("application/json", {})
                schema_ref = json_ct.get("schema", {})
            else:
                # Check request body
                req_body = details.get("requestBody", {})
                content = req_body.get("content", {})
                json_ct = content.get("application/json", {})
                schema_ref = json_ct.get("schema", {})

            if not schema_ref:
                continue

            # Resolve $ref if present
            ref = schema_ref.get("$ref", "")
            if ref:
                schema_def = self._resolve_ref(root_schema, ref)
            else:
                schema_def = schema_ref

            if not schema_def:
                continue

            props = schema_def.get("properties", {})
            if not props:
                continue

            # Look for name-like keys
            for candidate in ("displayName", "groupName", "titleName", "name"):
                if candidate in props:
                    resource["name_key"] = candidate
                    break

            # Look for ID keys
            for candidate in ("groupPlatformId", "groupId", "id"):
                if candidate in props:
                    resource["id_key"] = candidate
                    break

            # Found what we need
            if resource["name_key"] != "name" or resource["id_key"] != "id":
                break

    @staticmethod
    def _resolve_ref(root_schema, ref):
        """Resolve a JSON $ref like '#/components/schemas/Category'."""
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        node = root_schema
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return None
            if node is None:
                return None
        return node

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        """Ensure schemas have been loaded (or at least attempted)."""
        if self._classic_resources is None or self._jpapi_resources is None:
            # Schemas not loaded yet — they'll be empty dicts.
            # The caller should have called load_schemas() first.
            if self._classic_resources is None:
                self._classic_resources = {}
            if self._jpapi_resources is None:
                self._jpapi_resources = {}

    def _build_classic_result(self, resource_name, object_type):
        """Build a resolved result dict from a Classic schema resource."""
        info = self._classic_resources[resource_name]

        # Determine the list key
        list_key = CLASSIC_LIST_KEY_OVERRIDES.get(resource_name, resource_name)

        return {
            "api_type": "classic",
            "endpoint": f"JSSResource/{resource_name}",
            "methods": info["methods"],
            "name_key": "name",
            "id_key": "id",
            "list_key": list_key,
            "deprecated": info["deprecated"],
            "deprecation_date": info.get("deprecation_date", ""),
        }

    def _find_jpapi_by_alias(self, alias_path):
        """Find the JPAPI resource key matching an alias path.

        Handles template variables: if alias_path contains {param},
        matches against resource keys where the parameter name may differ.
        """
        if alias_path in self._jpapi_resources:
            return alias_path
        # Handle template variables (e.g. "v1/.../plans/{id}/events")
        if "{" in alias_path:
            pattern = re.sub(r"\\\{[^}]+\\\}", r"\{[^}]+\}", re.escape(alias_path))
            for base_path in self._jpapi_resources:
                if re.fullmatch(pattern, base_path):
                    return base_path
        return None

    def _find_jpapi_resource(self, object_type):
        """Try to find a JPAPI resource matching the object_type."""
        # Strategy: convert object_type like "computer_prestage" to
        # a hyphenated form "computer-prestages" and search path keys
        # for a suffix match.
        hyphenated = object_type.replace("_", "-")

        # Try plural forms
        candidates = [
            hyphenated,
            hyphenated + "s",
            hyphenated + "es",
        ]
        # y -> ies (e.g. "category" -> "categories")
        if hyphenated.endswith("y"):
            candidates.append(hyphenated[:-1] + "ies")
        # Also try without trailing 's' if it ends with one
        if hyphenated.endswith("s"):
            candidates.append(hyphenated[:-1])

        for base_path, info in self._jpapi_resources.items():
            # base_path is like "v1/categories" or "v3/computer-prestages"
            path_suffix = base_path.split("/", 1)[-1] if "/" in base_path else base_path
            if path_suffix in candidates:
                return self._build_jpapi_result(base_path, info, object_type)

        return None

    def _find_jpapi_by_path(self, path_fragment):
        """Look up a literal path fragment in the JPAPI resources."""
        # path_fragment could be "v1/departments" — match against base_path
        for base_path, info in self._jpapi_resources.items():
            if base_path == path_fragment:
                return self._build_jpapi_result(base_path, info)
        return None

    @staticmethod
    def _build_jpapi_result(base_path, info, object_type=None):
        """Build a resolved result dict from a JPAPI schema resource."""
        result = {
            "api_type": "jpapi",
            "endpoint": info["full_path"],
            "methods": info["methods"],
            "name_key": info.get("name_key", "name"),
            "id_key": info.get("id_key", "id"),
            "list_key": base_path.split("/")[-1] if "/" in base_path else base_path,
            "deprecated": info["deprecated"],
            "deprecation_date": info.get("deprecation_date", ""),
        }
        # Apply key overrides for types with non-standard field names
        if object_type and object_type in JPAPI_KEY_OVERRIDES:
            overrides = JPAPI_KEY_OVERRIDES[object_type]
            if "name_key" in overrides:
                result["name_key"] = overrides["name_key"]
            if "id_key" in overrides:
                result["id_key"] = overrides["id_key"]
        return result

    def _normalise_to_classic(self, object_type):
        """Try to convert an object_type to a Classic resource name.

        Returns the matching resource name or None.
        """
        normalised = object_type.replace("_", "").lower()
        candidates = [normalised, normalised + "s", normalised + "es"]
        # y -> ies (e.g. "category" -> "categories")
        if normalised.endswith("y"):
            candidates.append(normalised[:-1] + "ies")
        for candidate in candidates:
            if candidate in self._classic_resources:
                return candidate
        return None
