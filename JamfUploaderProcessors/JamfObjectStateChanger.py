#!/usr/local/autopkg/python

"""
Copyright 2025 Graham Pugh

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
All functions are in JamfUploaderLib/JamfObjectStateChangerBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfObjectStateChangerBase import (  # pylint: disable=import-error, wrong-import-position
    JamfObjectStateChangerBase,
)

__all__ = ["JamfObjectStateChanger"]


class JamfObjectStateChanger(JamfObjectStateChangerBase):
    description = (
        "A processor for AutoPkg that will change the state of an object on a Jamf "
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
        "object_name": {
            "required": True,
            "description": "Name of the object. Required.",
            "default": "",
        },
        "object_type": {
            "required": True,
            "description": {
                "The API object type. This is in the singular form - for "
                "Classic API endpoints this is the name of the key in the XML template. For "
                "JSON objects it is a construction made interally for this project. See the "
                "[Object Reference](./Object%20Reference.md) for valid objects. Valid values "
                "are `policy`, `computer_extension_attribute`, `app_installers_deployment`"
                "Note that only script-based extension attributes may be enabled or disabled."
            },
            "default": "policy",
        },
        "object_state": {
            "required": True,
            "description": "The desired state of the object, either 'enable' or 'disable'",
            "default": "disable",
        },
        "retain_data": {
            "required": False,
            "description": "When disabling a computer extension attribute, "
            "set to true to retain existing data. "
            "Ignored for other object types.",
            "default": True,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
        "max_tries": {
            "required": False,
            "description": (
                "Maximum number of attempts to upload the account. "
                "Must be an integer between 1 and 10."
            ),
            "default": "5",
        },
    }

    output_variables = {
        "jamfobjectstatechanger_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfObjectStateChanger()
    PROCESSOR.execute_shell()
