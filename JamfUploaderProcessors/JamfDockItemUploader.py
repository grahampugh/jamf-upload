#!/usr/local/autopkg/python

"""
JamfDockItemUploader processor for uploading a dock item to Jamf Pro using AutoPkg
    by Marcel Keßler based on G Pugh's work
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfDockItemUploaderBase import (  # noqa: E402
    JamfDockItemUploaderBase,
)

__all__ = ["JamfDockItemUploader"]


class JamfDockItemUploader(JamfDockItemUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a Dock item to a Jamf Cloud "
        "or on-prem server."
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
        "dock_item_name": {
            "required": True,
            "description": "Name of Dock Item",
            "default": "",
        },
        "dock_item_type": {
            "required": True,
            "description": "Type of Dock Item - either 'App', 'File' or 'Folder'",
            "default": "App",
        },
        "dock_item_path": {
            "required": True,
            "description": "Path of Dock Item - e.g. 'file:///Applications/Safari.app/'",
            "default": "",
        },
        "replace_dock_item": {
            "required": False,
            "description": "Overwrite an existing dock item if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "dock_item": {"description": "The created/updated dock item."},
        "jamfdockitemuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfDockItemUploader()
    PROCESSOR.execute_shell()
