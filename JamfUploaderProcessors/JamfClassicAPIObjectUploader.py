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

DEPRECATION NOTICE:
This processor has been superceded by the functionally equivalent
JamfObjectUploader processor, and will be removed at a future date.
Please update any recipes or sscripts to use JamfObjectUploader.
The input and output variables are unachanged.

NOTES:
The API endpoint must be defined in the api_endpoints function in JamfUploaderBase.py

All functions are in JamfUploaderLib/JamfClassicAPIObjectUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfClassicAPIObjectUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfClassicAPIObjectUploaderBase,
)

__all__ = ["JamfClassicAPIObjectUploader"]


class JamfClassicAPIObjectUploader(JamfClassicAPIObjectUploaderBase):
    description = "THIS PROCESSOR IS DEPRECATED. Please use JamfObjectUploader instead."

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
        "object_name": {
            "required": True,
            "description": "Name of the object",
            "default": "",
        },
        "object_template": {
            "required": True,
            "description": "Full path to the XML template",
        },
        "object_type": {
            "required": True,
            "description": "Type of the object. This is the name of the key in the XML template",
            "default": "",
        },
        "replace_object": {
            "required": False,
            "description": "Overwrite an existing object if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfclassicapiobjectuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "object_name": {
            "description": "Jamf object name of the newly created or modified object.",
        },
        "object_updated": {"description": "Boolean - True if the object was changed."},
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfClassicAPIObjectUploader()
    PROCESSOR.execute_shell()
