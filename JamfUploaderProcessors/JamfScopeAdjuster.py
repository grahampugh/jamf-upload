#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
2025 Neil Martin

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

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfScopeAdjusterBase import (  # pylint: disable=import-error, wrong-import-position
    JamfScopeAdjusterBase,
)

__all__ = ["JamfScopeAdjuster"]


class JamfScopeAdjuster(JamfScopeAdjusterBase):
    """Processor to adjust the scope of a Jamf object"""

    description = (
        "AutoPkg processor that adds or removes a scopeable object as a target, "
        "limitation or exclusion to or from a Jamf API object."
    )

    input_variables = {
        "object_template": {
            "required": False,
            "description": "Full path of the object file to modify.",
        },
        "raw_object": {
            "required": False,
            "description": (
                "XML object string to modify. Used if object_template is not supplied, "
                "e.g. if taking input from JamfObjectReader."
            ),
        },
        "scoping_operation": {
            "required": True,
            "description": "Specify 'add' or 'remove'.",
        },
        "scoping_type": {
            "required": True,
            "description": "Type of scope. Specify 'target', 'limitation' or 'exclusion'.",
        },
        "scopeable_type": {
            "required": True,
            "description": (
                "Type of scopeable object. Specify 'user_group', 'computer_group' "
                "'mobile_device_group', 'network_segment', 'building', 'department'."
            ),
        },
        "scopeable_name": {
            "required": True,
            "description": "Name of scopeable object.",
        },
        "strict_mode": {
            "required": False,
            "description": (
                "Raise a ProcessorError when adding a scopable object that already exists "
                "or removing a scopable object that does not exist in the raw object. "
                "If set to False, continue without changing the raw object. "
                "Whilst this is safe and will not write unintended changes to the Jamf API, "
                "errors/oversights in specifying scopable object names may go unnoticed."
            ),
            "default": "True",
        },
        "strip_raw_xml": {
            "required": False,
            "description": (
                "Strip all XML tags except for scope. Set to True if input is from "
                "JamfObjectReader raw_object (default). Ensures only scope is written "
                "back to the Jamf API. Set to False if input is from object_template file."
            ),
            "default": "True",
        },
        "output_dir": {
            "required": False,
            "description": (
                "Directory to save the modified object file. Defaults to RECIPE_CACHE_DIR."
            ),
        },
    }

    output_variables = {
        "object_template": {
            "description": (
                "Full path of the modified object file. Intended to pass to "
                "JamfObjectUploader."
            )
        },
        "raw_object": {
            "description": (
                "Raw processed XML object string. For chaining additional "
                "JamfScopeAdjuster processors."
            )
        },
    }

    def main(self):
        """Run the execute function"""

        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfScopeAdjuster()
    PROCESSOR.execute_shell()
