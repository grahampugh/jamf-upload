#!/usr/local/autopkg/python

"""
Copyright 2023 Graham Pugh

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
All functions are in JamfUploaderLib/JamfPolicyUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPolicyUploaderBase import (  # noqa: E402
    JamfPolicyUploaderBase,
)

__all__ = ["JamfPolicyUploader"]


class JamfPolicyUploader(JamfPolicyUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a policy to a Jamf Cloud or "
        "on-prem server. Optionally, an icon can be uploaded and associated "
        "with the policy."
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
        "policy_name": {
            "required": False,
            "description": "Policy name",
            "default": "",
        },
        "icon": {
            "required": False,
            "description": "Full path to Self Service icon",
            "default": "",
        },
        "policy_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_policy": {
            "required": False,
            "description": "Overwrite an existing policy if True.",
            "default": False,
        },
        "replace_icon": {
            "required": False,
            "description": "Overwrite an existing policy icon if True.",
            "default": False,
        },
        "retain_scope": {
            "required": False,
            "description": "Retain the existing scope if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfpolicyuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "policy_name": {
            "description": "Jamf object name of the newly created or modified policy.",
        },
        "policy_updated": {
            "description": "Boolean - True if the policy was changed.",
        },
        "changed_policy_id": {
            "description": "Jamf object ID of the newly created or modified policy.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfPolicyUploader()
    PROCESSOR.execute_shell()
