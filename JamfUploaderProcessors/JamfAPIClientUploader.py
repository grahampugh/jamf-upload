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
All functions are in JamfUploaderLib/JamfAPIClientUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfAPIClientUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfAPIClientUploaderBase,
)

__all__ = ["JamfAPIClientUploader"]


class JamfAPIClientUploader(JamfAPIClientUploaderBase):
    """Processor to create an API Client"""

    description = (
        "A processor for AutoPkg that will upload a script to a Jamf Cloud or "
        "on-prem server."
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
        "api_client_name": {
            "required": False,
            "description": "Name of the API Client in Jamf",
        },
        "api_client_id": {
            "required": False,
            "description": "Client ID of the API Client in Jamf",
        },
        "api_client_enabled": {
            "required": False,
            "description": "Set the API Client to enabled if True",
            "default": False,
        },
        "access_token_lifetime": {
            "required": False,
            "description": "Access Token lifetime in seconds",
            "default": "300",
        },
        "api_role_name": {
            "required": False,
            "description": "API Role to scope to the API Client. Currently limited to a single API Role",
            "default": "",
        },
        "replace_api_client": {
            "required": False,
            "description": "Overwrite an existing script if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "api_client_name": {
            "description": "Name of the API Client in Jamf",
        },
        "api_client_id": {
            "description": "Client ID of the API Client in Jamf",
        },
        "api_client_secret": {
            "description": "Client Secret of the API Client in Jamf",
        },
        "jamfapiclientuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfAPIClientUploader()
    PROCESSOR.execute_shell()
