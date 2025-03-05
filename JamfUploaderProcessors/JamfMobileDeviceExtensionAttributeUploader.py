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
All functions are in JamfUploaderLib/JamfMobileDeviceExtensionAttributeUploaderBase.py
"""

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfMobileDeviceExtensionAttributeUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfMobileDeviceExtensionAttributeUploaderBase,
)

__all__ = ["JamfMobileDeviceExtensionAttributeUploader"]


class JamfMobileDeviceExtensionAttributeUploader(
    JamfMobileDeviceExtensionAttributeUploaderBase
):
    description = (
        "A processor for AutoPkg that will upload an Extension Attribute item to a "
        "Jamf Cloud or on-prem server."
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
        "ea_name": {
            "required": False,
            "description": "Extension Attribute name",
            "default": "",
        },
        "ea_input_type": {
            "required": False,
            "description": ("Type of EA. One of popup, text, or ldap."),
            "default": "text",
        },
        "ea_popup_choices": {
            "required": False,
            "description": "A comma-separated list of choices for a popup EA.",
        },
        "ea_inventory_display": {
            "required": False,
            "description": (
                "Inventory Display value for the EA. One of GENERAL, HARDWARE, "
                "OPERATING_SYSTEM, USER_AND_LOCATION, PURCHASING, EXTENSION_ATTRIBUTES."
            ),
            "default": "EXTENSION_ATTRIBUTES",
        },
        "ea_data_type": {
            "required": False,
            "description": "Data type for the EA. One of String, Integer or Date.",
            "default": "String",
        },
        "ea_description": {
            "required": False,
            "description": "Description for the EA.",
        },
        "ea_directory_service_attribute_mapping": {
            "required": False,
            "description": (
                "Directory Service (LDAP) attribute mapping. "
                "Currently this must be manaully set."
            ),
        },
        "replace_ea": {
            "required": False,
            "description": "Overwrite an existing category if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfmobiledeviceextensionattributeuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfMobileDeviceExtensionAttributeUploader()
    PROCESSOR.execute_shell()
