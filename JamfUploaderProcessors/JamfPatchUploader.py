#!/usr/local/autopkg/python

"""
Copyright 2023 Graham Pugh, Marcel Keßler

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
This processor was written by Marcel Keßler based on other JamfUploader processors
All functions are in JamfUploaderLib/JamfPatchUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPatchUploaderBase import (  # noqa: E402
    JamfPatchUploaderBase,
)

__all__ = ["JamfPatchUploaderBase"]


class JamfPatchUploader(JamfPatchUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a Patch Policy to a Jamf "
        "Cloud or on-prem server."
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
        "pkg_name": {
            "required": False,
            "description": "Name of package which should be used in the patch."
            "Mostly provided by previous AutoPKG recipe/processor.",
            "default": "",
        },
        "version": {
            "required": False,
            "description": "Version string - provided by previous pkg recipe/processor.",
            "default": "",
        },
        "patch_softwaretitle": {
            "required": True,
            "description": (
                "Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. "
                "You need to create the patch softwaretitle by hand, since there is "
                "currently no way to create these via the API."
            ),
            "default": "",
        },
        "patch_name": {
            "required": False,
            "description": (
                "Name of the patch policy (e.g. 'Mozilla Firefox - 93.02.10'). "
                "If no name is provided defaults to '%patch_softwaretitle% - %version%'."
            ),
            "default": "",
        },
        "patch_template": {
            "required": False,
            "description": (
                "XML-Template used for the patch policy. If none is provided, only the "
                "installer will be linked to the corresponding version."
            ),
            "default": "",
        },
        "patch_icon_policy_name": {
            "required": False,
            "description": (
                "Name of an already existing (!) policy (not a patch policy). "
                "The icon of this policy will be extracted and can be used in the patch template "
                "with the variable %patch_icon_id%. There is currently no reasonable "
                "way to upload a custom icon for patch policies."
            ),
            "default": "",
        },
        "replace_patch": {
            "required": False,
            "description": "Overwrite an existing patch policy if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "patch": {"description": "The created/updated patch definition."},
        "jamfpatchuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfPatchUploader()
    PROCESSOR.execute_shell()
