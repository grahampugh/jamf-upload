#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
2026 Neil Martin

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

import base64
import binascii
import json
import os
import sys

from urllib.parse import quote

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


class JamfDirectoryServiceGroupEncoderBase(JamfUploaderBase):
    """Class for functions used to encode a directory service group criterion value"""

    def encode_ds_group_value(self, uuid, server_id):
        """Return the base64-encoded criterion value for a directory service group.

        The key order and the string type of serverId both matter: they must match
        what the Jamf Pro interface writes, so that a value written by JamfUploader
        is byte-identical to one written by hand.
        """
        ref = {"uuid": str(uuid), "serverId": str(server_id)}
        return base64.b64encode(
            json.dumps(ref, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")

    def decode_ds_group_value(self, value):
        """Return the decoded {uuid,serverId} dict if value is an encoded directory
        service group value, otherwise None (i.e. value is a group name).

        Raises a ProcessorError if the value looks encoded but is malformed, so that
        a typo in a pasted value is not uploaded as if it were a group name.
        """
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            return None
        try:
            ref = json.loads(decoded)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(ref, dict) or not ("uuid" in ref or "serverId" in ref):
            return None

        # it looked encoded, so any defect is an error rather than a group name
        if not ref.get("uuid"):
            raise ProcessorError(
                "ERROR: encoded directory service group value has an empty uuid. The "
                "directory lookup returned no uuid mapping for this group (e.g. Okta "
                "with default mappings). Jamf Pro will not save a criterion without a uuid."
            )
        if not ref.get("serverId"):
            raise ProcessorError(
                "ERROR: encoded directory service group value has an empty serverId"
            )
        return ref

    def get_directory_service_groups(self, api_url, token, group_name):
        """Return the directory service groups whose name matches group_name exactly.

        The API performs a 'contains' search across all configured Directory Service
        servers, so the results are filtered to an exact name match here. The servers
        searched include both LDAP servers and Cloud Identity Providers; the API returns
        the server's ID as 'ldapServerId' in both cases.
        """
        url = f"{api_url}/api/v1/ldap/groups?q={quote(group_name)}"
        r = self.curl(api_type="jpapi", request="GET", url=url, token=token)
        if r.status_code != 200:
            raise ProcessorError(
                f"ERROR: directory service group search failed (HTTP {r.status_code})"
            )
        results = r.output.get("results", []) if isinstance(r.output, dict) else []
        return [group for group in results if group.get("name") == group_name]

    def resolve_ds_group_value(self, api_url, token, group_name):
        """Resolve a directory service group name to its encoded criterion value.

        Returns a tuple of (encoded value, uuid, Directory Service server id).
        """
        groups = self.get_directory_service_groups(api_url, token, group_name)
        if not groups:
            raise ProcessorError(
                f"ERROR: no directory service group named '{group_name}' was found on "
                "any configured Directory Service server. The name must match exactly, "
                "including case."
            )
        if len(groups) > 1:
            servers = ", ".join(str(group.get("ldapServerId")) for group in groups)
            raise ProcessorError(
                f"ERROR: '{group_name}' matches groups on more than one Directory "
                f"Service server (server IDs: {servers}). Supply "
                "directory_service_group_uuid and directory_service_group_server_id "
                "to specify which group to use."
            )

        group = groups[0]
        uuid = group.get("uuid")
        server_id = group.get("ldapServerId")
        if not uuid:
            raise ProcessorError(
                f"ERROR: directory service group '{group_name}' has no uuid mapping. "
                "Jamf Pro will not save a criterion without a uuid - check the Directory "
                "Service mappings for the group's object class."
            )
        self.output(
            f"Resolved '{group_name}': uuid {uuid}, Directory Service server "
            f"ID {server_id}",
            verbose_level=2,
        )
        return (
            self.encode_ds_group_value(uuid, server_id),
            uuid,
            str(server_id),
        )

    def execute(self):
        """Encode a directory service group criterion value"""
        jamf_url = (self.env.get("JSS_URL") or "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        group_name = self.env.get("directory_service_group_name") or ""
        group_uuid = self.env.get("directory_service_group_uuid") or ""
        server_id = self.env.get("directory_service_group_server_id") or ""
        output_variable_name = self.env.get("output_variable_name") or ""
        skip_if = self.get_and_clear_skip_if()

        process_skipped = False

        # skip the process if skip_if is True
        if skip_if and self.predicate_evaluates_as_true(skip_if):
            self.output("Skipping to next process as skip_if evaluated to True")
            process_skipped = True
            self.env["process_skipped"] = process_skipped
            return
        elif skip_if:
            self.output("Not skipping process as skip_if evaluated to False")

        # substitute user-assignable keys
        group_name = self.substitute_assignable_keys(group_name)

        if group_uuid and server_id:
            # encode offline, no API lookup required
            self.output(
                f"Encoding supplied uuid {group_uuid} and Directory Service server "
                f"ID {server_id}"
            )
            encoded_value = self.encode_ds_group_value(group_uuid, server_id)
        elif group_uuid or server_id:
            raise ProcessorError(
                "ERROR: directory_service_group_uuid and "
                "directory_service_group_server_id must be supplied together"
            )
        elif not group_name:
            raise ProcessorError(
                "ERROR: supply either directory_service_group_name, or both "
                "directory_service_group_uuid and directory_service_group_server_id"
            )
        else:
            # an already-encoded value is validated and passed through unchanged
            decoded = self.decode_ds_group_value(group_name)
            if decoded:
                self.output(
                    "Supplied value is already an encoded directory service group "
                    "value, passing it through unchanged"
                )
                encoded_value = group_name
                group_uuid = decoded["uuid"]
                server_id = decoded["serverId"]
                group_name = ""
            else:
                # get a token
                (
                    token,
                    jamf_url,
                    jamf_platform_gw_region,
                    jamf_platform_gw_tenant_id,
                ) = self.auth(
                    jamf_url=jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    region=jamf_platform_gw_region,
                    tenant_id=jamf_platform_gw_tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    token=bearer_token,
                    jamf_cli_profile=jamf_cli_profile,
                )

                # construct the api_url based on the API type
                api_url = self.construct_api_url(
                    jamf_url=jamf_url, region=jamf_platform_gw_region
                )
                self.output(f"API URL is {api_url}", verbose_level=3)

                self.output(f"Looking up directory service group '{group_name}'")
                encoded_value, group_uuid, server_id = self.resolve_ds_group_value(
                    api_url, token, group_name
                )

        self.output(f"Directory service group criterion value: {encoded_value}")

        # output the results
        self.env["directory_service_group_value"] = encoded_value
        self.env["directory_service_group_name"] = group_name
        self.env["directory_service_group_uuid"] = group_uuid
        self.env["directory_service_group_server_id"] = str(server_id)
        if output_variable_name:
            self.env[output_variable_name] = encoded_value
            self.output(
                f"Set '{output_variable_name}' to the encoded value", verbose_level=2
            )
        self.env["process_skipped"] = process_skipped
