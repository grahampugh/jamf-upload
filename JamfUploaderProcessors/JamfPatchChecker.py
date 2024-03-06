#!/usr/local/autopkg/python

"""
JamfPatchChecker processor for checking if a patch definition exists for the given 
pkg name and version in Jamf Pro.

Made by Jerker Adolfsson based on the other JamfUploader processors.
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPatchCheckerBase import (  # noqa: E402
    JamfPatchCheckerBase,
)

__all__ = ["JamfPatchChecker"]


class JamfPatchChecker(JamfPatchCheckerBase):
    description = (
        "A processor for AutoPkg that will check if a Patch Policy is ready to be uploaded "
        "to a Jamf Cloud or on-prem server."
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
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "patch_version_found": {
            "description": "Returns True if the specified version is found in the patch software title, "
            "False otherwise."
        },
        "jamfpatchchecker_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfPatchChecker()
    PROCESSOR.execute_shell()
