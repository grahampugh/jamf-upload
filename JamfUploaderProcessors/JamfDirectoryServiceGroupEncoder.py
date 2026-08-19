#!/usr/local/autopkg/python

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

NOTES:
All functions are in JamfUploaderLib/JamfDirectoryServiceGroupEncoderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfDirectoryServiceGroupEncoderBase import (  # noqa: E402
    JamfDirectoryServiceGroupEncoderBase,
)

__all__ = ["JamfDirectoryServiceGroupEncoder"]


class JamfDirectoryServiceGroupEncoder(JamfDirectoryServiceGroupEncoderBase):
    description = (
        "A processor for AutoPkg that resolves a directory service group "
        "name to the base64-encoded {uuid,serverId} value required by directory "
        "service group smart group and advanced search criteria (Jamf Pro 11.29+). "
        "Outputs directory_service_group_value for substitution into a template."
    )

    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": False,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": False,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "CLIENT_ID": {
            "required": False,
            "description": "Client ID with access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": "Secret associated with the Client ID, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "BEARER_TOKEN": {
            "required": False,
            "description": "A pre-existing bearer token for the Jamf Pro API. "
            "If provided, the token will be validated and used directly, "
            "bypassing credential-based authentication.",
        },
        "JAMF_CLI_PROFILE": {
            "required": False,
            "description": "A jamf-cli profile to use to obtain a bearer token. "
            "Requires jamf-cli to be installed and in the PATH. "
            "Set to a profile name to enable.",
            "default": "",
        },
        "PLATFORM_API_REGION": {
            "required": False,
            "description": "Region for Jamf Platform API Gateway (e.g., 'us1', 'eu1', 'au1'). "
            "Required for Platform API authentication.",
            "default": "",
        },
        "PLATFORM_API_TENANT_ID": {
            "required": False,
            "description": "Tenant ID for Jamf Platform API Gateway. "
            "Required for Platform API authentication.",
            "default": "",
        },
        "directory_service_group_name": {
            "required": False,
            "description": "Name of the directory service group to resolve. Must match the "
            "group name in the directory exactly (case-sensitive). An already-encoded "
            "base64 value may also be supplied, in which case it is validated and passed "
            "through unchanged. Not required if directory_service_group_uuid and "
            "directory_service_group_server_id are both supplied.",
            "default": "",
        },
        "directory_service_group_uuid": {
            "required": False,
            "description": "UUID of the directory service group. Supply together with "
            "directory_service_group_server_id to encode the value offline, without "
            "an API lookup.",
            "default": "",
        },
        "directory_service_group_server_id": {
            "required": False,
            "description": "ID of the Directory Service server the group belongs to, which "
            "is either an LDAP server or a Cloud Identity Provider. Supply together with "
            "directory_service_group_uuid to encode the value offline, without an API lookup.",
            "default": "",
        },
        "output_variable_name": {
            "required": False,
            "description": "Optional name of an additional output variable to set to the "
            "encoded value, e.g. 'DS_GROUP_VALUE' so that %DS_GROUP_VALUE% can be used in "
            "a template.",
            "default": "",
        },
        "skip_if": {
            "required": False,
            "description": "Skip the process if the supplied predicate evaluates to True.",
            "default": False,
        },
    }

    output_variables = {
        "directory_service_group_value": {
            "description": "The base64-encoded {uuid,serverId} criterion value."
        },
        "directory_service_group_name": {
            "description": "The resolved directory service group name."
        },
        "directory_service_group_uuid": {
            "description": "The UUID of the resolved directory service group."
        },
        "directory_service_group_server_id": {
            "description": "The ID of the Directory Service server (LDAP server or Cloud "
            "Identity Provider) the resolved group belongs to."
        },
        "process_skipped": {"description": "Returns True if the process was skipped."},
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfDirectoryServiceGroupEncoder()
    PROCESSOR.execute_shell()
