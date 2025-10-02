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
Developed from an idea posted at
    https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021

All functions are in JamfUploaderLib/JamfPackageUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPackageUploaderBase import (  # noqa: E402
    JamfPackageUploaderBase,
)

__all__ = ["JamfPackageUploader"]


class JamfPackageUploader(JamfPackageUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a package to a JCDS or File "
        "Share Distribution Point."
        "Can be run as a post-processor for a pkg recipe or in a child recipe. "
        "The pkg recipe must output pkg_path or this will fail."
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
        "SMB_URL": {
            "required": False,
            "description": (
                "URL to a Jamf Pro file share distribution point "
                "which should be in the form smb://server/share "
                "or a local DP in the form file://path. "
                "Subsequent DPs can be configured using SMB2_URL, SMB3_URL etc. "
                "Accompanying username and password must be supplied for each DP, e.g. "
                "SMB2_USERNAME, SMB2_PASSWORD etc."
            ),
            "default": "",
        },
        "SMB_USERNAME": {
            "required": False,
            "description": (
                "Username of account with appropriate access to "
                "a Jamf Pro fileshare distribution point."
            ),
            "default": "",
        },
        "SMB_PASSWORD": {
            "required": False,
            "description": (
                "Password of account with appropriate access to "
                "a Jamf Pro fileshare distribution point."
            ),
            "default": "",
        },
        "SMB_SHARES": {
            "required": False,
            "description": (
                "An array of dictionaries containing SMB_URL, SMB_USERNAME and "
                "SMB_PASSWORD, as an alternative to individual keys. Any individual keys will "
                "override this complete array. The array can only be provided via the AutoPkg "
                "preferences file."
            ),
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
        "pkg_path": {
            "required": False,
            "description": "Path to a pkg or dmg to import - provided by "
            "previous pkg recipe/processor.",
            "default": "",
        },
        "version": {
            "required": False,
            "description": "Version string - provided by "
            "previous pkg recipe/processor.",
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
        "replace_pkg": {
            "required": False,
            "description": "Overwrite an existing package if True.",
            "default": "False",
        },
        "jcds_mode": {
            "required": False,
            "description": (
                "This option is no longer functional. "
                "A warning message is displayed if set."
            ),
            "default": "False",
        },
        "jcds2_mode": {
            "required": False,
            "description": "Use jcds2 endpoint if True.",
            "default": "False",
        },
        "aws_cdp_mode": {
            "required": False,
            "description": "Use AWS CDP mode if True.",
            "default": "False",
        },
        "replace_pkg_metadata": {
            "required": False,
            "description": (
                "Overwrite existing package metadata and continue if True, "
                "even if the package object is not re-uploaded."
            ),
            "default": "False",
        },
        "skip_metadata_upload": {
            "required": False,
            "description": (
                "Skip processing package metadata and continue if True. "
                "Designed for organisations where amending packages is not allowed."
            ),
            "default": "False",
        },
        "recalculate": {
            "required": False,
            "description": "Recalculate package metadata in JCDS.",
            "default": "False",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "pkg_path": {
            "description": "The path of the package as provided from the parent recipe.",
        },
        "pkg_name": {"description": "The name of the uploaded package."},
        "pkg_uploaded": {
            "description": "True/False depending if a package was uploaded or not.",
        },
        "jamfpackageuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfPackageUploader()
    PROCESSOR.execute_shell()
