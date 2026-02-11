#!/usr/bin/env python3
"""
Classic API XML to Jamf Pro API JSON Converter for Computer Groups
This script converts computer group definitions from Classic API XML format
to Jamf Pro API JSON format.

IMPORTANT SECURITY NOTICE:
- This script is provided as a starting point only and MUST be thoroughly tested before deployment
- The person requesting/deploying this script assumes full responsibility for validation and consequences
- Never deploy untested scripts to production environments or customer devices
- All scripts should be reviewed for security implications and potential unintended consequences
- Consider edge cases and error handling for different OS versions and configurations

Usage:
    python3 convert_computer_group.py input.xml output.json
    or
    python3 convert_computer_group.py input.xml  (prints to stdout)
"""

import xml.etree.ElementTree as ET
import json
import sys
from typing import Dict, Any


def parse_criterion(criterion_elem: ET.Element) -> Dict[str, Any]:
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
        "priority": int(priority.text) if priority is not None and priority.text else 0,
        "andOr": and_or.text.lower() if and_or is not None and and_or.text else "and",
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


def convert_xml_to_json(xml_content: str) -> Dict[str, Any]:
    """
    Convert Classic API XML computer group to Jamf Pro API JSON format.

    Args:
        xml_content: String containing the XML content

    Returns:
        Dictionary representing the JSON structure for Jamf Pro API
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML content: {e}") from e

    # Extract basic group information
    name = root.find("name")
    is_smart = root.find("is_smart")
    site = root.find("site")
    criteria = root.find("criteria")

    # Determine if this is a smart group based on presence of criteria
    is_smart_group = (
        is_smart.text.lower() == "true"
        if is_smart is not None and is_smart.text
        else False
    )

    # Build the Jamf Pro API JSON structure
    json_data = {
        "name": name.text if name is not None and name.text else "",
        "description": "This JSON was auto-converted from Classic API XML format",
    }

    # Add site information if present
    if site is not None:
        site_id = site.find("id")
        # site_name = site.find("name")
        if site_id is not None and site_id.text and site_id.text != "-1":
            json_data["siteId"] = site_id.text

    # Parse criteria for smart groups
    if is_smart_group and criteria is not None:
        criterion_list = []
        for criterion_elem in criteria.findall("criterion"):
            criterion_list.append(parse_criterion(criterion_elem))

        if criterion_list:
            json_data["criteria"] = criterion_list

    return json_data


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python3 convert_computer_group.py <input.xml> [output.json]")
        print("\nIf output.json is not specified, results will be printed to stdout")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # Read the XML file
        with open(input_file, "r", encoding="utf-8") as f:
            xml_content = f.read()

        # Convert to JSON
        json_data = convert_xml_to_json(xml_content)

        # Output the result
        json_output = json.dumps(json_data, indent=2, ensure_ascii=False)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Conversion complete! Output written to: {output_file}")
            print("\nIMPORTANT NOTES:")
            print("1. This JSON was auto-converted from Classic API XML format")
            print(
                "2. Use endpoint /api/v2/computer-groups/smart-groups for smart groups"
            )
            print(
                "3. Use endpoint /api/v2/computer-groups/static-groups for static groups"
            )
            print("4. Test the group criteria logic in a non-production environment")
            print(
                "5. Verify the conversion by comparing with the original group in Jamf Pro"
            )
        else:
            print(json_output)
            print("\nIMPORTANT NOTES:", file=sys.stderr)
            print(
                "1. This JSON was auto-converted from Classic API XML format",
                file=sys.stderr,
            )
            print(
                "2. Use endpoint /api/v2/computer-groups/smart-groups for smart groups",
                file=sys.stderr,
            )
            print(
                "3. Use endpoint /api/v2/computer-groups/static-groups for static groups",
                file=sys.stderr,
            )
            print(
                "4. Test the group criteria logic in a non-production environment",
                file=sys.stderr,
            )
            print(
                "5. Verify the conversion by comparing with the original group in Jamf Pro",
                file=sys.stderr,
            )

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (IOError, OSError) as e:
        print(f"File operation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
