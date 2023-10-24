#!/usr/local/autopkg/python

"""
JamfComputerProfileUploader processor for uploading a computer configuration profile
to Jamf Pro using AutoPkg
    by G Pugh

Note that all functions are in JamfUploaderLib/JamfAccountUploaderBase.py
"""

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfComputerProfileUploaderBase import (  # noqa: E402
    JamfComputerProfileUploaderBase,
)

__all__ = ["JamfComputerProfileUploader"]


class JamfComputerProfileUploader(JamfComputerProfileUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a computer configuration "
        "profile to a Jamf Cloud or on-prem server."
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
        "profile_name": {
            "required": False,
            "description": "Configuration Profile name",
            "default": "",
        },
        "payload": {
            "required": False,
            "description": "Path to Configuration Profile payload plist file",
        },
        "mobileconfig": {
            "required": False,
            "description": "Path to Configuration Profile mobileconfig file",
        },
        "identifier": {
            "required": False,
            "description": "Configuration Profile payload identifier",
        },
        "profile_template": {
            "required": False,
            "description": "Path to Configuration Profile XML template file",
        },
        "profile_category": {
            "required": False,
            "description": "a category to assign to the profile",
        },
        "organization": {
            "required": False,
            "description": "Organization to assign to the profile",
        },
        "profile_description": {
            "required": False,
            "description": "a description to assign to the profile",
        },
        "profile_computergroup": {
            "required": False,
            "description": "a computer group that will be scoped to the profile",
        },
        "unsign_profile": {
            "required": False,
            "description": (
                "Unsign a mobileconfig file prior to uploading "
                "if it is signed, if true."
            ),
            "default": False,
        },
        "replace_profile": {
            "required": False,
            "description": "overwrite an existing Configuration Profile if True.",
            "default": False,
        },
        "retain_scope": {
            "required": False,
            "description": "Retain the existing scope if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfcomputerprofileuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfComputerProfileUploader()
    PROCESSOR.execute_shell()
