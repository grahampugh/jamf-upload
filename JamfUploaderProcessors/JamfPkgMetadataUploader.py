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

All functions are in JamfUploaderLib/JamfPkgMetadataUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPkgMetadataUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfPkgMetadataUploaderBase,
)

__all__ = ["JamfPkgMetadataUploader"]


class JamfPkgMetadataUploader(JamfPkgMetadataUploaderBase):
    description = (
        "A processor for AutoPkg that will upload package metadata to Jamf Pro."
    )
    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server to which the API user has write access.",
        },
        "API_USERNAME": {
            "required": False,
            "description": (
                "Username of account with appropriate access to "
                "jss, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "API_PASSWORD": {
            "required": False,
            "description": (
                "Password of api user, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "CLIENT_ID": {
            "required": False,
            "description": (
                "Client ID with access to "
                "jss, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": (
                "Secret associated with the Client ID, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "CLOUD_DP": {
            "required": False,
            "description": (
                "Indicates the presence of a Cloud Distribution Point. "
                "The default is deliberately blank. If no SMB DP is configured, "
                "the default setting assumes that the Cloud DP has been enabled. "
                "If at least one SMB DP is configured, the default setting assumes "
                "that no Cloud DP has been set. "
                "This can be overridden by setting CLOUD_DP to True, in which case "
                "packages will be uploaded to both a Cloud DP plus the SMB DP(s)."
            ),
            "default": False,
        },
        "pkg_name": {
            "required": False,
            "description": (
                "Package name. If supplied, will rename the package supplied "
                "in the pkg_path key when uploading it to the fileshare."
            ),
            "default": "",
        },
        "pkg_display_name": {
            "required": False,
            "description": "Package display name.",
            "default": "",
        },
        "pkg_category": {
            "required": False,
            "description": "Package category",
            "default": "",
        },
        "pkg_info": {
            "required": False,
            "description": "Package info field",
            "default": "",
        },
        "pkg_notes": {
            "required": False,
            "description": "Package notes field",
            "default": "",
        },
        "pkg_priority": {
            "required": False,
            "description": "Package priority. Default=10",
            "default": "10",
        },
        "reboot_required": {
            "required": False,
            "description": (
                "Whether a package requires a reboot after installation. "
                "Default='False'"
            ),
            "default": "",
        },
        "os_requirements": {
            "required": False,
            "description": "Package OS requirement",
            "default": "",
        },
        "required_processor": {
            "required": False,
            "description": "Package required processor. Acceptable values are 'x86' or 'None'",
            "default": "None",
        },
        "send_notification": {
            "required": False,
            "description": (
                "Whether to send a notification when a package is installed. "
                "Default='False'"
            ),
            "default": "",
        },
        "replace_pkg_metadata": {
            "required": False,
            "description": (
                "Overwrite existing package metadata and continue if True, "
                "even if the package object is not re-uploaded."
            ),
            "default": "False",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "pkg_name": {"description": "The name of the uploaded package."},
        "jamfpkgmetadatauploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfPkgMetadataUploader()
    PROCESSOR.execute_shell()
