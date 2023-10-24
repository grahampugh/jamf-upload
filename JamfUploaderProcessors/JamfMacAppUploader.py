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
All functions are in JamfUploaderLib/JamfMacAppUploaderBase.py
"""

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfMacAppUploaderBase import (  # noqa: E402
    JamfMacAppUploaderBase,
)

__all__ = ["JamfMacAppUploader"]


class JamfMacAppUploader(JamfMacAppUploaderBase):
    description = (
        "A processor for AutoPkg that will update or clone a Mac App Store app "
        "object on a Jamf Pro server."
        "Note that an icon can only be successsfully injected into a Mac App Store app "
        "item if Cloud Services Connection is enabled."
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
        "macapp_name": {
            "required": False,
            "description": "Mac App Store app name",
            "default": "",
        },
        "clone_from": {
            "required": False,
            "description": "Mac App Store app name from which to clone this entry",
            "default": "",
        },
        "selfservice_icon_uri": {
            "required": False,
            "description": "Mac App Store app icon URI",
            "default": "",
        },
        "macapp_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_macapp": {
            "required": False,
            "description": "Overwrite an existing Mac App Store app if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfmacappuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "macapp_name": {
            "description": "Jamf object name of the newly created or modified macapp.",
        },
        "macapp_updated": {"description": "Boolean - True if the macapp was changed."},
        "changed_macapp_id": {
            "description": "Jamf object ID of the newly created or modified macapp.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfMacAppUploader()
    PROCESSOR.execute_shell()
