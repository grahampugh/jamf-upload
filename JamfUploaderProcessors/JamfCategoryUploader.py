#!/usr/local/autopkg/python

"""
JamfCategoryUploader processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh

Note that all functions are in JamfUploaderLib/JamfAccountUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfCategoryUploaderBase import (  # noqa: E402
    JamfCategoryUploaderBase,
)

__all__ = ["JamfCategoryUploader"]


class JamfCategoryUploader(JamfCategoryUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a category to a Jamf Cloud "
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
        "category_name": {"required": False, "description": "Category", "default": ""},
        "category_priority": {
            "required": False,
            "description": "Category priority",
            "default": "10",
        },
        "replace_category": {
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
        "category": {"description": "The created/updated category."},
        "jamfcategoryuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfCategoryUploader()
    PROCESSOR.execute_shell()
