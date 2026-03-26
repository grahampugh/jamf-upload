#!/usr/local/autopkg/python

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

NOTES:
All functions are in JamfUploaderLib/JamfComputerStaticGroupUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfComputerStaticGroupUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfComputerStaticGroupUploaderBase,
)

__all__ = ["JamfComputerStaticGroupUploader"]


class JamfComputerStaticGroupUploader(JamfComputerStaticGroupUploaderBase):
    """Processor to read an API object"""

    description = (
        "A processor for AutoPkg that will upload a computer group (smart or "
        "static) to a Jamf Cloud or on-prem server."
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
        "jamf_credentials_manager": {
            "required": False,
            "description": "Use JamfCredentialsManager to obtain a bearer token. "
            "Requires JamfCredentialsManager to be installed at "
            "/usr/local/lib/JamfCredentialsManager. Set to 'True' to enable.",
            "default": "",
        },
        "computergroup_name": {
            "required": False,
            "description": "Computer Group name",
            "default": "",
        },
        "group_description": {
            "required": False,
            "description": "Group description",
            "default": "Created by JamfUploader",
        },
        "replace_group": {
            "required": False,
            "description": "Overwrite an existing Computer Group if True.",
            "default": False,
        },
        "clear_assignments": {
            "required": False,
            "description": "Clear assignments in an existing Computer Group if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
        "max_tries": {
            "required": False,
            "description": (
                "Maximum number of attempts to upload the account. "
                "Must be an integer between 1 and 10."
            ),
            "default": "5",
        },
    }

    output_variables = {
        "jamfcomputerstaticgroupuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfComputerStaticGroupUploader()
    PROCESSOR.execute_shell()
