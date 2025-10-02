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

All functions are in JamfUploaderLib/JamfComputerPreStageUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfComputerPreStageUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfComputerPreStageUploaderBase,
)

__all__ = ["JamfComputerPreStageUploader"]


class JamfComputerPreStageUploader(JamfComputerPreStageUploaderBase):
    """Processor to upload an API object not covered by the other specific
    JamfUploader processors
    """

    description = (
        "A processor for AutoPkg that will create or update an API object template "
        "on a Jamf Pro server."
        "'Jamf Pro privileges are required by the API_USERNAME user for whatever the endpoint is."
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
        "prestage_name": {
            "required": False,
            "description": "Name of the object. Required except for settings-related objects.",
        },
        "prestage_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_prestage": {
            "required": False,
            "description": "Overwrite an existing object if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfcomputerprestageuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "prestage_name": {
            "description": "Jamf object name of the newly created or modified object.",
        },
        "prestage_updated": {
            "description": "Boolean - True if the object was changed."
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfComputerPreStageUploader()
    PROCESSOR.execute_shell()
