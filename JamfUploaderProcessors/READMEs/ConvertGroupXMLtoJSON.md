# ConvertGroupXMLtoJSON

## Description

A processor for AutoPkg that converts a Classic API group XML definition to JSON format for use with the Jamf Pro API.

## Input variables

- **group_xml_path:**
  - **required:** True
  - **description:** Path to the XML file containing the Classic API group definition.
- **group_json_path:**
  - **required:** False
  - **description:** Path where the converted JSON file should be written. If not provided, the JSON will be output to the AutoPkg environment.

## Output variables

- **group_json_data:**
  - **description:** String containing the converted JSON group data.
- **is_smart_group:**
  - **description:** Boolean indicating whether the group is a smart group.
- **group_name:**
  - **description:** Name of the group.
