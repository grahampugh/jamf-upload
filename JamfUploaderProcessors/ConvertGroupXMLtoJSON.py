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
This processor converts Classic API XML group definitions to Jamf Pro API JSON format.
It handles both smart and static groups.
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Any

from autopkglib import Processor, ProcessorError  # pylint: disable=import-error

__all__ = ["ConvertGroupXMLtoJSON"]


class ConvertGroupXMLtoJSON(Processor):
    """Converts Classic API XML group definitions to Jamf Pro API JSON format."""

    description = __doc__
    input_variables = {
        "group_xml_path": {
            "required": True,
            "description": "Path to the XML file containing the Classic API group definition.",
        },
        "group_json_path": {
            "required": False,
            "description": (
                "Path where the converted JSON file should be written. "
                "If not provided, the JSON will be output to the AutoPkg environment."
            ),
        },
    }

    output_variables = {
        "group_json_data": {
            "description": "Dictionary containing the converted group data in Jamf Pro API format."
        },
        "is_smart_group": {
            "description": "Boolean indicating whether this is a smart group (True) or static group (False)."
        },
        "group_name": {"description": "Name of the group from the XML definition."},
    }

    def parse_criterion(self, criterion_elem: ET.Element) -> Dict[str, Any]:
        """
        Parse a single criterion from Classic API XML format.

        Returns a dictionary representing the criterion for Jamf Pro API.
        """
        name = criterion_elem.find("name")
        priority = criterion_elem.find("priority")
        and_or = criterion_elem.find("and_or")
        search_type = criterion_elem.find("search_type")
        value = criterion_elem.find("value")
        opening_paren = criterion_elem.find("opening_paren")
        closing_paren = criterion_elem.find("closing_paren")

        criterion = {
            "name": name.text if name is not None and name.text else "",
            "priority": (
                int(priority.text) if priority is not None and priority.text else 0
            ),
            "andOr": (
                and_or.text.lower() if and_or is not None and and_or.text else "and"
            ),
            "searchType": (
                search_type.text.lower()
                if search_type is not None and search_type.text
                else ""
            ),
            "value": value.text if value is not None and value.text else "",
        }

        # Add parentheses if present (for complex logic)
        if opening_paren is not None and opening_paren.text == "true":
            criterion["openingParen"] = True
        if closing_paren is not None and closing_paren.text == "true":
            criterion["closingParen"] = True

        return criterion

    def convert_xml_to_json(self, xml_content: str) -> tuple[Dict[str, Any], bool, str]:
        """
        Convert Classic API XML group definition to Jamf Pro API JSON format.

        Args:
            xml_content: String containing the XML content

        Returns:
            Tuple of (json_data, is_smart_group, group_name)
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ProcessorError(f"Invalid XML content: {e}") from e

        # Extract basic group information
        name = root.find("name")
        is_smart = root.find("is_smart")
        site = root.find("site")
        criteria = root.find("criteria")

        # Get the group name
        group_name = name.text if name is not None and name.text else ""

        # Determine if this is a smart group based on presence of criteria
        is_smart_group = (
            is_smart.text.lower() == "true"
            if is_smart is not None and is_smart.text
            else False
        )

        # Build the Jamf Pro API JSON structure
        json_data = {
            "name": group_name,
            "description": "This JSON was auto-converted from Classic API XML format",
        }

        # Add site information if present
        if site is not None:
            site_id = site.find("id")
            if site_id is not None and site_id.text and site_id.text != "-1":
                json_data["siteId"] = site_id.text

        # Parse criteria for smart groups
        if is_smart_group and criteria is not None:
            criterion_list = []
            for criterion_elem in criteria.findall("criterion"):
                criterion_list.append(self.parse_criterion(criterion_elem))

            if criterion_list:
                json_data["criteria"] = criterion_list

        return json_data, is_smart_group, group_name

    def main(self):
        """Main processor execution."""
        group_xml_path = self.env.get("group_xml_path")
        group_json_path = self.env.get("group_json_path")

        if not group_xml_path:
            raise ProcessorError("group_xml_path is required")

        # Read the XML file
        try:
            with open(group_xml_path, "r", encoding="utf-8") as f:
                xml_content = f.read()
        except FileNotFoundError as exc:
            raise ProcessorError(f"XML file not found: {group_xml_path}") from exc
        except (IOError, OSError) as e:
            raise ProcessorError(f"Error reading XML file: {e}") from e

        # Convert to JSON
        try:
            json_data, is_smart_group, group_name = self.convert_xml_to_json(
                xml_content
            )
        except ProcessorError:
            raise
        except Exception as e:
            raise ProcessorError(f"Error converting XML to JSON: {e}") from e

        # Set output variables
        self.env["group_json_data"] = json_data
        self.env["is_smart_group"] = is_smart_group
        self.env["group_name"] = group_name

        # Write to file if path provided
        if group_json_path:
            try:
                json_output = json.dumps(json_data, indent=2, ensure_ascii=False)
                with open(group_json_path, "w", encoding="utf-8") as f:
                    f.write(json_output)
                self.output(f"Conversion complete! JSON written to: {group_json_path}")
            except (IOError, OSError) as e:
                raise ProcessorError(f"Error writing JSON file: {e}") from e
        else:
            self.output("Conversion complete! JSON data available in group_json_data")

        # Output important notes
        self.output("")
        self.output("IMPORTANT NOTES:")
        if is_smart_group:
            self.output("- This is a smart group")
            self.output(
                "- Use endpoint: /api/v2/computer-groups/smart-groups for computer groups"
            )
            self.output(
                "- Use endpoint: /api/v1/mobile-device-groups/smart-groups for mobile device groups"
            )
        else:
            self.output("- This is a static group")
            self.output(
                "- Use endpoint: /api/v2/computer-groups/static-groups for computer groups"
            )
            self.output(
                "- Use endpoint: /api/v1/mobile-device-groups/static-groups for mobile device groups"
            )
        self.output("- Test the group criteria logic in a non-production environment")
        self.output(
            "- Verify the conversion by comparing with the original group in Jamf Pro"
        )


if __name__ == "__main__":
    PROCESSOR = ConvertGroupXMLtoJSON()
    PROCESSOR.execute_shell()
