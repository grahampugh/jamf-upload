#!/usr/local/autopkg/python

"""
JamfIconUploader processor for uploading an icon to Jamf Pro using AutoPkg
    by G Pugh
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfIconUploaderBase import (  # noqa: E402
    JamfIconUploaderBase,
)

__all__ = ["JamfIconUploader"]


class JamfIconUploader(JamfIconUploaderBase):
    """A processor for AutoPkg that will upload an icon to a Jamf Cloud or on-prem server.
    Note that an icon can only be successsfully injected into a Mac App Store app item if
    Cloud Services Connection is enabled."""

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
        "icon_file": {
            "required": False,
            "description": "An icon to upload",
            "default": "",
        },
        "icon_uri": {
            "required": False,
            "description": "An icon to upload directly from a Jamf Cloud URI",
            "default": "",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "selfservice_icon_uri": {"description": "The uploaded icon's URI."},
        "icon_id": {"description": "The cuploaded icon's ID."},
        "jamficonuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfIconUploader()
    PROCESSOR.execute_shell()
