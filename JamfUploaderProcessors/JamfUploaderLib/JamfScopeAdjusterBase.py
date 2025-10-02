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
import os
import sys

from urllib.parse import urlparse
from xml.dom.minidom import parseString

from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfScopeAdjusterBase(JamfUploaderBase):
    """Class for functions used to adjust scope of a Jamf API object"""

    def generate_filename_from_raw_xml(self, object_type, raw_object):
        """
        Generates a filename from the given raw XML object.
        """
        ext = ".xml"
        object_instance = urlparse(self.env.get("JSS_URL")).hostname.split(".")[0]
        object_name = ET.fromstring(raw_object).find("./general/name").text
        object_id = ET.fromstring(raw_object).find("./general/id").text
        return f"{object_instance}_{object_type}_{object_id}_{object_name}{ext}"

    def clean_raw_xml(self, raw_object):
        """
        Cleans the provided raw XML object by removing unnecessary elements.

        This function parses the given raw XML string, retains only the
        'scope' section in the root. All other elements are removed.
        """
        root = ET.fromstring(raw_object)

        for child in list(root):
            if child.tag not in "scope":
                root.remove(child)

        return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode()

    def add_scope_element(
        self,
        raw_object,
        object_type,
        scoping_type,
        scopeable_type,
        scopeable_name,
        strict_mode,
    ):
        """
        Add an XML tag to the given raw XML object based on the specified parameters.
        """
        root = ET.fromstring(raw_object)

        scope = root.find("./scope")
        if scope is None:
            scope = ET.SubElement(root, "scope")

        if (
            scopeable_type == "user_group"
            and scoping_type == "limitation"
            and object_type == "policy"
        ):
            parent_xpath = "./scope/limit_to_users/user_groups"
            parent = root.find(parent_xpath)

            if parent is None:
                limit_to_users = scope.find("limit_to_users")
                if limit_to_users is None:
                    limit_to_users = ET.SubElement(scope, "limit_to_users")

                if limit_to_users.find("user_groups") is None:
                    ET.SubElement(limit_to_users, "user_groups")

                parent = root.find(parent_xpath)

            for child in parent.findall(scopeable_type):
                if child.text == scopeable_name and not strict_mode:
                    self.output(
                        f"WARNING: {scoping_type}: {scopeable_type} with name "
                        f"'{scopeable_name}' already exists, raw object unchanged."
                    )
                    return ET.tostring(
                        root, encoding="UTF-8", xml_declaration=True
                    ).decode()
                if child.text == scopeable_name:
                    raise ProcessorError(
                        f"{scoping_type}: {scopeable_type} with name "
                        f"'{scopeable_name}' already exists."
                    )

            new_tag = ET.Element(scopeable_type)
            new_tag.text = scopeable_name
            parent.append(new_tag)

        else:
            if scoping_type == "target" and scopeable_type in (
                "computer_group",
                "mobile_device_group",
                "building",
                "department",
            ):
                parent_xpath = f"./scope/{scopeable_type}s"
                if scope.find(f"{scopeable_type}s") is None:
                    ET.SubElement(scope, f"{scopeable_type}s")

            elif (
                (
                    object_type != "restricted_software"
                    and scoping_type == "limitation"
                    and scopeable_type
                    in ("network_segment", "user_group", "computer_group")
                )
                or (
                    object_type == "restricted_software"
                    and scoping_type == "exclusion"
                    and scopeable_type in ("computer_group", "building", "department")
                )
                or (
                    object_type != "restricted_software"
                    and scoping_type == "exclusion"
                    and scopeable_type
                    in (
                        "computer_group",
                        "mobile_device_group",
                        "user_group",
                        "network_segment",
                        "building",
                        "department",
                    )
                )
            ):
                parent_xpath = f"./scope/{scoping_type}s/{scopeable_type}s"
                scoping_types = scope.find(f"{scoping_type}s")
                if scoping_types is None:
                    scoping_types = ET.SubElement(scope, f"{scoping_type}s")

                if scoping_types.find(f"{scopeable_type}s") is None:
                    ET.SubElement(scoping_types, f"{scopeable_type}s")

            else:
                raise ProcessorError(
                    "Unsupported scope: "
                    f"Object type: {object_type} , Scoping type: "
                    f"{scoping_type} , Scopeable type: {scopeable_type} , "
                )

            parent = root.find(parent_xpath)

            for child in parent.findall(scopeable_type):
                name_tag = child.find("name")
                if (
                    name_tag is not None
                    and name_tag.text == scopeable_name
                    and not strict_mode
                ):
                    self.output(
                        f"WARNING: {scoping_type}: {scopeable_type} with name "
                        f"'{scopeable_name}' already exists, raw object unchanged."
                    )
                    return ET.tostring(
                        root, encoding="UTF-8", xml_declaration=True
                    ).decode()
                if name_tag is not None and name_tag.text == scopeable_name:
                    raise ProcessorError(
                        f"{scoping_type}: {scopeable_type} with name "
                        f"'{scopeable_name}' already exists."
                    )

            new_group = ET.Element(scopeable_type)
            name_tag = ET.SubElement(new_group, "name")
            name_tag.text = scopeable_name
            parent.append(new_group)

        self.output(
            f"Added {scoping_type}: {scopeable_type} with name '{scopeable_name}'."
        )
        return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode()

    def remove_scope_element(
        self,
        raw_object,
        object_type,
        scoping_type,
        scopeable_type,
        scopeable_name,
        strict_mode,
    ):
        """
        Remove a specific XML tag from a given raw XML object based on the provided
        scoping and scopeable types.
        """
        root = ET.fromstring(raw_object)
        removed = False

        if (
            scopeable_type == "user_group"
            and scoping_type == "limitation"
            and object_type == "policy"
        ):
            parent_xpath = "./scope/limit_to_users/user_groups"
            parent = root.find(parent_xpath)

            if parent is None and not strict_mode:
                self.output(
                    f"WARNING: Parent element not found for XPath: {parent_xpath}"
                )
            elif parent is None:
                raise ProcessorError(
                    f"Parent element not found for XPath: {parent_xpath}"
                )

            for child in list(parent):
                if child.tag == scopeable_type and child.text == scopeable_name:
                    parent.remove(child)
                    removed = True

        if scoping_type == "target":
            parent_xpath = f"./scope/{scopeable_type}s"
        elif scoping_type == "limitation" or scoping_type == "exclusion":
            parent_xpath = f"./scope/{scoping_type}s/{scopeable_type}s"
        else:
            raise ProcessorError(f"Incorrect scoping_type '{scoping_type}' specified.")

        parent = root.find(parent_xpath)

        if parent is None and not strict_mode:
            self.output(f"WARNING: Parent element not found for XPath: {parent_xpath}")
        elif parent is None:
            raise ProcessorError(f"Parent element not found for XPath: {parent_xpath}")

        for child in list(parent):
            if any(
                subchild.tag == "name" and subchild.text == scopeable_name
                for subchild in list(child)
            ):
                parent.remove(child)
                removed = True

        if removed:
            self.output(
                f"Removed {scoping_type}: {scopeable_type} with name '{scopeable_name}'."
            )
        else:
            if not strict_mode:
                self.output(
                    f"WARNING: {scoping_type}: {scopeable_type} with name "
                    f"'{scopeable_name}' not found, raw object unchanged."
                )
            else:
                raise ProcessorError(
                    f"{scoping_type}: {scopeable_type} with name '{scopeable_name}' not found."
                )

        return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode()

    def execute(self):  # pylint: disable=too-many-branches
        """Main function for adjusting the scope of an object"""
        raw_object = self.env.get("raw_object")
        object_template = self.env.get("object_template")
        output_dir = self.env.get("output_dir") or self.env.get("RECIPE_CACHE_DIR")
        scoping_operation = self.env.get("scoping_operation")
        scopeable_type = self.env.get("scopeable_type")
        scoping_type = self.env.get("scoping_type")
        scopeable_name = self.env.get("scopeable_name")
        strict_mode = self.to_bool(self.env.get("strict_mode"))
        strip_raw_xml = self.to_bool(self.env.get("strip_raw_xml"))

        if object_template:
            if not object_template.startswith("/"):
                found_template = self.get_path_to_file(object_template)
                if found_template:
                    object_template = found_template
                else:
                    raise ProcessorError(f"File {object_template} not found")
            try:
                with open(object_template, "r", encoding="UTF-8") as file:
                    raw_object = file.read().strip()
                    self.output(f"Read XML from template file: {object_template}")
            except Exception as e:
                raise ProcessorError(f"Error reading template file: {e}") from e

        if not strict_mode:
            self.output("WARNING: Strict mode disabled!")

        if raw_object.strip().startswith("<"):
            object_type = ET.fromstring(raw_object).tag

            if object_template:
                filename = os.path.basename(object_template)
            else:
                filename = self.generate_filename_from_raw_xml(object_type, raw_object)
            object_template = os.path.join(output_dir, filename)
            if strip_raw_xml:
                raw_object = self.clean_raw_xml(raw_object)
            if scoping_operation == "add":
                raw_object = self.add_scope_element(
                    raw_object,
                    object_type,
                    scoping_type,
                    scopeable_type,
                    scopeable_name,
                    strict_mode,
                )
            elif scoping_operation == "remove":
                raw_object = self.remove_scope_element(
                    raw_object,
                    object_type,
                    scoping_type,
                    scopeable_type,
                    scopeable_name,
                    strict_mode,
                )
        else:
            raise ProcessorError("Unsupported data format. Use XML.")

        raw_object = parseString(raw_object).toprettyxml(indent="  ")
        raw_object = "\n".join(
            [line for line in raw_object.split("\n") if line.strip()]
        )
        with open(object_template, "w", encoding="UTF-8") as file:
            file.write(raw_object)
            self.output(f"Wrote processed XML to file: {object_template}")

        self.env["object_template"] = object_template
        self.env["raw_object"] = raw_object
