#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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
The API endpoint must be defined in the api_endpoints function in JamfUploaderBase.py

All functions are in JamfUploaderLib/JamfObjectUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfMSUPlanUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfMSUPlanUploaderBase,
)

__all__ = ["JamfMSUPlanUploader"]


class JamfMSUPlanUploader(JamfMSUPlanUploaderBase):
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
        "days_until_force_install": {
            "required": False,
            "description": "Days until forced installation of planned managed software update.",
            "default": "7",
        },
        "device_type": {
            "required": False,
            "description": (
                "Device type, must be one of 'computer', 'mobile-device', "
                "'apple-tv' (case-insensitive)."
            ),
            "default": "",
        },
        "group_name": {
            "required": True,
            "description": "Name of the target computer group or mobile device group.",
        },
        "version": {
            "required": True,
            "description": (
                "OS Version to deploy, must be one of 'latest-minor', 'latest-major', "
                "'latest-any', or a valid specific version string for the OS to be applied."
            ),
            "default": "",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfmsuplanuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "device_type": {
            "description": "Device type.",
        },
        "version_type": {
            "description": (
                "Version type, one of 'latest_minor', 'latest_major', 'latest_any', "
                "or 'specific_version'"
            ),
        },
        "specific_version": {
            "description": "Specific version, if 'version_type' is set to 'specific_version'.",
        },
        "force_install_local_datetime": {
            "description": "The date and time of the plan's forced installation deadline."
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfMSUPlanUploader()
    PROCESSOR.execute_shell()
