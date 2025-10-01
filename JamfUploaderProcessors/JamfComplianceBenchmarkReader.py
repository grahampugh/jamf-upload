#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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
The API endpoint must be defined in the api_endpoints function in JamfUploaderBase.py

All functions are in JamfUploaderLib/JamfObjectReaderBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfComplianceBenchmarkReader import (  # pylint: disable=import-error, wrong-import-position
    JamfComplianceBenchmarkReader,
)

__all__ = ["JamfObjectReader"]


class JamfObjectReader(JamfComplianceBenchmarkReader):
    """Processor to read an API object"""

    description = """
        A processor for AutoPkg that will read a Jamf Platform Compliance Benchmark API object on a Jamf Pro server.
        Platform API credentials are required.
    """

    input_variables = {
        "PLATFORM_URL": {
            "required": True,
            "description": (
                "URL to a Jamf Pro server that the API user has write access "
                "to, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "PLATFORM_CLIENT_ID": {
            "required": False,
            "description": (
                "Client ID with access to "
                "jss, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "PLATFORM_CLIENT_SECRET": {
            "required": False,
            "description": (
                "Secret associated with the Client ID, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "object_id": {
            "required": False,
            "description": "ID of an object. May be used instead of supplying an object name.",
            "default": "",
        },
        "object_name": {
            "required": False,
            "description": "Name of the object. Required unless using 'all_objects'",
            "default": "",
        },
        "object_type": {
            "required": True,
            "description": "Type of the object. See documentation for valid types.",
            "default": "",
        },
        "output_dir": {
            "required": False,
            "description": "Output directory to dump the xml or json file",
            "default": "",
        },
        "elements_to_remove": {
            "required": False,
            "description": (
                "A list of JSON elements that should be removed from the downloaded JSON. "
            ),
        },
        "all_objects": {
            "required": False,
            "description": "Download all objects of the specific object type",
            "default": "False",
        },
        "list_only": {
            "required": False,
            "description": "Only output a variable with a list of all objects - ID and name",
            "default": "False",
        },
    }

    output_variables = {
        "jamfcompliancebenchmarkreader_summary_result": {
            "description": "Description of interesting results.",
        },
        "object_name": {
            "description": "Jamf object name of the object.",
        },
        "object_list": {
            "description": "A list of all objects.",
        },
        "object_id": {
            "description": "Jamf object ID of the object.",
        },
        "raw_object": {
            "description": "String containing the complete raw downloaded XML",
        },
        "parsed_object": {
            "description": "String containing parsed XML (removes IDs and computers)",
        },
        "output_dir": {
            "description": "Path of dumped xml",
        },
        "file_path": {
            "description": "Path of outputted results",
        },
        "payload_path": {
            "description": "Path of outputted payload",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfComplianceBenchmarkReader()
    PROCESSOR.execute_shell()
