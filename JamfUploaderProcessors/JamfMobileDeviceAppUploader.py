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
All functions are in JamfUploaderLib/JamfMobileDeviceAppUploaderBase.py
"""

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfMobileDeviceAppUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfMobileDeviceAppUploaderBase,
)

__all__ = ["JamfMobileDeviceAppUploader"]


class JamfMobileDeviceAppUploader(JamfMobileDeviceAppUploaderBase):
    description = (
        "A processor for AutoPkg that will update or clone a Mobile device app "
        "object on a Jamf Pro server."
        "Note that an icon can only be successsfully injected into a Mobile device app "
        "item if Cloud Services Connection is enabled."
    )

    __doc__ = description

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
        "mobiledeviceapp_name": {
            "required": False,
            "description": "Mobile device app name",
            "default": "",
        },
        "clone_from": {
            "required": False,
            "description": "Mobile device app name from which to clone this entry",
            "default": "",
        },
        "selfservice_icon_uri": {
            "required": False,
            "description": "Mobile device app icon URI",
            "default": "",
        },
        "mobiledeviceapp_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "appconfig_template": {
            "required": False,
            "description": "Full path to the AppConfig XML template",
        },
        "preferred_volume_purchase_location": {
            "required": False,
            "description": (
                "Text to match within the Volume Purchasing Location name when "
                "prioritizing app content."
            ),
            "default": "",
        },
        "replace_mobiledeviceapp": {
            "required": False,
            "description": "Overwrite an existing Mobile device app if True.",
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
        "jamfmobiledeviceappuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "mobiledeviceapp_name": {
            "description": "Jamf object name of the newly created or modified Mobile device app.",
        },
        "mobiledeviceapp_updated": {
            "description": "Boolean - True if the Mobile device app was changed."
        },
        "changed_mobiledeviceapp_id": {
            "description": "Jamf object ID of the newly created or modified Mobile device app.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfMobileDeviceAppUploader()
    PROCESSOR.execute_shell()
