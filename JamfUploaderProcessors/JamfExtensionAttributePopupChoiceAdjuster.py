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
All functions are in JamfUploaderLib/JamfExtensionAttributePopupChoiceAdjusterBase.py
"""

import os
import sys

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfExtensionAttributePopupChoiceAdjusterBase import (  # pylint: disable=import-error, wrong-import-position
    JamfExtensionAttributePopupChoiceAdjusterBase,
)

__all__ = ["JamfExtensionAttributePopupChoiceAdjuster"]


class JamfExtensionAttributePopupChoiceAdjuster(
    JamfExtensionAttributePopupChoiceAdjusterBase
):
    """AutoPkg processor that adds or removes pop-up choices from a Jamf Extension Attribute."""

    description = "AutoPkg processor that adds or removes pop-up choices from a Jamf Extension Attribute."

    input_variables = {
        "object_template": {
            "required": False,
            "description": "Full path of the object file to modify.",
        },
        "parsed_object": {
            "required": False,
            "description": (
                "XML or JSON parsed object string to modify. Used if object_template "
                "is not supplied, e.g. if taking input from JamfObjectReader."
            ),
        },
        "choice_operation": {
            "required": True,
            "description": "Specify 'add' to add a choice or 'remove' to remove a choice.",
        },
        "choice_value": {
            "required": True,
            "description": "Pop-up choice value to add or remove.",
        },
        "strict_mode": {
            "required": False,
            "description": (
                "Raise a ProcessorError when adding a choice that already exists "
                "or removing a choice that does not exist in the parsed object. If set to False, "
                "continue without changing the parsed object. Whilst this is safe and will not write "
                "unintended changes to the Jamf API, errors/oversights in specifying choice names "
                "may go unnoticed."
            ),
            "default": "True",
        },
        "output_dir": {
            "required": False,
            "description": (
                "Directory to save the modified XML or JSON file. Defaults to RECIPE_CACHE_DIR."
            ),
        },
    }

    output_variables = {
        "object_template": {
            "description": (
                "Full path of the modified object file. Intended to pass to JamfObjectUploader."
            )
        },
        "parsed_object": {
            "description": (
                "Parsed processed object string. For chaining additional "
                "JamfExtensionAttributePopupChoiceAdjuster processors."
            )
        },
    }

    def main(self):
        """Run the execute function"""
        self.execute()


if __name__ == "__main__":
    PROCESSOR = JamfExtensionAttributePopupChoiceAdjuster()
    PROCESSOR.execute_shell()
