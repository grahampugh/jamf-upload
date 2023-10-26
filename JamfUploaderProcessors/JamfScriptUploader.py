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
All functions are in JamfUploaderLib/JamfScriptUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfScriptUploaderBase import JamfScriptUploaderBase  # noqa: E402

__all__ = ["JamfScriptUploader"]


class JamfScriptUploader(JamfScriptUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a script to a Jamf Cloud or "
        "on-prem server."
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
        "script_path": {
            "required": False,
            "description": "Full path to the script to be uploaded",
        },
        "script_name": {
            "required": False,
            "description": "Name of the script in Jamf",
        },
        "script_category": {
            "required": False,
            "description": "Script category",
            "default": "",
        },
        "script_priority": {
            "required": False,
            "description": "Script priority (BEFORE or AFTER)",
            "default": "AFTER",
        },
        "osrequirements": {
            "required": False,
            "description": "Script OS requirements",
            "default": "",
        },
        "script_info": {
            "required": False,
            "description": "Script info field",
            "default": "",
        },
        "script_notes": {
            "required": False,
            "description": "Script notes field",
            "default": "",
        },
        "script_parameter4": {
            "required": False,
            "description": "Script parameter 4 title",
            "default": "",
        },
        "script_parameter5": {
            "required": False,
            "description": "Script parameter 5 title",
            "default": "",
        },
        "script_parameter6": {
            "required": False,
            "description": "Script parameter 6 title",
            "default": "",
        },
        "script_parameter7": {
            "required": False,
            "description": "Script parameter 7 title",
            "default": "",
        },
        "script_parameter8": {
            "required": False,
            "description": "Script parameter 8 title",
            "default": "",
        },
        "script_parameter9": {
            "required": False,
            "description": "Script parameter 9 title",
            "default": "",
        },
        "script_parameter10": {
            "required": False,
            "description": "Script parameter 10 title",
            "default": "",
        },
        "script_parameter11": {
            "required": False,
            "description": "Script parameter 11 title",
            "default": "",
        },
        "skip_script_key_substitution": {
            "required": False,
            "description": "Skip key substitution in processing the script",
            "default": False,
        },
        "replace_script": {
            "required": False,
            "description": "Overwrite an existing script if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "script_name": {
            "required": False,
            "description": "Name of the uploaded script",
        },
        "jamfscriptuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfScriptUploader()
    PROCESSOR.execute_shell()
