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
"""

import xml.etree.ElementTree as ET
import json
import os
import sys

from urllib.parse import urlparse

from autopkglib import (  # pylint: disable=import-error
    ProcessorError,
)

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfExtensionAttributePopupChoiceAdjusterBase(JamfUploaderBase):
    """Class for functions used to adjust an Extension Attribute Pop-up Choice"""

    def generate_filename_from_object(self, is_json, parsed_object):
        """
        Generate a filename based on the object instance and name.

        Args:
            is_json (bool): Flag indicating if the object is in JSON format.
            parsed_object (str): The parsed object string.

        Returns:
            str: The generated filename.
        """
        object_instance = urlparse(self.env.get("JSS_URL")).hostname.split(".")[0]
        if is_json:
            ext = ".json"
            object_name = json.loads(parsed_object)["name"]
        else:
            ext = ".xml"
            object_name = ET.fromstring(parsed_object).find("./name").text

        return f"{object_instance}_{object_name}{ext}"

    def validate_ea_type(self, is_json, parsed_object):
        """
        Validate the type of the extension attribute.

        Args:
            is_json (bool): Flag indicating if the object is in JSON format.
            parsed_object (str): The parsed object string.

        Raises:
            ProcessorError: If the extension attribute type is invalid.
        """
        if is_json:
            data = json.loads(parsed_object)

            if data.get("inputType") != "POPUP":
                raise ProcessorError(
                    "Invalid Extension Attribute inputType, must be POPUP."
                )
        else:
            root = ET.fromstring(parsed_object)

            if root.find(".//input_type/type").text != "Pop-up Menu":
                raise ProcessorError(
                    "Invalid Extension Attribute input_type, must be Pop-up Menu."
                )

    def add_xml_tag(
        self, parsed_object, parent_xpath, element, choice_value, strict_mode
    ):  # pylint: disable=too-many-arguments
        """
        Add an XML tag to the parsed object.

        Args:
            parsed_object (str): The parsed object string.
            parent_xpath (str): The XPath of the parent element.
            element (str): The name of the element to add.
            choice_value (str): The value of the choice to add.
            strict_mode (str): Flag indicating if strict mode is enabled.

        Returns:
            str: The modified parsed object string.

        Raises:
            ProcessorError: If the parent element is not found or the element already exists.
        """
        root = ET.fromstring(parsed_object)
        parent = root.find(parent_xpath)

        if parent is None:
            raise ProcessorError(f"Parent element not found for XPath: {parent_xpath}")

        for child in parent.findall(element):
            if child.text == choice_value and strict_mode == "False":
                self.output(
                    f"WARNING: Element <{element}> with choice_value '{choice_value}' already exists "
                    f"in {parent_xpath}, parsed object unchanged."
                )
                return ET.tostring(
                    root, encoding="UTF-8", xml_declaration=True
                ).decode()
            if child.text == choice_value:
                raise ProcessorError(
                    f"Element <{element}> with choice_value '{choice_value}' already exists in "
                    f"{parent_xpath}"
                )

        new_tag = ET.Element(element)
        new_tag.text = choice_value
        parent.append(new_tag)

        self.output(
            f"Added element <{element}> and choice_value '{choice_value}' to {parent_xpath}"
        )
        return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode()

    def remove_xml_tag(self, parsed_object, element, choice_value, strict_mode):
        """
        Remove an XML tag from the parsed object.

        Args:
            parsed_object (str): The parsed object string.
            element (str): The name of the element to remove.
            choice_value (str): The value of the choice to remove.
            strict_mode (str): Flag indicating if strict mode is enabled.

        Returns:
            str: The modified parsed object string.

        Raises:
            ProcessorError: If the element is not found and strict mode is enabled.
        """
        root = ET.fromstring(parsed_object)
        removed = False

        for parent in list(root.iter()):
            for child in list(parent):
                if child.tag == element and child.text == choice_value:
                    parent.remove(child)
                    removed = True

        if removed:
            self.output(
                f"Removed all instances of <{element}> containing '{choice_value}' from XML."
            )
        elif strict_mode == "False":
            self.output(
                f"WARNING: Element <{element}> with choice_value '{choice_value}' not found, "
                "parsed object unchanged."
            )
        else:
            raise ProcessorError(
                f"Element <{element}> with choice_value '{choice_value}' not found."
            )

        return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode()

    def add_json_key(self, parsed_object, element, choice_value, strict_mode):
        """
        Add a key to the JSON object.

        Args:
            parsed_object (str): The parsed object string.
            element (str): The name of the element to add.
            choice_value (str): The value of the choice to add.
            strict_mode (str): Flag indicating if strict mode is enabled.

        Returns:
            str: The modified parsed object string.

        Raises:
            ProcessorError: If the element already exists and strict mode is enabled.
        """
        data = json.loads(parsed_object)

        if element in data:
            if isinstance(data[element], list):
                if choice_value in data[element] and strict_mode == "False":
                    self.output(
                        f"WARNING: choice_value '{choice_value}' already exists in array '{element}', "
                        f"parsed object unchanged."
                    )
                    return json.dumps(data, indent=4)
                if choice_value in data[element]:
                    raise ProcessorError(
                        f"choice_value '{choice_value}' already exists in array '{element}'."
                    )
                data[element].append(choice_value)
            else:
                raise ProcessorError(f"Key '{element}' exists but is not an array.")
        else:
            data[element] = [choice_value]

        self.output(f"Added choice_value '{choice_value}' to key '{element}' in JSON.")

        return json.dumps(data, indent=4)

    def remove_json_key(self, parsed_object, element, choice_value, strict_mode):
        """
        Remove a key from the JSON object.

        Args:
            parsed_object (str): The parsed object string.
            element (str): The name of the element to remove.
            choice_value (str): The value of the choice to remove.
            strict_mode (str): Flag indicating if strict mode is enabled.

        Returns:
            str: The modified parsed object string.

        Raises:
            ProcessorError: If the element is not found and strict mode is enabled.
        """
        data = json.loads(parsed_object)

        if element in data:
            if isinstance(data[element], list):
                if choice_value in data[element]:
                    data[element].remove(choice_value)
                    if not data[element]:
                        del data[element]
                elif strict_mode == "False":
                    self.output(
                        f"WARNING: choice_value '{choice_value}' not found in array '{element}', "
                        f"parsed object unchanged."
                    )
                else:
                    raise ProcessorError(
                        f"choice_value '{choice_value}' not found in array '{element}'."
                    )
            elif data[element] == choice_value:
                del data[element]
            else:
                raise ProcessorError(
                    f"No matching key '{element}' with choice_value '{choice_value}' found in JSON."
                )
        else:
            raise ProcessorError(f"Key '{element}' not found in JSON.")

        return json.dumps(data, indent=4)

    def execute(self):
        """
        Execute the main logic for adjusting pop-up choices in a Jamf Extension Attribute.
        """
        choice_operation = self.env.get("choice_operation")
        parsed_object = self.env.get("parsed_object")
        object_template = self.env.get("object_template")
        output_dir = self.env.get("output_dir") or self.env.get("RECIPE_CACHE_DIR")
        choice_value = self.env.get("choice_value")
        strict_mode = self.to_bool(self.env.get("strict_mode"))

        if object_template:
            if not object_template.startswith("/"):
                found_template = self.get_path_to_file(object_template)
                if found_template:
                    object_template = found_template
                else:
                    raise ProcessorError(f"File {object_template} not found")
            try:
                with open(object_template, "r", encoding="UTF-8") as file:
                    parsed_object = file.read().strip()
                    self.output(f"Read parsed_object from file: {object_template}")
            except Exception as e:
                raise ProcessorError(f"Error reading object_template file: {e}") from e

        if not strict_mode:
            self.output("WARNING: Strict mode disabled!")

        is_json = parsed_object.strip().startswith(
            "{"
        ) or parsed_object.strip().startswith("[")
        self.validate_ea_type(is_json, parsed_object)

        if object_template:
            filename = os.path.basename(object_template)
        else:
            filename = self.generate_filename_from_object(is_json, parsed_object)

        object_template = os.path.join(output_dir, filename)

        if parsed_object.strip().startswith("<"):
            element = "choice"
            parent_xpath = "./input_type/popup_choices"
            if choice_operation == "add":
                parsed_object = self.add_xml_tag(
                    parsed_object, parent_xpath, element, choice_value, strict_mode
                )
            elif choice_operation == "remove":
                parsed_object = self.remove_xml_tag(
                    parsed_object, element, choice_value, strict_mode
                )
        elif is_json:
            element = "popupMenuChoices"
            if choice_operation == "add":
                parsed_object = self.add_json_key(
                    parsed_object, element, choice_value, strict_mode
                )
            elif choice_operation == "remove":
                parsed_object = self.remove_json_key(
                    parsed_object, element, choice_value, strict_mode
                )
        else:
            raise ProcessorError("Unsupported data format. Use XML or JSON.")

        with open(object_template, "w", encoding="utf-8") as file:
            file.write(parsed_object)

        self.env["object_template"] = object_template
        self.env["parsed_object"] = parsed_object
