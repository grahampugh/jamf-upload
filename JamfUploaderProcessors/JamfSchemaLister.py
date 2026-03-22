#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2026 Graham Pugh

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
All functions are in JamfUploaderLib/JamfSchemaListerBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfSchemaListerBase import (  # pylint: disable=import-error, wrong-import-position
    JamfSchemaListerBase,
)

__all__ = ["JamfSchemaLister"]


class JamfSchemaLister(JamfSchemaListerBase):
    """Processor to list all discoverable API endpoints from Jamf Pro schemas"""

    description = """
        A processor for AutoPkg that will list all discoverable API endpoints
        from the Jamf Pro Classic API and JPAPI schemas.
    """

    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": (
                "URL to a Jamf Pro server, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "API_USERNAME": {
            "required": False,
            "description": (
                "Username of account with appropriate access to "
                "jss, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "API_PASSWORD": {
            "required": False,
            "description": (
                "Password of api user, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "CLIENT_ID": {
            "required": False,
            "description": (
                "Client ID with access to "
                "jss, optionally set as a key in the com.github.autopkg "
                "preference file."
            ),
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": (
                "Secret associated with the Client ID, optionally set as a key in "
                "the com.github.autopkg preference file."
            ),
        },
        "api_filter": {
            "required": False,
            "description": (
                "Filter endpoints by API type. "
                "One of 'all', 'classic', or 'jpapi'. Default: 'all'."
            ),
            "default": "all",
        },
        "show_deprecated": {
            "required": False,
            "description": ("Show deprecated endpoints in the output. Default: False."),
            "default": "False",
        },
        "output_dir": {
            "required": False,
            "description": (
                "Optional directory to write the schema listing to a file. "
                "Directory must exist."
            ),
        },
    }

    output_variables = {
        "jamfschemalister_summary_result": {
            "description": "Description of interesting results.",
        },
        "schema_lister_output": {
            "description": "Text listing of all discovered endpoints.",
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfSchemaLister()
    PROCESSOR.execute_shell()
