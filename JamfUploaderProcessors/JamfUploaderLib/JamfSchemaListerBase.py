#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
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

import os.path
import sys

from autopkglib import (  # pylint: disable=import-error
    ProcessorError,
)

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfSchemaListerBase(JamfUploaderBase):
    """Class for listing all discoverable API endpoints from Jamf Pro schemas."""

    def execute(self):
        """List all discoverable API endpoints."""
        jamf_url = self.env.get("JSS_URL", "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        api_filter = self.env.get("api_filter", "all").lower()
        show_deprecated = self.to_bool(self.env.get("show_deprecated", "False"))

        if not jamf_url:
            raise ProcessorError("ERROR: JSS_URL is required")

        # Authenticate
        self.output(f"Connecting to {jamf_url}")
        token = self.handle_api_auth(
            jamf_url,
            jamf_user=jamf_user,
            password=jamf_password,
            client_id=client_id,
            client_secret=client_secret,
        )

        # Load schemas via the registry
        registry = self._ensure_registry_loaded(jamf_url, token)

        lines = []

        # Classic API
        if api_filter in ("all", "classic"):
            classic = registry.get_classic_resources()
            if classic:
                lines.append("")
                lines.append(
                    "Classic API endpoints (from /classicapi/doc/swagger.yaml):"
                )
                for name in sorted(classic):
                    info = classic[name]
                    if info.get("deprecated") and not show_deprecated:
                        continue
                    methods_str = " ".join(m.upper() for m in sorted(info["methods"]))
                    dep_marker = ""
                    if info.get("deprecated"):
                        dep_date = info.get("deprecation_date", "")
                        dep_marker = (
                            f"  [DEPRECATED {dep_date}]"
                            if dep_date
                            else "  [DEPRECATED]"
                        )
                    lines.append(f"  {name:<40s} {methods_str}{dep_marker}")
            else:
                lines.append("")
                lines.append("Classic API: no endpoints discovered")

        # JPAPI
        if api_filter in ("all", "jpapi"):
            jpapi = registry.get_jpapi_resources()
            if jpapi:
                lines.append("")
                lines.append("JPAPI endpoints (from /api/schema):")
                for name in sorted(jpapi):
                    info = jpapi[name]
                    if info.get("deprecated") and not show_deprecated:
                        continue
                    methods_str = " ".join(m.upper() for m in sorted(info["methods"]))
                    dep_marker = ""
                    if info.get("deprecated"):
                        dep_date = info.get("deprecation_date", "")
                        dep_marker = (
                            f"  [DEPRECATED {dep_date}]"
                            if dep_date
                            else "  [DEPRECATED]"
                        )
                    lines.append(f"  {name:<40s} {methods_str}{dep_marker}")
            else:
                lines.append("")
                lines.append("JPAPI: no endpoints discovered")

        output_text = "\n".join(lines)
        self.output(output_text)

        # Set output variables
        self.env["schema_lister_output"] = output_text
        self.env["jamfschemalister_summary_result"] = {
            "summary_text": "The following endpoints were discovered:",
            "report_fields": ["output"],
            "data": {"output": output_text},
        }
