#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2025 Graham Pugh

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
All functions are in JamfUploaderLib/JamfObjectDeleterBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfObjectDeleterBase import (  # pylint: disable=import-error, wrong-import-position
    JamfObjectDeleterBase,
)

__all__ = ["JamfObjectDeleter"]


class JamfObjectDeleter(JamfObjectDeleterBase):
    """Processor to delete an API object"""

    description = (
        "A processor for AutoPkg that will delete a policy from a Jamf Cloud "
        "or on-prem server."
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
        "object_name": {
            "required": True,
            "description": "Object to delete",
            "default": "",
        },
        "object_type": {
            "required": True,
            "description": "Type of the object. This is the name of the key in the XML template",
            "default": "",
        },
        "skip_and_proceed": {
            "required": False,
            "description": "If True, skip the upload process and proceed.",
            "default": False,
        },
    }

    output_variables = {
        "jamfobjectdeleter_summary_result": {
            "description": "Description of interesting results.",
        },
        "process_skipped": {
            "description": "Boolean - True if the process was skipped due to "
            "skip_and_proceed input variable being set to True.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfObjectDeleter()
    PROCESSOR.execute_shell()
