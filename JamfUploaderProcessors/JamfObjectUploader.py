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

NOTES:
The API endpoint must be defined in the api_endpoints function in JamfUploaderBase.py

All functions are in JamfUploaderLib/JamfObjectUploaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfObjectUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfObjectUploaderBase,
)

__all__ = ["JamfObjectUploader"]


class JamfObjectUploader(JamfObjectUploaderBase):
    """Processor to upload an API object not covered by the other specific
    JamfUploader processors
    """

    description = (
        "A processor for AutoPkg that will create or update an API object template "
        "on a Jamf Pro server."
        "'Jamf Pro privileges are required by the API_USERNAME user for whatever the endpoint is."
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
            "required": False,
            "description": "Name of the object. Required except for settings-related objects.",
        },
        "object_id": {
            "required": False,
            "description": "ID of an object. May be used instead of supplying an object name.",
            "default": "",
        },
        "object_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "object_type": {
            "required": True,
            "description": "Type of the object. This is the name of the key in the XML template",
            "default": "",
        },
        "elements_to_remove": {
            "required": False,
            "description": (
                "A list of XML or JSON elements that should be removed from the downloaded XML. "
                "Note that id and self_service_icon are removed automatically."
            ),
        },
        "element_to_replace": {
            "required": False,
            "description": (
                "Full path of an element to replace the value of, "
                "such as general/id. "
            ),
        },
        "replacement_value": {
            "required": False,
            "description": (
                "The value of the element provided by the element_to_replace key. "
            ),
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
        "jamfobjectuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "object_name": {
            "description": "Jamf object name of the newly created or modified object.",
        },
        "object_updated": {"description": "Boolean - True if the object was changed."},
        "failover_url": {
            "description": "Failover URL, if uploading failover_generate_command object.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfObjectUploader()
    PROCESSOR.execute_shell()
