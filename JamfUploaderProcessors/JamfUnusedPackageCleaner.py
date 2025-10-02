#!/usr/local/autopkg/python

"""
Copyright 2023 Graham Pugh, Henrik Engström

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
This processor was written by Henrik Engström based on other JamfUploader processors
All functions are in JamfUploaderLib/JamfUnusedPackageCleanerBase.py
"""

import os.path
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUnusedPackageCleanerBase import (  # noqa: E402
    JamfUnusedPackageCleanerBase,
)

__all__ = ["JamfUnusedPackageCleaner"]


class JamfUnusedPackageCleaner(JamfUnusedPackageCleanerBase):
    description = (
        "A processor for AutoPkg that will remove packages from Jamf Pro, "
        "but keep X number of a packages matching a string"
    )

    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access to.",
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
        "dry_run": {
            "required": False,
            "description": "If set to True, nothing is deleted from Jamf Pro. "
            "Use together with '-vv' for detailed information. "
            "This is used for testing",
            "default": False,
        },
        "output_dir": {
            "required": False,
            "description": "Output directory to dump the csv file.",
            "default": "",
        },
        "slack_webhook_url": {"required": False, "description": ("Slack webhook.")},
    }

    output_variables = {
        "jamfunusedpackagecleaner_summary_result": {
            "description": "Description of interesting results.",
        }
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfUnusedPackageCleaner()
    PROCESSOR.execute_shell()
